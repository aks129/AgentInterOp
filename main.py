#!/usr/bin/env python3
"""
Flask-compatible WSGI application for Replit workflow compatibility
"""
import os
import json
import uuid
from flask import Flask, render_template, request, jsonify

# Create Flask app (WSGI compatible)
app = Flask(__name__, template_folder='app/web/templates', static_folder='app/web/static')
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Global state for protocol management
current_protocol = "a2a"

@app.route('/')
def index():
    """Main application page"""
    return render_template('simple_index.html')

@app.route('/api/current_protocol')
def get_current_protocol():
    """Get the current active protocol"""
    return jsonify({"protocol": current_protocol})

@app.route('/api/protocol', methods=['POST'])
def switch_protocol():
    """Switch between A2A and MCP protocols"""
    global current_protocol
    data = request.get_json()
    new_protocol = data.get('protocol')
    
    if new_protocol in ['a2a', 'mcp']:
        current_protocol = new_protocol
        return jsonify({"success": True, "protocol": current_protocol})
    else:
        return jsonify({"success": False, "error": "Invalid protocol"}), 400

@app.route('/api/start_conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation between agents"""
    data = request.get_json()
    scenario = data.get('scenario', 'eligibility_check')
    
    # Mock response for demonstration
    session_id = str(uuid.uuid4())
    
    if current_protocol == "a2a":
        initial_exchange = {
            "applicant_request": {"method": "initiate_eligibility_check", "id": "req-1"},
            "applicant_response": {"result": "Request submitted", "id": "req-1"},
            "admin_response": {"method": "process_application", "result": "Application received", "id": "req-2"}
        }
    else:
        initial_exchange = {
            "eligibility_call": {"tool": "eligibility_check", "parameters": {"scenario": scenario}},
            "applicant_response": {"result": "Eligibility check initiated"},
            "process_call": {"tool": "process_application", "parameters": {"data": "application_data"}},
            "admin_response": {"result": "Application processed successfully"}
        }
    
    return jsonify({
        "success": True,
        "result": {
            "session_id": session_id,
            "protocol": current_protocol,
            "initial_exchange": initial_exchange
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

# For gunicorn compatibility (WSGI)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)