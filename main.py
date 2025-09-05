#!/usr/bin/env python3
"""
Flask-compatible WSGI application for Replit workflow compatibility
"""
import os
import json
import uuid
import base64
import asyncio
from datetime import datetime
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

@app.route('/config')
def config_page():
    """Configuration control panel"""
    return render_template('config.html')

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
    """List all available scenarios with current active"""
    try:
        scenarios = list_scenarios()
        active_name, _ = get_active()
        return jsonify({
            "scenarios": scenarios,
            "active": active_name
        })
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

@app.route('/api/scenarios/activate', methods=['POST'])
def activate_scenario():
    """Activate a scenario"""
    try:
        data = request.get_json()
        scenario_name = data.get('name')
        if not scenario_name:
            return jsonify({"error": "Missing 'name' field"}), 400
        
        # Update config
        update_config({"scenario": {"active": scenario_name}})
        return jsonify({"success": True, "active": scenario_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/options', methods=['POST'])
def update_scenario_options():
    """Update scenario options (supports both direct and narrative-generated)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No options data provided"}), 400
        
        # Handle both formats: {"options": {...}} and direct {...}
        if 'options' in data:
            options = data.get('options', {})
        else:
            options = data
        
        # Update config using the existing update_config function
        update_config({"scenario": {"options": options}})
        
        return jsonify({
            "ok": True,
            "success": True,
            "message": "Scenario options updated",
            "options": options
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/requirements')
def get_requirements():
    """Get current scenario requirements"""
    try:
        name, scenario = get_active()
        return jsonify({
            "scenario": name,
            "requirements": scenario["requirements"]()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulation', methods=['POST'])
def update_simulation():
    """Update simulation settings"""
    try:
        data = request.get_json()
        update_config({"simulation": data})
        return jsonify({"success": True, "simulation": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mode', methods=['POST'])
def update_mode():
    """Update operation mode"""
    try:
        data = request.get_json()
        role = data.get('role')
        if role not in ["applicant_only", "administrator_only", "full_stack"]:
            return jsonify({"error": "Invalid role"}), 400
        
        update_config({"mode": {"role": role}})
        return jsonify({"success": True, "role": role})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/transcript/<context_id>')
def get_transcript(context_id):
    """Get full task history JSON"""
    try:
        from app.engine import conversation_engine
        conversation = conversation_engine.get_conversation_state(context_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify(conversation)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/artifacts/<context_id>')
def get_artifacts(context_id):
    """Get artifact metadata"""
    try:
        from app.engine import conversation_engine
        conversation = conversation_engine.get_conversation_state(context_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        artifacts = []
        for name, content in conversation.get("artifacts", {}).items():
            artifacts.append({
                "name": name,
                "size": len(content),
                "type": "application/fhir+json" if name.endswith(".json") else "application/octet-stream"
            })
        return jsonify({"artifacts": artifacts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/reset', methods=['POST'])
def reset_stores():
    """Clear in-memory stores"""
    try:
        from app.store.memory import task_store, conversation_store
        from app.engine import conversation_engine
        
        # Clear stores
        task_store._tasks.clear()
        conversation_store._conversations.clear()
        conversation_engine.conversations.clear()
        conversation_engine.capacity_counters.clear()
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/selftest')
def selftest():
    """Conformance self-test"""
    try:
        scenarios = list_scenarios()
        config = load_config()
        
        return jsonify({
            "mcp_tools": ["begin_chat_thread", "send_message_to_chat_thread", "check_replies"],
            "a2a_methods": ["message/send", "message/stream", "tasks/get", "tasks/cancel"],
            "scenarios": list(scenarios.keys()),
            "mode": config.mode.role,
            "ok": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500

@app.route('/.well-known/agent-card.json')
def agent_card():
    """Agent Card derived from configuration"""
    config = load_config()
    
    # Determine role based on operation mode
    role = "applicant" if config.mode.role == "applicant_only" else \
          "administrator" if config.mode.role == "administrator_only" else \
          "composite"
    
    # Create agent card
    card = {
        "protocolVersion": "0.2.9",
        "preferredTransport": "JSONRPC",
        "capabilities": {
            "streaming": True
        },
        "role": role,
        "skills": [{
            "name": "discovery",
            "description": "Multi-scenario connectathon demo",
            "a2a.config64": base64.b64encode(
                json.dumps({
                    "scenario": config.scenario.active,
                    "tags": config.tags
                }).encode()
            ).decode()
        }]
    }
    
    # Add endpoints if public_base_url is set
    if config.protocol.public_base_url:
        card["endpoints"] = {
            "jsonrpc": f"{config.protocol.public_base_url}/api/bridge/demo/a2a"
        }
    
    return jsonify(card)

# FHIR Integration Routes
@app.route('/api/fhir/config', methods=['POST'])
def configure_fhir():
    """Configure FHIR connection"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No data provided"}), 400
        
        base_url = data.get('base')
        token = data.get('token')
        
        if not base_url:
            return jsonify({"ok": False, "error": "FHIR base URL is required"}), 400
        
        # Update config with FHIR settings
        fhir_options = {"fhir_base": base_url}
        if token:
            fhir_options["fhir_token"] = token
        
        # Update the data.options in config
        current_config = load_config()
        current_options = current_config.data.options.copy()
        current_options.update(fhir_options)
        
        update_config({"data": {"options": current_options}})
        
        return jsonify({"ok": True, "message": "FHIR configuration saved"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/fhir/capabilities')
def get_fhir_capabilities():
    """Get FHIR server capabilities"""
    try:
        from app.fhir.service import build_connector
        connector = asyncio.run(build_connector())
        capabilities = asyncio.run(connector.capabilities())
        return jsonify(capabilities)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"FHIR server error: {str(e)}"}), 500

@app.route('/api/fhir/patients')
def get_fhir_patients():
    """Search FHIR patients"""
    try:
        from app.fhir.service import build_connector
        connector = asyncio.run(build_connector())
        
        # Extract query parameters
        search_params = {}
        if request.args.get('name'):
            search_params['name'] = request.args.get('name')
        if request.args.get('identifier'):
            search_params['identifier'] = request.args.get('identifier')
        
        # Search patients
        result = asyncio.run(connector.search("Patient", **search_params))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"FHIR search error: {str(e)}"}), 500

@app.route('/api/fhir/patient/<patient_id>/everything')
def get_patient_everything(patient_id: str):
    """Get patient $everything bundle"""
    try:
        from app.fhir.service import build_connector
        connector = asyncio.run(build_connector())
        
        # Get patient everything
        result = asyncio.run(connector.patient_everything(patient_id))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"FHIR patient error: {str(e)}"}), 500

@app.route('/api/ingest', methods=['POST'])
def ingest_patient_data():
    """Ingest FHIR bundle and map to scenario-specific applicant payload"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No data provided"}), 400
        
        # Support both legacy format and new bundle format
        bundle = data.get('bundle') or data.get('patientData')
        patient_id = data.get('patientId')
        
        if not bundle:
            return jsonify({"ok": False, "error": "Missing bundle or patientData"}), 400
        
        # Get current scenario from config
        from app.config import load_config
        from app.ingest.mapper import map_for_scenario
        from app.scenarios.registry import get_active
        
        config = load_config()
        scenario_key, scenario_data = get_active()
        scenario_name = scenario_key if scenario_key else "bcse"
        
        # Map FHIR bundle to applicant payload based on scenario
        applicant_payload = map_for_scenario(scenario_name, bundle)
        
        # Create context ID
        if not patient_id:
            # Try to extract patient ID from bundle
            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('resourceType') == 'Patient':
                    patient_id = resource.get('id', 'unknown')
                    break
            if not patient_id:
                patient_id = f"patient-{hash(str(bundle)) % 100000}"
        
        ingest_context_id = f"ingested-{scenario_name}-{patient_id}"
        
        # Store the mapped data in a simple global dict for now
        # This will be accessible to agents during conversations
        if not hasattr(app, 'ingested_data'):
            app.ingested_data = {}
        
        from datetime import datetime
        app.ingested_data[ingest_context_id] = {
            "status": "ingested",
            "scenario": scenario_name,
            "patient_id": patient_id,
            "raw_bundle": bundle,
            "applicant_payload": applicant_payload,
            "ingested_at": datetime.utcnow().isoformat() + 'Z',
            "stage": "data_available"
        }
        
        # Extract summary information for response
        bundle_entries = bundle.get('entry', [])
        resource_counts = {}
        for entry in bundle_entries:
            resource_type = entry.get('resource', {}).get('resourceType', 'Unknown')
            resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1
        
        return jsonify({
            "ok": True,
            "message": f"Patient {patient_id} data ingested and mapped for {scenario_name}",
            "context_id": ingest_context_id,
            "scenario": scenario_name,
            "applicant_payload": applicant_payload,
            "resource_summary": resource_counts,
            "total_resources": len(bundle_entries)
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": f"Ingestion error: {str(e)}"}), 500

@app.route('/api/ingested/latest')
def get_latest_ingested():
    """Get the most recently ingested FHIR data"""
    try:
        if not hasattr(app, 'ingested_data') or not app.ingested_data:
            return jsonify({"ok": False, "message": "No ingested data available"})
        
        # Find the most recent ingestion
        latest_data = None
        latest_time = None
        
        for context_id, data in app.ingested_data.items():
            ingested_at = data.get('ingested_at')
            if ingested_at:
                if not latest_time or ingested_at > latest_time:
                    latest_time = ingested_at
                    latest_data = data
        
        if latest_data:
            return jsonify({
                "ok": True,
                "data": latest_data,
                "context_id": context_id
            })
        else:
            return jsonify({"ok": False, "message": "No valid ingested data found"})
            
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error retrieving ingested data: {str(e)}"}), 500

@app.route('/api/scenarios/narrative', methods=['POST'])
def process_narrative():
    """Convert narrative text to JSON scenario using Claude"""
    try:
        data = request.get_json()
        if not data or not data.get('text'):
            return jsonify({"ok": False, "error": "Missing narrative text"}), 400
        
        narrative_text = data.get('text')
        
        # Import and call the Anthropic LLM function
        import asyncio
        from app.llm.anthropic import narrative_to_json
        
        # Run the async function
        try:
            scenario_json = asyncio.run(narrative_to_json(narrative_text))
        except ValueError as e:
            if "ANTHROPIC_API_KEY not set" in str(e):
                return jsonify({
                    "ok": False, 
                    "error": "ANTHROPIC_API_KEY environment variable is required",
                    "requires_key": True
                }), 400
            else:
                raise e
        
        # Update scenario options with the generated JSON using existing function
        update_config({"scenario": {"options": scenario_json}})
        
        return jsonify({
            "ok": True,
            "message": "Narrative converted and applied to scenario",
            "generated_schema": scenario_json,
            "updated_options": scenario_json
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": f"Narrative processing error: {str(e)}"}), 500

@app.route('/api/trace/<context_id>')
def get_trace(context_id):
    """Get decision trace for a context"""
    try:
        from app.store.memory import trace_store
        
        # Get trace events for the context
        trace_events = trace_store.get_trace(context_id)
        
        # Convert TraceEvent objects to dictionaries
        events_data = []
        for event in trace_events:
            events_data.append({
                "timestamp": event.timestamp,
                "actor": event.actor,
                "action": event.action,
                "detail": event.detail
            })
        
        return jsonify({
            "ok": True,
            "context_id": context_id,
            "events": events_data,
            "count": len(events_data)
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": f"Trace retrieval error: {str(e)}"}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

# For gunicorn compatibility (WSGI)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)