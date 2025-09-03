import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MCPProtocol:
    """Model Context Protocol (MCP) Implementation"""
    
    def __init__(self, memory, applicant_agent, administrator_agent):
        self.memory = memory
        self.applicant_agent = applicant_agent
        self.administrator_agent = administrator_agent
        self.active_sessions = {}
        self.tools = self._initialize_tools()
        logger.info("MCP Protocol initialized")
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize MCP tools registry"""
        return {
            "eligibility_check": {
                "name": "eligibility_check",
                "description": "Check patient eligibility for benefits",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "benefit_type": {"type": "string"},
                        "session_id": {"type": "string"}
                    },
                    "required": ["patient_id", "benefit_type"]
                }
            },
            "process_application": {
                "name": "process_application",
                "description": "Process eligibility application",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "application_data": {"type": "object"},
                        "session_id": {"type": "string"}
                    },
                    "required": ["application_data"]
                }
            },
            "get_patient_data": {
                "name": "get_patient_data",
                "description": "Retrieve patient data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            }
        }
    
    def create_tool_call(self, tool_name: str, parameters: Dict[str, Any], call_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an MCP tool call"""
        if call_id is None:
            call_id = str(uuid.uuid4())
        
        return {
            "type": "tool_call",
            "id": call_id,
            "function": {
                "name": tool_name,
                "arguments": json.dumps(parameters)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def create_tool_response(self, call_id: str, result: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
        """Create an MCP tool response"""
        response = {
            "type": "tool_response",
            "id": call_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response
    
    def start_conversation(self, scenario: str) -> Dict[str, Any]:
        """Start a new conversation using MCP protocol"""
        session_id = str(uuid.uuid4())
        
        # Initialize conversation in memory
        conversation_data = {
            "session_id": session_id,
            "protocol": "mcp",
            "scenario": scenario,
            "started_at": datetime.now().isoformat(),
            "messages": [],
            "tool_calls": [],
            "artifacts": []
        }
        
        self.memory.store_conversation(session_id, conversation_data)
        self.active_sessions[session_id] = conversation_data
        
        # Create initial tool call for eligibility check
        tool_call = self.create_tool_call(
            tool_name="eligibility_check",
            parameters={
                "patient_id": "001",
                "benefit_type": "bcse",
                "session_id": session_id,
                "scenario": scenario
            }
        )
        
        # Process with applicant agent
        applicant_response = self.applicant_agent.process_message(tool_call, "mcp")
        
        # Store tool call and response
        self._store_tool_call(session_id, "applicant", tool_call)
        self._store_message(session_id, "applicant", applicant_response)
        
        # Create follow-up tool call for processing application
        process_call = self.create_tool_call(
            tool_name="process_application",
            parameters={
                "application_data": applicant_response.get("result", {}),
                "session_id": session_id
            }
        )
        
        admin_response = self.administrator_agent.process_message(process_call, "mcp")
        self._store_tool_call(session_id, "administrator", process_call)
        self._store_message(session_id, "administrator", admin_response)
        
        logger.info(f"MCP conversation started: {session_id}")
        
        return {
            "session_id": session_id,
            "protocol": "mcp",
            "tools_available": list(self.tools.keys()),
            "initial_exchange": {
                "eligibility_call": tool_call,
                "applicant_response": applicant_response,
                "process_call": process_call,
                "admin_response": admin_response
            }
        }
    
    def handle_message(self, message: str, sender: str) -> Dict[str, Any]:
        """Handle incoming message through MCP protocol"""
        try:
            # Parse message
            parsed_message = json.loads(message) if isinstance(message, str) else message
            
            # Check if it's a tool call or regular message
            if parsed_message.get("type") == "tool_call":
                return self._handle_tool_call(parsed_message, sender)
            else:
                return self._handle_regular_message(parsed_message, sender)
        
        except Exception as e:
            logger.error(f"Error handling MCP message: {str(e)}")
            return {
                "protocol": "mcp",
                "error": {
                    "message": "Failed to process message",
                    "details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
    
    def _handle_tool_call(self, tool_call: Dict[str, Any], sender: str) -> Dict[str, Any]:
        """Handle MCP tool call"""
        tool_name = tool_call.get("function", {}).get("name")
        
        if tool_name not in self.tools:
            return self.create_tool_response(
                call_id=tool_call.get("id", "unknown"),
                error=f"Unknown tool: {tool_name}"
            )
        
        # Determine target agent based on tool
        if tool_name in ["eligibility_check", "get_patient_data"]:
            response = self.applicant_agent.process_message(tool_call, "mcp")
            target_agent = "applicant"
        else:
            response = self.administrator_agent.process_message(tool_call, "mcp")
            target_agent = "administrator"
        
        # Store in memory if session_id is provided
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        session_id = arguments.get("session_id")
        
        if session_id:
            self._store_tool_call(session_id, target_agent, tool_call)
            self._store_message(session_id, target_agent, response)
        
        return {
            "protocol": "mcp",
            "agent": target_agent,
            "tool_call": tool_call,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_regular_message(self, message: Dict[str, Any], sender: str) -> Dict[str, Any]:
        """Handle regular MCP message"""
        # Determine target agent
        if sender == "applicant":
            response = self.applicant_agent.process_message(message, "mcp")
            target_agent = "applicant"
        else:
            response = self.administrator_agent.process_message(message, "mcp")
            target_agent = "administrator"
        
        return {
            "protocol": "mcp",
            "agent": target_agent,
            "message": message,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    
    def _store_tool_call(self, session_id: str, agent: str, tool_call: Dict[str, Any]):
        """Store tool call in conversation memory"""
        if session_id in self.active_sessions:
            call_entry = {
                "agent": agent,
                "tool_call": tool_call,
                "timestamp": datetime.now().isoformat()
            }
            self.active_sessions[session_id]["tool_calls"].append(call_entry)
            self.memory.update_conversation(session_id, self.active_sessions[session_id])
    
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
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools"""
        return list(self.tools.values())
    
    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data for a specific session"""
        return self.active_sessions.get(session_id, {})
