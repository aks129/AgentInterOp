"""Scenario runner for managing A2A conversations"""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from .scenario_models import RunConfig, RunContext, Scenario, ScenarioAgent
from .scenario_loader import fetch_scenario
from .agentcard_loader import fetch_agent_card
from .mcp_fhir_bridge import fetch_patient_everything, extract_minimal_facts
from .bcs_guidelines import evaluate_bcs_eligibility
from .a2a_proxy import proxy_a2a_message, create_message_send_payload, create_message_stream_payload

# Global run state storage (in production, use Redis or database)
_run_contexts: Dict[str, RunContext] = {}


async def start_scenario_run(config: RunConfig) -> str:
    """
    Start a new scenario run.
    
    Returns:
        run_id: Unique identifier for the run
    """
    run_id = str(uuid.uuid4())
    
    # Initialize run context
    context = RunContext(
        runId=run_id,
        config=config,
        status="initializing",
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )
    
    try:
        # Load scenario
        scenario = await fetch_scenario(config.scenarioUrl)
        context.scenario = scenario
        
        # Validate agent ID
        agent = scenario.get_agent_by_id(config.myAgentId)
        if not agent:
            raise ValueError(f"Agent '{config.myAgentId}' not found in scenario")
        
        # Load remote agent card if specified
        if config.remoteAgentCardUrl:
            agent_card_info = await fetch_agent_card(config.remoteAgentCardUrl)
            context.remoteAgentCard = agent_card_info["details"]["raw"]
            context.remoteA2aUrl = agent_card_info["url"]
        
        # Fetch FHIR data if configured
        if config.fhir and config.fhir.get("base") and config.fhir.get("patientId"):
            try:
                fhir_bundle = await fetch_patient_everything(
                    config.fhir["base"],
                    config.fhir["patientId"],
                    config.fhir.get("token")
                )
                context.fhirFacts = extract_minimal_facts(fhir_bundle)
            except Exception as e:
                # Don't fail the run if FHIR fetch fails
                context.artifacts.append({
                    "type": "error",
                    "name": "FHIR fetch failed",
                    "content": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Evaluate BCS eligibility if enabled and we have FHIR facts
        if config.bcse and config.bcse.get("enabled") and context.fhirFacts:
            try:
                context.bcsEvaluation = evaluate_bcs_eligibility(context.fhirFacts)
            except Exception as e:
                context.artifacts.append({
                    "type": "error",
                    "name": "BCS evaluation failed",
                    "content": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Prepare initial message if available
        initial_message = None
        if agent.messageToUseWhenInitiatingConversation:
            initial_message = agent.messageToUseWhenInitiatingConversation
        elif agent.systemPrompt:
            # Extract a greeting from system prompt or create default
            initial_message = create_default_initial_message(agent)
        
        if initial_message:
            context.transcript.append({
                "role": "assistant",
                "content": initial_message,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "local",
                "agent_id": config.myAgentId
            })
        
        context.status = "ready"
        context.updated_at = datetime.utcnow().isoformat()
        
    except Exception as e:
        context.status = "failed"
        context.artifacts.append({
            "type": "error",
            "name": "Initialization failed",
            "content": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        context.updated_at = datetime.utcnow().isoformat()
    
    # Store context
    _run_contexts[run_id] = context
    return run_id


async def send_message_in_run(
    run_id: str,
    message_parts: List[Dict[str, Any]],
    task_id: Optional[str] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Send a message within a scenario run.
    
    Args:
        run_id: Run identifier
        message_parts: Message parts to send
        task_id: Optional task ID to continue conversation
        stream: Whether to use streaming
    
    Returns:
        Response data and updated transcript
    """
    context = _run_contexts.get(run_id)
    if not context:
        raise ValueError(f"Run {run_id} not found")
    
    if context.status not in ["ready", "waiting", "working"]:
        raise ValueError(f"Run {run_id} is not in a valid state for messaging: {context.status}")
    
    # Update context
    context.status = "working"
    context.updated_at = datetime.utcnow().isoformat()
    
    # Use existing task ID or the one provided
    if task_id:
        context.taskId = task_id
    
    try:
        # Add user message to transcript
        user_message = {
            "role": "user",
            "content": extract_text_from_parts(message_parts),
            "parts": message_parts,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "local",
            "agent_id": context.config.myAgentId
        }
        context.transcript.append(user_message)
        
        # Send message based on conversation mode
        if context.config.conversationMode == "remote" and context.remoteA2aUrl:
            response = await send_message_remote(context, message_parts, stream)
        else:
            response = await send_message_local(context, message_parts)
        
        # Add response to transcript
        if response.get("success"):
            response_data = response.get("data", {})
            
            # Extract response content
            response_content = extract_response_content(response_data)
            
            assistant_message = {
                "role": "assistant", 
                "content": response_content,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "remote" if context.config.conversationMode == "remote" else "local",
                "raw_response": response_data
            }
            
            # Update task ID if provided in response
            if response_data.get("result", {}).get("taskId"):
                context.taskId = response_data["result"]["taskId"]
                assistant_message["task_id"] = context.taskId
            
            context.transcript.append(assistant_message)
            context.status = "waiting"
        else:
            context.status = "failed"
            context.artifacts.append({
                "type": "error",
                "name": "Message send failed",
                "content": response.get("error", "Unknown error"),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        context.updated_at = datetime.utcnow().isoformat()
        return response
        
    except Exception as e:
        context.status = "failed"
        context.artifacts.append({
            "type": "error",
            "name": "Message processing failed",
            "content": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        context.updated_at = datetime.utcnow().isoformat()
        raise


async def send_message_remote(
    context: RunContext,
    message_parts: List[Dict[str, Any]],
    stream: bool = False
) -> Dict[str, Any]:
    """Send message to remote A2A endpoint"""
    if stream:
        payload = create_message_stream_payload(message_parts, context.taskId)
    else:
        payload = create_message_send_payload(message_parts, context.taskId)
    
    return await proxy_a2a_message(context.remoteA2aUrl, payload, stream)


async def send_message_local(
    context: RunContext,
    message_parts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate local response (simulation mode)"""
    # Simple simulation - in a real implementation, this would
    # use the local A2A handler or generate contextual responses
    
    message_text = extract_text_from_parts(message_parts)
    
    # Generate contextual response based on scenario and message
    response_text = generate_simulated_response(context, message_text)
    
    return {
        "success": True,
        "data": {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "result": {
                "taskId": context.taskId or str(uuid.uuid4()),
                "status": "completed",
                "message": {
                    "parts": [{"kind": "text", "text": response_text}]
                }
            }
        }
    }


def get_run_status(run_id: str) -> Optional[RunContext]:
    """Get current run status and transcript"""
    return _run_contexts.get(run_id)


def cancel_run(run_id: str) -> bool:
    """Cancel a running scenario"""
    context = _run_contexts.get(run_id)
    if not context:
        return False
    
    context.status = "cancelled"
    context.updated_at = datetime.utcnow().isoformat()
    return True


def list_active_runs() -> List[str]:
    """List all active run IDs"""
    return list(_run_contexts.keys())


def cleanup_old_runs(max_age_hours: int = 24):
    """Clean up old run contexts"""
    cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
    
    to_remove = []
    for run_id, context in _run_contexts.items():
        if context.created_at:
            created_time = datetime.fromisoformat(context.created_at.replace('Z', '+00:00')).timestamp()
            if created_time < cutoff_time:
                to_remove.append(run_id)
    
    for run_id in to_remove:
        del _run_contexts[run_id]


# Helper functions

def create_default_initial_message(agent: ScenarioAgent) -> str:
    """Create a default initial message from agent definition"""
    if agent.role == "administrator" or agent.role == "clinician":
        return f"Hello! I'm {agent.name or agent.agentId}. How can I help you today?"
    elif agent.role == "applicant":
        return "Hello, I'd like to get information about my eligibility."
    else:
        return f"Hello! I'm ready to start our conversation as {agent.role}."


def extract_text_from_parts(parts: List[Dict[str, Any]]) -> str:
    """Extract text content from message parts"""
    text_parts = []
    for part in parts:
        if part.get("kind") == "text" and part.get("text"):
            text_parts.append(part["text"])
    return " ".join(text_parts)


def extract_response_content(response_data: Dict[str, Any]) -> str:
    """Extract readable content from A2A response"""
    if "result" in response_data:
        result = response_data["result"]
        if "message" in result and "parts" in result["message"]:
            return extract_text_from_parts(result["message"]["parts"])
    
    return str(response_data)


def generate_simulated_response(context: RunContext, user_message: str) -> str:
    """Generate a simulated response for local mode"""
    user_msg_lower = user_message.lower()
    
    # BCS-specific responses
    if context.scenario and "bcs" in context.scenario.metadata.id.lower():
        if any(word in user_msg_lower for word in ["age", "old"]):
            return "Thank you for that information. Can you also tell me about your previous screening history?"
        elif any(word in user_msg_lower for word in ["mammogram", "screening", "last"]):
            if context.bcsEvaluation:
                decision = context.bcsEvaluation.get("decision", "needs-more-info")
                rationale = context.bcsEvaluation.get("rationale", "")
                return f"Based on the information provided, {rationale} Would you like help finding screening locations?"
            return "Thank you. Let me evaluate your screening eligibility..."
        elif "schedule" in user_msg_lower or "appointment" in user_msg_lower:
            return "I can help you find screening appointments in your area. What is your preferred location?"
    
    # Generic responses
    if "hello" in user_msg_lower or "hi" in user_msg_lower:
        return "Hello! I'm here to help. What would you like to know?"
    elif "help" in user_msg_lower:
        return "I can assist with eligibility screening and appointment scheduling. What specific information do you need?"
    else:
        return "Thank you for that information. Is there anything else you'd like to discuss?"