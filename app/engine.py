"""
Conversation Engine - Orchestrates agent interactions for BCS-E eligibility checking
"""
import json
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

from app.agents.applicant import ApplicantAgent
from app.agents.administrator import AdministratorAgent
from app.store.memory import task_store, conversation_store, encode_base64, trace
from app.scenarios import registry
from app.config import load_config

logger = logging.getLogger(__name__)

# Global agent instances
applicant_agent = ApplicantAgent()
administrator_agent = AdministratorAgent()

class ConversationEngine:
    """Orchestrates conversation flow between applicant and administrator agents"""
    
    def __init__(self, max_conversations: int = 100, cleanup_hours: int = 1):
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.capacity_counters: Dict[str, int] = {}  # Track capacity usage per scenario
        self.max_conversations = max_conversations
        self.cleanup_hours = cleanup_hours
        
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
        logger.info(f"🔄 TURN START - Protocol: Unknown, Context: {context_id}, Role: {role}, Text: {incoming_text[:50] if incoming_text else 'None'}...")
        
        # Load current config and active scenario
        config = load_config()
        scenario_name, scenario = registry.get_active()
        
        # Clean up old conversations if at capacity
        if len(self.conversations) >= self.max_conversations:
            self._cleanup_old_conversations()
        
        # Initialize conversation state if not exists
        if context_id not in self.conversations:
            self.conversations[context_id] = {
                "status": "active",
                "messages": [],
                "artifacts": {},
                "stage": "requirements",  # requirements -> application -> decision -> completed
                "patient_data": None,
                "questionnaire_response": None,
                "decision_bundle": None,
                "scenario_name": scenario_name,
                "config_tags": config.tags,
                "metadata": {
                    "scenario": scenario_name,
                    "tags": config.tags,
                    "created_at": self._get_timestamp()
                }
            }
        
        conv = self.conversations[context_id]
        response_messages = []
        
        # First turn - Administrator sends requirements message
        if incoming_text is None and not conv["messages"]:
            logger.info(f"📋 STAGE: requirements → Administrator sending {scenario_name} requirements")
            # Use scenario requirements instead of hardcoded BCS-E
            requirements_text = f"Please provide the following information for {scenario['label']} evaluation:\n\n{scenario['requirements']()}"
            
            # Add scenario examples if available
            if scenario.get('examples'):
                requirements_text += "\n\nExample payload format:\n" + json.dumps(scenario['examples'][0], indent=2)
            
            message = {
                "role": "administrator",
                "content": requirements_text,
                "timestamp": self._get_timestamp()
            }
            conv["messages"].append(message)
            response_messages.append(message)
            
            logger.info(f"✅ TURN END - Status: {conv['status']}, Messages: {len(response_messages)}, Artifacts: {len(conv['artifacts'])}")
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
            logger.info("🤖 STAGE: requirements → Applicant processing patient data and generating QuestionnaireResponse")
            
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
                logger.info(f"⚖️ STAGE: application → Administrator evaluating {scenario_name} eligibility")
                
                # Honor simulation settings
                self._apply_simulation_delay(config)
                
                # Check for error injection
                if self._should_inject_error(config):
                    decision = "failed"
                    rationale = "Injected error"
                    used_resources = []
                elif self._check_capacity_limit(config, scenario_name):
                    decision = "needs-more-info"
                    rationale = "Capacity limit reached - please try again later"
                    used_resources = []
                else:
                    # Use scenario evaluation instead of administrator agent
                    try:
                        # Convert questionnaire response to applicant payload
                        applicant_payload = self._extract_applicant_payload(conv["questionnaire_response"])
                        
                        # Prepare patient bundle
                        patient_bundle = conv["patient_data"] or {}
                        
                        # Trace pre-evaluation state
                        trace(context_id, "scenario", "evaluate_start", {
                            "scenario_name": scenario_name,
                            "applicant_payload": applicant_payload,
                            "patient_bundle_size": len(str(patient_bundle)),
                            "has_patient_data": bool(patient_bundle)
                        })
                        
                        # Call scenario evaluation
                        decision, rationale, used_resources = scenario["evaluate"](applicant_payload, patient_bundle)
                        
                        # Trace post-evaluation results
                        trace(context_id, "scenario", "evaluate_complete", {
                            "decision": decision,
                            "rationale": rationale,
                            "resources_used": used_resources,
                            "evaluation_success": True
                        })
                        
                    except Exception as e:
                        logger.error(f"Scenario evaluation error: {e}")
                        decision = "failed"
                        rationale = f"Evaluation error: {str(e)}"
                        used_resources = []
                        
                        # Trace evaluation error
                        trace(context_id, "scenario", "evaluate_error", {
                            "error": str(e),
                            "evaluation_success": False
                        })
                
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
                logger.info(f"🎯 DECISION: {decision} - {rationale[:50]}...")
                
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
                # Honor simulation settings
                self._apply_simulation_delay(config)
                
                # Check for error injection
                if self._should_inject_error(config):
                    decision = "failed"
                    rationale = "Injected error"
                    used_resources = []
                elif self._check_capacity_limit(config, scenario_name):
                    decision = "needs-more-info"
                    rationale = "Capacity limit reached - please try again later"
                    used_resources = []
                else:
                    # Use scenario evaluation instead of administrator agent
                    try:
                        # Convert questionnaire response to applicant payload
                        applicant_payload = self._extract_applicant_payload(conv["questionnaire_response"])
                        
                        # Prepare patient bundle
                        patient_bundle = conv["patient_data"] or {}
                        
                        # Trace pre-evaluation state
                        trace(context_id, "scenario", "evaluate_start", {
                            "scenario_name": scenario_name,
                            "applicant_payload": applicant_payload,
                            "patient_bundle_size": len(str(patient_bundle)),
                            "has_patient_data": bool(patient_bundle)
                        })
                        
                        # Call scenario evaluation
                        decision, rationale, used_resources = scenario["evaluate"](applicant_payload, patient_bundle)
                        
                        # Trace post-evaluation results
                        trace(context_id, "scenario", "evaluate_complete", {
                            "decision": decision,
                            "rationale": rationale,
                            "resources_used": used_resources,
                            "evaluation_success": True
                        })
                        
                    except Exception as e:
                        logger.error(f"Scenario evaluation error: {e}")
                        decision = "failed"
                        rationale = f"Evaluation error: {str(e)}"
                        used_resources = []
                        
                        # Trace evaluation error
                        trace(context_id, "scenario", "evaluate_error", {
                            "error": str(e),
                            "evaluation_success": False
                        })
                
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
            
        logger.info(f"✅ TURN END - Status: {conv['status']}, Messages: {len(response_messages)}, Artifacts: {len(conv['artifacts'])}, Stage: {conv['stage']}")
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
    
    def _apply_simulation_delay(self, config) -> None:
        """Apply simulation processing delay"""
        delay_ms = config.simulation.admin_processing_ms
        if delay_ms > 0:
            delay_seconds = delay_ms / 1000.0
            logger.info(f"⏱️ Simulating admin processing delay: {delay_ms}ms")
            time.sleep(delay_seconds)
    
    def _should_inject_error(self, config) -> bool:
        """Check if an error should be injected based on configuration"""
        error_rate = config.simulation.error_injection_rate
        if error_rate > 0:
            should_inject = random.random() < error_rate
            if should_inject:
                logger.info(f"💥 Injecting error (rate: {error_rate})")
            return should_inject
        return False
    
    def _check_capacity_limit(self, config, scenario_name: str) -> bool:
        """Check if capacity limit is reached for referral/prior_auth scenarios"""
        capacity_limit = config.simulation.capacity_limit
        
        # Only apply capacity limits to referral_specialist and prior_auth scenarios
        if scenario_name not in ["referral_specialist", "prior_auth"] or capacity_limit is None:
            return False
        
        # Initialize counter if not exists
        if scenario_name not in self.capacity_counters:
            self.capacity_counters[scenario_name] = 0
        
        # Check if limit reached
        if self.capacity_counters[scenario_name] >= capacity_limit:
            logger.info(f"🚫 Capacity limit reached for {scenario_name}: {capacity_limit}")
            return True
        
        # Increment counter
        self.capacity_counters[scenario_name] += 1
        logger.info(f"📊 Capacity usage for {scenario_name}: {self.capacity_counters[scenario_name]}/{capacity_limit}")
        return False
    
    def _extract_applicant_payload(self, questionnaire_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract applicant payload from QuestionnaireResponse for scenario evaluation"""
        payload = {}
        
        if not questionnaire_response or "item" not in questionnaire_response:
            return payload
        
        # Extract answers from QuestionnaireResponse items
        for item in questionnaire_response.get("item", []):
            link_id = item.get("linkId", "")
            answer = item.get("answer", [])
            
            if answer:
                # Get the first answer value
                first_answer = answer[0]
                if "valueString" in first_answer:
                    payload[link_id] = first_answer["valueString"]
                elif "valueInteger" in first_answer:
                    payload[link_id] = first_answer["valueInteger"]
                elif "valueDecimal" in first_answer:
                    payload[link_id] = first_answer["valueDecimal"]
                elif "valueBoolean" in first_answer:
                    payload[link_id] = first_answer["valueBoolean"]
                elif "valueDate" in first_answer:
                    payload[link_id] = first_answer["valueDate"]
                elif "valueCoding" in first_answer:
                    coding = first_answer["valueCoding"]
                    payload[link_id] = coding.get("code", coding.get("display", ""))
        
        logger.info(f"📝 Extracted applicant payload: {payload}")
        return payload
    
    def _cleanup_old_conversations(self) -> int:
        """Remove old conversations to free memory"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cleanup_hours)
        convs_to_remove = []
        
        for conv_id, conv in self.conversations.items():
            # Check if conversation has metadata with created_at
            if "metadata" in conv and "created_at" in conv["metadata"]:
                try:
                    created_time = datetime.fromisoformat(conv["metadata"]["created_at"].replace('Z', '+00:00'))
                    if created_time < cutoff_time:
                        convs_to_remove.append(conv_id)
                except (ValueError, TypeError):
                    # Remove conversations with invalid timestamps
                    convs_to_remove.append(conv_id)
        
        # Remove oldest conversations first if still over limit
        if len(convs_to_remove) < len(self.conversations) - self.max_conversations // 2:
            # Sort by created_at if available, otherwise remove arbitrary conversations
            sortable_convs = []
            for conv_id, conv in self.conversations.items():
                if conv_id not in convs_to_remove:
                    created_at = conv.get("metadata", {}).get("created_at", "")
                    sortable_convs.append((conv_id, created_at))
            
            sortable_convs.sort(key=lambda x: x[1])
            needed = len(self.conversations) - self.max_conversations // 2 - len(convs_to_remove)
            for conv_id, _ in sortable_convs[:needed]:
                convs_to_remove.append(conv_id)
        
        # Remove conversations
        for conv_id in convs_to_remove:
            del self.conversations[conv_id]
        
        if convs_to_remove:
            logger.info(f"🧹 Cleaned up {len(convs_to_remove)} old conversations")
        
        return len(convs_to_remove)

# Global conversation engine instance
conversation_engine = ConversationEngine()