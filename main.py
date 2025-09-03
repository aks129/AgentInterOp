#!/usr/bin/env python3
"""
Flask-compatible WSGI application for Replit workflow compatibility
"""
import os
import json
import uuid
import base64
from flask import Flask, render_template, request, jsonify
from app.config import load_config, save_config, update_config, ConnectathonConfig
from app.scenarios.registry import get_active, list_scenarios
from app.scenarios import registry
from app.scenarios import sc_bcse, sc_clinical_trial, sc_referral_specialist, sc_prior_auth, sc_custom

# Create Flask app (WSGI compatible)
app = Flask(__name__, template_folder='app/web/templates', static_folder='app/web/static')
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Register scenarios
registry.register("bcse", sc_bcse)
registry.register("clinical_trial", sc_clinical_trial)
registry.register("referral_specialist", sc_referral_specialist)
registry.register("prior_auth", sc_prior_auth)
registry.register("custom", sc_custom)

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

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    config = load_config()
    return jsonify(json.loads(config.model_dump_json()))

@app.route('/api/config', methods=['POST'])
def update_config_endpoint():
    """Update configuration with JSON patch"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    try:
        updated_config = update_config(data)
        return jsonify({
            "success": True,
            "config": json.loads(updated_config.model_dump_json())
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset configuration to defaults"""
    default_config = ConnectathonConfig()
    save_config(default_config)
    return jsonify({
        "success": True,
        "config": json.loads(default_config.model_dump_json())
    })

@app.route('/api/scenarios')
def get_scenarios():
    """List all available scenarios"""
    try:
        scenarios = list_scenarios()
        return jsonify({"scenarios": scenarios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/active')
def get_active_scenario():
    """Get active scenario details"""
    try:
        name, scenario = get_active()
        return jsonify({
            "name": name,
            "label": scenario["label"],
            "requirements": scenario["requirements"](),
            "examples": scenario["examples"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<scenario_name>/evaluate', methods=['POST'])
def evaluate_scenario(scenario_name):
    """Evaluate a specific scenario"""
    try:
        data = request.get_json()
        applicant_payload = data.get('applicant_payload', {})
        patient_bundle = data.get('patient_bundle', {})
        
        # Get scenario and evaluate
        name, scenario = get_active()
        if name != scenario_name:
            return jsonify({"error": f"Scenario '{scenario_name}' is not active"}), 400
            
        decision, rationale, artifacts = scenario["evaluate"](applicant_payload, patient_bundle)
        
        return jsonify({
            "scenario": name,
            "decision": decision,
            "rationale": rationale,
            "artifacts": artifacts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/.well-known/agent-card.json')
def agent_card():
    """Agent Card derived from configuration"""
    config = load_config()
    
    # Determine role based on operation mode
    role_mapping = {
        "applicant_only": "client",
        "administrator_only": "server", 
        "full_stack": "both"
    }
    
    # Create agent card
    card = {
        "protocolVersion": "0.2.9",
        "preferredTransport": "JSONRPC",
        "capabilities": {
            "streaming": True
        },
        "role": role_mapping.get(config.mode.role, "both"),
        "extensions": {
            "a2a.config64": base64.b64encode(
                json.dumps({"scenario": config.scenario.active}).encode()
            ).decode()
        }
    }
    
    return jsonify(card)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

# For gunicorn compatibility (WSGI)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)