import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class A2AProtocol:
    """Agent-to-Agent JSON-RPC + SSE Protocol Implementation"""
    
    def __init__(self, memory, applicant_agent, administrator_agent):
        self.memory = memory
        self.applicant_agent = applicant_agent
        self.administrator_agent = administrator_agent
        self.active_sessions = {}
        logger.info("A2A Protocol initialized")
    
    def create_jsonrpc_message(self, method: str, params: Dict[str, Any], message_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a JSON-RPC 2.0 message"""
        if message_id is None:
            message_id = str(uuid.uuid4())
        
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": message_id
        }
    
    def create_response(self, message_id: str, result: Any = None, error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a JSON-RPC 2.0 response"""
        response = {
            "jsonrpc": "2.0",
            "id": message_id
        }
        
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result
        
        return response
    
    def start_conversation(self, scenario: str) -> Dict[str, Any]:
        """Start a new conversation using A2A protocol"""
        session_id = str(uuid.uuid4())
        
        # Initialize conversation in memory
        conversation_data = {
            "session_id": session_id,
            "protocol": "a2a",
            "scenario": scenario,
            "started_at": datetime.now().isoformat(),
            "messages": [],
            "artifacts": []
        }
        
        self.memory.store_conversation(session_id, conversation_data)
        self.active_sessions[session_id] = conversation_data
        
        # Create initial message from applicant to administrator
        initial_request = self.create_jsonrpc_message(
            method="initiate_eligibility_check",
            params={
                "scenario": scenario,
                "timestamp": datetime.now().isoformat(),
                "agent_id": "applicant",
                "session_id": session_id
            }
        )
        
        # Process with applicant agent
        applicant_response = self.applicant_agent.process_message(initial_request, "a2a")
        
        # Store message in conversation
        self._store_message(session_id, "applicant", initial_request)
        self._store_message(session_id, "applicant", applicant_response)
        
        # Send to administrator agent
        admin_request = self.create_jsonrpc_message(
            method="process_application",
            params={
                "application_data": applicant_response.get("result", {}),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        admin_response = self.administrator_agent.process_message(admin_request, "a2a")
        self._store_message(session_id, "administrator", admin_response)
        
        logger.info(f"A2A conversation started: {session_id}")
        
        return {
            "session_id": session_id,
            "protocol": "a2a",
            "initial_exchange": {
                "applicant_request": initial_request,
                "applicant_response": applicant_response,
                "admin_response": admin_response
            }
        }
    
    def handle_message(self, message: str, sender: str) -> Dict[str, Any]:
        """Handle incoming message through A2A protocol"""
        try:
            # Parse JSON-RPC message
            parsed_message = json.loads(message) if isinstance(message, str) else message
            
            # Determine target agent
            if sender == "applicant" or parsed_message.get("params", {}).get("agent_id") == "applicant":
                response = self.applicant_agent.process_message(parsed_message, "a2a")
                target_agent = "applicant"
            else:
                response = self.administrator_agent.process_message(parsed_message, "a2a")
                target_agent = "administrator"
            
            # Store in memory if session_id is provided
            session_id = parsed_message.get("params", {}).get("session_id")
            if session_id:
                self._store_message(session_id, target_agent, parsed_message)
                self._store_message(session_id, target_agent, response)
            
            return {
                "protocol": "a2a",
                "agent": target_agent,
                "request": parsed_message,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error handling A2A message: {str(e)}")
            parsed_message = {}
            error_response = self.create_response(
                message_id=parsed_message.get("id", "unknown"),
                error={
                    "code": -32000,
                    "message": "Internal error",
                    "data": str(e)
                }
            )
            
            return {
                "protocol": "a2a",
                "error": error_response,
                "timestamp": datetime.now().isoformat()
            }
    
    def _store_message(self, session_id: str, agent: str, message: Dict[str, Any]):
        """Store message in conversation memory"""
        if session_id in self.active_sessions:
            message_entry = {
                "agent": agent,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            self.active_sessions[session_id]["messages"].append(message_entry)
            self.memory.update_conversation(session_id, self.active_sessions[session_id])
    
    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data for a specific session"""
        return self.active_sessions.get(session_id, {})
    
    def create_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Create Server-Sent Events formatted message"""
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        return f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
