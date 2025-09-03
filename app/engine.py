"""
Conversation Engine - Orchestrates agent interactions for BCS-E eligibility checking
"""
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

from app.agents.applicant import ApplicantAgent
from app.agents.administrator import AdministratorAgent
from app.store.memory import task_store, conversation_store, encode_base64

logger = logging.getLogger(__name__)

# Global agent instances
applicant_agent = ApplicantAgent()
administrator_agent = AdministratorAgent()

class ConversationEngine:
    """Orchestrates conversation flow between applicant and administrator agents"""
    
    def __init__(self):
        self.conversations: Dict[str, Dict[str, Any]] = {}
        
    def drive_turn(self, context_id: str, incoming_text: Optional[str] = None, 
                   incoming_files: Optional[List[str]] = None, role: str = "applicant") -> Dict[str, Any]:
        """
        Drive a conversation turn between agents
        
        Args:
            context_id: A2A contextId or MCP conversationId
            incoming_text: Text message from user (None on first turn)
            incoming_files: Attached files (if any)
            role: Role of the sender ("applicant" or "administrator")
            
        Returns:
            Dict containing messages, artifacts, and status
        """
        logger.info(f"Driving turn for context {context_id}, role: {role}, text: {incoming_text[:100] if incoming_text else 'None'}")
        
        # Initialize conversation state if not exists
        if context_id not in self.conversations:
            self.conversations[context_id] = {
                "status": "active",
                "messages": [],
                "artifacts": {},
                "stage": "requirements",  # requirements -> application -> decision -> completed
                "patient_data": None,
                "questionnaire_response": None,
                "decision_bundle": None
            }
        
        conv = self.conversations[context_id]
        response_messages = []
        
        # First turn - Administrator sends requirements message
        if incoming_text is None and not conv["messages"]:
            logger.info("First turn - sending administrator requirements")
            requirements = administrator_agent.requirements_message()
            requirements_text = "Please provide the following information for BCS-E eligibility checking:\n" + "\n".join(f"- {req}" for req in requirements)
            
            message = {
                "role": "administrator",
                "content": requirements_text,
                "timestamp": self._get_timestamp()
            }
            conv["messages"].append(message)
            response_messages.append(message)
            
            return {
                "messages": response_messages,
                "artifacts": conv["artifacts"],
                "status": conv["status"]
            }
        
        # Add incoming message to conversation
        if incoming_text:
            incoming_message = {
                "role": role,
                "content": incoming_text,
                "timestamp": self._get_timestamp()
            }
            conv["messages"].append(incoming_message)
        
        # Process based on conversation stage
        if conv["stage"] == "requirements" and role == "applicant" and incoming_text:
            # Applicant responding to requirements
            logger.info("Processing applicant response to requirements")
            
            # Parse requirements from administrator
            admin_requirements = administrator_agent.requirements_message()
            
            # Have applicant answer requirements
            qresp_result = applicant_agent.answer_requirements(admin_requirements)
            
            if "questionnaire_response" in qresp_result and "error" not in qresp_result:
                conv["questionnaire_response"] = qresp_result["questionnaire_response"]
                
                # Load patient data if not provided
                if "patient_data" in qresp_result:
                    conv["patient_data"] = qresp_result["patient_data"]
                else:
                    # Load patient data directly from applicant agent
                    try:
                        conv["patient_data"] = applicant_agent.load_patient()
                    except Exception as e:
                        logger.warning(f"Could not load patient data: {e}")
                        conv["patient_data"] = {}
                
                conv["stage"] = "application"
                
                # Generate application message
                app_message = {
                    "role": "applicant", 
                    "content": "I have completed the questionnaire and gathered the required patient data. Here is my application for BCS-E eligibility review.",
                    "timestamp": self._get_timestamp()
                }
                conv["messages"].append(app_message)
                response_messages.append(app_message)
                
                # Store QuestionnaireResponse artifact
                qresp_json = json.dumps(conv["questionnaire_response"], indent=2)
                conv["artifacts"]["QuestionnaireResponse.json"] = encode_base64(qresp_json)
                
                # Automatically proceed to process the application
                logger.info("Auto-processing application for decision")
                decision, rationale, used_resources = administrator_agent.validate(
                    conv["questionnaire_response"], 
                    conv["patient_data"]
                )
                
                # Create decision bundle
                decision_bundle = administrator_agent.finalize(decision, rationale, used_resources)
                conv["decision_bundle"] = decision_bundle
                conv["stage"] = "decision"
                
                # Generate decision message
                decision_message = {
                    "role": "administrator",
                    "content": f"Application processed. Decision: {decision.upper()}. {rationale}",
                    "timestamp": self._get_timestamp()
                }
                conv["messages"].append(decision_message)
                response_messages.append(decision_message)
                
                # Store DecisionBundle artifact
                bundle_json = json.dumps(decision_bundle, indent=2)
                conv["artifacts"]["DecisionBundle.json"] = encode_base64(bundle_json)
                
                # Mark as completed
                conv["status"] = "completed"
                
                completion_message = {
                    "role": "system",
                    "content": "BCS-E eligibility check completed. All artifacts have been generated.",
                    "timestamp": self._get_timestamp()
                }
                conv["messages"].append(completion_message)
                response_messages.append(completion_message)
                
            else:
                error_message = {
                    "role": "system",
                    "content": f"Error processing requirements: {qresp_result.get('error', 'Unknown error')}",
                    "timestamp": self._get_timestamp()
                }
                conv["messages"].append(error_message)
                response_messages.append(error_message)
        
        elif conv["stage"] == "application" and role == "applicant":
            # Process application submission
            logger.info("Processing application submission")
            
            if conv["questionnaire_response"] and conv["patient_data"]:
                # Administrator validates the application
                decision, rationale, used_resources = administrator_agent.validate(
                    conv["questionnaire_response"], 
                    conv["patient_data"]
                )
                
                # Create decision bundle
                decision_bundle = administrator_agent.finalize(decision, rationale, used_resources)
                conv["decision_bundle"] = decision_bundle
                conv["stage"] = "decision"
                
                # Generate decision message
                decision_message = {
                    "role": "administrator",
                    "content": f"Application processed. Decision: {decision.upper()}. {rationale}",
                    "timestamp": self._get_timestamp()
                }
                conv["messages"].append(decision_message)
                response_messages.append(decision_message)
                
                # Store DecisionBundle artifact
                bundle_json = json.dumps(decision_bundle, indent=2)
                conv["artifacts"]["DecisionBundle.json"] = encode_base64(bundle_json)
                
                # Mark as completed
                conv["status"] = "completed"
                
                completion_message = {
                    "role": "system",
                    "content": "BCS-E eligibility check completed. All artifacts have been generated.",
                    "timestamp": self._get_timestamp()
                }
                conv["messages"].append(completion_message)
                response_messages.append(completion_message)
            
        return {
            "messages": response_messages,
            "artifacts": conv["artifacts"],
            "status": conv["status"]
        }
    
    def get_conversation_state(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversation state"""
        return self.conversations.get(context_id)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

# Global conversation engine instance
conversation_engine = ConversationEngine()