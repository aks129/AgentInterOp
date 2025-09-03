import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from app.eligibility.bcse import BCSDEligibilityChecker

logger = logging.getLogger(__name__)

class AdministratorAgent:
    """Administrator Agent - handles application processing and approval"""
    
    def __init__(self):
        self.agent_id = "administrator"
        self.name = "Administrator Agent"
        self.description = "Processes applications and makes eligibility determinations"
        self.eligibility_checker = BCSDEligibilityChecker()
        
        # Load agent card
        self.card = self._load_agent_card()
        logger.info("Administrator Agent initialized")
    
    def _load_agent_card(self) -> Dict[str, Any]:
        """Load agent card configuration"""
        try:
            card_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'cards', 'administrator-agent-card.json')
            with open(card_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load agent card: {e}")
            return {
                "name": self.name,
                "description": self.description,
                "capabilities": ["application_processing", "eligibility_determination", "approval_workflow"]
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
            if method == "process_application":
                result = self._process_application(params)
            elif method == "approve_application":
                result = self._approve_application(params)
            elif method == "review_eligibility":
                result = self._review_eligibility(params)
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
            if tool_name == "process_application":
                result = self._process_application(arguments)
            elif tool_name == "approve_application":
                result = self._approve_application(arguments)
            elif tool_name == "review_eligibility":
                result = self._review_eligibility(arguments)
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
            "message": f"Processed message from administrator agent",
            "original_message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def _process_application(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process eligibility application"""
        application_data = params.get("application_data", {})
        session_id = params.get("session_id")
        
        # Extract patient data from application
        patient_data = application_data.get("patient_data", {}).get("result", {})
        benefit_type = application_data.get("requested_benefit", "bcse")
        
        # Perform eligibility check
        eligibility_result = self.eligibility_checker.check_eligibility(
            patient_data, benefit_type
        )
        
        # Make determination
        determination = self._make_determination(patient_data, eligibility_result)
        
        result = {
            "application_processed": True,
            "session_id": session_id,
            "patient_id": application_data.get("patient_id"),
            "benefit_type": benefit_type,
            "eligibility_check": eligibility_result,
            "determination": determination,
            "processed_by": self.agent_id,
            "processing_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Processed application for session {session_id}: {determination['status']}")
        
        return result
    
    def _make_determination(self, patient_data: Dict[str, Any], eligibility_result: Dict[str, Any]) -> Dict[str, Any]:
        """Make eligibility determination based on data and rules"""
        eligible = eligibility_result.get("eligible", False)
        criteria_met = eligibility_result.get("criteria_met", {})
        
        if eligible and all(criteria_met.values()):
            status = "approved"
            reason = "All eligibility criteria met"
        elif eligible and any(criteria_met.values()):
            status = "conditional_approval"
            reason = "Some criteria met, pending additional verification"
        else:
            status = "denied"
            reason = "Eligibility criteria not met"
        
        return {
            "status": status,
            "reason": reason,
            "criteria_analysis": criteria_met,
            "determination_code": f"DET_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "reviewer": self.agent_id
        }
    
    def _approve_application(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Approve processed application"""
        application_id = params.get("application_id")
        approval_reason = params.get("reason", "Standard approval")
        
        return {
            "action": "application_approved",
            "application_id": application_id,
            "approval_id": f"APV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "reason": approval_reason,
            "approved_by": self.agent_id,
            "approval_timestamp": datetime.now().isoformat(),
            "status": "approved"
        }
    
    def _review_eligibility(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Review eligibility determination"""
        patient_id = params.get("patient_id")
        determination = params.get("determination", {})
        
        # Perform administrative review
        review_result = {
            "patient_id": patient_id,
            "original_determination": determination,
            "review_status": "reviewed",
            "review_notes": "Administrative review completed",
            "reviewed_by": self.agent_id,
            "review_timestamp": datetime.now().isoformat()
        }
        
        # Add any override logic here if needed
        if determination.get("status") == "conditional_approval":
            review_result["final_status"] = "approved"
            review_result["override_reason"] = "Administrative override for conditional approval"
        else:
            review_result["final_status"] = determination.get("status", "pending")
        
        return review_result
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.card.get("capabilities", []),
            "protocols_supported": ["a2a", "mcp"]
        }
