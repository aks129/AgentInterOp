import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
from datetime import datetime

from app.protocols.a2a import A2AProtocol
from app.protocols.mcp import MCPProtocol
from app.store.memory import ConversationMemory
from app.agents.applicant import ApplicantAgent
from app.agents.administrator import AdministratorAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
socketio = SocketIO(app, cors_allowed_origins="*")

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
    return render_template('index.html')

@app.route('/api/conversations')
def get_conversations():
    """Get all conversations from memory"""
    conversations = memory.get_all_conversations()
    return jsonify(conversations)

@app.route('/api/protocol', methods=['POST'])
def switch_protocol():
    """Switch between A2A and MCP protocols"""
    global current_protocol
    data = request.get_json()
    new_protocol = data.get('protocol')
    
    if new_protocol in ['a2a', 'mcp']:
        current_protocol = new_protocol
        logger.info(f"Protocol switched to: {current_protocol}")
        
        # Emit protocol change to all clients
        socketio.emit('protocol_changed', {'protocol': current_protocol})
        
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
        
        # Emit conversation started event
        socketio.emit('conversation_started', {
            'protocol': current_protocol,
            'scenario': scenario,
            'result': result
        })
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected")
    emit('connected', {'protocol': current_protocol})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming message from client"""
    try:
        message = data.get('message')
        sender = data.get('sender', 'user')
        
        if current_protocol == "a2a":
            response = a2a_protocol.handle_message(message, sender)
        else:
            response = mcp_protocol.handle_message(message, sender)
        
        # Emit response to all clients
        emit('message_response', response, broadcast=True)
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    logger.info("Starting Multi-Agent Interoperability Demo")
    logger.info(f"Current protocol: {current_protocol}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
