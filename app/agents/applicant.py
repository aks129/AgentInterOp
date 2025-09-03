import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from app.eligibility.bcse import BCSDEligibilityChecker

logger = logging.getLogger(__name__)

class ApplicantAgent:
    """Applicant Agent - handles patient eligibility applications"""
    
    def __init__(self):
        self.agent_id = "applicant"
        self.name = "Applicant Agent"
        self.description = "Handles patient eligibility applications and data gathering"
        self.eligibility_checker = BCSDEligibilityChecker()
        
        # Load agent card
        self.card = self._load_agent_card()
        logger.info("Applicant Agent initialized")
    
    def _load_agent_card(self) -> Dict[str, Any]:
        """Load agent card configuration"""
        try:
            card_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'cards', 'applicant-agent-card.json')
            with open(card_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load agent card: {e}")
            return {
                "name": self.name,
                "description": self.description,
                "capabilities": ["eligibility_check", "data_gathering", "application_submission"]
            }
    
    def process_message(self, message: Dict[str, Any], protocol: str) -> Dict[str, Any]:
        """Process incoming message based on protocol"""
        if protocol == "a2a":
            return self._process_a2a_message(message)
        elif protocol == "mcp":
            return self._process_mcp_message(message)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
    
    def _process_a2a_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process A2A JSON-RPC message"""
        method = message.get("method")
        params = message.get("params", {})
        message_id = message.get("id")
        
        try:
            if method == "initiate_eligibility_check":
                result = self._initiate_eligibility_check(params)
            elif method == "get_patient_data":
                result = self._get_patient_data(params)
            elif method == "submit_application":
                result = self._submit_application(params)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": message_id
            }
        
        except Exception as e:
            logger.error(f"Error processing A2A message: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                },
                "id": message_id
            }
    
    def _process_mcp_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP tool call or message"""
        if message.get("type") == "tool_call":
            return self._process_mcp_tool_call(message)
        else:
            return self._process_mcp_regular_message(message)
    
    def _process_mcp_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP tool call"""
        tool_name = tool_call.get("function", {}).get("name")
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        call_id = tool_call.get("id")
        
        try:
            if tool_name == "eligibility_check":
                result = self._check_eligibility(arguments)
            elif tool_name == "get_patient_data":
                result = self._get_patient_data(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return {
                "type": "tool_response",
                "id": call_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error processing MCP tool call: {str(e)}")
            return {
                "type": "tool_response",
                "id": call_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _process_mcp_regular_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process regular MCP message"""
        return {
            "type": "response",
            "agent": self.agent_id,
            "message": f"Processed message from applicant agent",
            "original_message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def _initiate_eligibility_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate eligibility check process"""
        scenario = params.get("scenario", "eligibility_check")
        session_id = params.get("session_id")
        
        # Get default patient data
        patient_data = self._get_patient_data({"patient_id": "001"})
        
        # Prepare application data
        application_data = {
            "patient_id": "001",
            "scenario": scenario,
            "session_id": session_id,
            "patient_data": patient_data,
            "requested_benefit": "bcse",
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id
        }
        
        logger.info(f"Initiated eligibility check for session {session_id}")
        
        return {
            "action": "eligibility_check_initiated",
            "application_data": application_data,
            "status": "pending_review"
        }
    
    def _check_eligibility(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check patient eligibility"""
        patient_id = params.get("patient_id", "001")
        benefit_type = params.get("benefit_type", "bcse")
        
        # Get patient data
        patient_data = self._get_patient_data({"patient_id": patient_id})
        
        # Use BCSE eligibility checker
        eligibility_result = self.eligibility_checker.check_eligibility(
            patient_data.get("result", {}), benefit_type
        )
        
        return {
            "patient_id": patient_id,
            "benefit_type": benefit_type,
            "eligibility_status": eligibility_result.get("eligible", False),
            "details": eligibility_result,
            "checked_by": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_patient_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get patient data from storage"""
        patient_id = params.get("patient_id", "001")
        
        try:
            patient_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data', 'patients', f'{patient_id}.json'
            )
            
            with open(patient_file, 'r') as f:
                patient_data = json.load(f)
            
            return {
                "patient_id": patient_id,
                "result": patient_data,
                "retrieved_by": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error retrieving patient data: {str(e)}")
            return {
                "patient_id": patient_id,
                "error": f"Could not retrieve patient data: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _submit_application(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit eligibility application"""
        application_data = params.get("application_data", {})
        
        return {
            "action": "application_submitted",
            "application_id": f"APP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "data": application_data,
            "status": "submitted",
            "submitted_by": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.card.get("capabilities", []),
            "protocols_supported": ["a2a", "mcp"]
        }
