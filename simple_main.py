#!/usr/bin/env python3

import os
import sys
import logging
from flask import Flask, render_template, request, jsonify

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.protocols.a2a import A2AProtocol
from app.protocols.mcp import MCPProtocol
from app.store.memory import ConversationMemory
from app.agents.applicant import ApplicantAgent
from app.agents.administrator import AdministratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='app/web/templates', static_folder='app/web/static')
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize components
memory = ConversationMemory()
applicant_agent = ApplicantAgent()
administrator_agent = AdministratorAgent()

# Initialize protocols
a2a_protocol = A2AProtocol(memory, applicant_agent, administrator_agent)
mcp_protocol = MCPProtocol(memory, applicant_agent, administrator_agent)

# Current active protocol
current_protocol = "a2a"

@app.route('/')
def index():
    """Main application page"""
    return render_template('simple_index.html')

@app.route('/api/conversations')
def get_conversations():
    """Get all conversations from memory"""
    try:
        conversations = memory.get_all_conversations()
        return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return jsonify([])

@app.route('/api/protocol', methods=['POST'])
def switch_protocol():
    """Switch between A2A and MCP protocols"""
    global current_protocol
    data = request.get_json()
    new_protocol = data.get('protocol')
    
    if new_protocol in ['a2a', 'mcp']:
        current_protocol = new_protocol
        logger.info(f"Protocol switched to: {current_protocol}")
        return jsonify({'success': True, 'protocol': current_protocol})
    else:
        return jsonify({'success': False, 'error': 'Invalid protocol'}), 400

@app.route('/api/start_conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation between agents"""
    data = request.get_json()
    scenario = data.get('scenario', 'eligibility_check')
    
    try:
        if current_protocol == "a2a":
            result = a2a_protocol.start_conversation(scenario)
        else:
            result = mcp_protocol.start_conversation(scenario)
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/current_protocol')
def current_protocol_status():
    """Get current protocol status"""
    return jsonify({'protocol': current_protocol})

if __name__ == '__main__':
    logger.info("Starting Multi-Agent Interoperability Demo")
    logger.info(f"Current protocol: {current_protocol}")
    app.run(host='0.0.0.0', port=5000, debug=True)