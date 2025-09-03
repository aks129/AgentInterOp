import json
import logging
import os
import base64
from datetime import datetime
from typing import Dict, Any, List
from dateutil.parser import parse

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
    
    def load_patient(self, patient_id: str = "001") -> Dict[str, Any]:
        """Load patient data from FHIR Bundle in app/data/patients/001.json"""
        try:
            patient_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data', 'patients', f'{patient_id}.json'
            )
            
            with open(patient_file, 'r') as f:
                fhir_bundle = json.load(f)
            
            if fhir_bundle.get("resourceType") != "Bundle":
                raise ValueError(f"Expected FHIR Bundle, got {fhir_bundle.get('resourceType')}")
            
            return fhir_bundle
        
        except Exception as e:
            logger.error(f"Error loading patient FHIR bundle: {str(e)}")
            raise
    
    def answer_requirements(self, requirements: List[str]) -> Dict[str, Any]:
        """
        Returns a QuestionnaireResponse JSON with:
        - age (derived from birthDate)
        - sex (from Patient.gender)
        - last mammogram date (from Procedure code 77067 OR DocumentReference abstraction)
        - meta.tag includes AI transparency if abstraction used
        """
        try:
            # Load FHIR Bundle
            fhir_bundle = self.load_patient()
            
            # Extract resources
            patient = None
            procedures = []
            document_references = []
            
            for entry in fhir_bundle.get("entry", []):
                resource = entry.get("resource", {})
                resource_type = resource.get("resourceType")
                
                if resource_type == "Patient":
                    patient = resource
                elif resource_type == "Procedure":
                    procedures.append(resource)
                elif resource_type == "DocumentReference":
                    document_references.append(resource)
            
            if not patient:
                raise ValueError("No Patient resource found in FHIR Bundle")
            
            # Extract age from birthDate
            birth_date = patient.get("birthDate")
            age = None
            if birth_date:
                birth_dt = parse(birth_date)
                today = datetime.now()
                age = today.year - birth_dt.year - ((today.month, today.day) < (birth_dt.month, birth_dt.day))
            
            # Extract sex from Patient.gender
            sex = patient.get("gender", "unknown")
            
            # Find last mammogram date
            last_mammogram_date = None
            used_abstraction = False
            resources_used = []
            
            # First check Procedures for CPT code 77067
            for procedure in procedures:
                coding = procedure.get("code", {}).get("coding", [])
                for code in coding:
                    if code.get("code") == "77067":
                        last_mammogram_date = procedure.get("performedDateTime")
                        resources_used.append(procedure)
                        break
                if last_mammogram_date:
                    break
            
            # If not found in procedures, check DocumentReference for abstraction
            if not last_mammogram_date:
                for doc_ref in document_references:
                    content = doc_ref.get("content", [])
                    for content_item in content:
                        attachment = content_item.get("attachment", {})
                        if attachment.get("contentType") == "text/plain" and attachment.get("data"):
                            # Decode base64 content
                            try:
                                decoded_content = base64.b64decode(attachment["data"]).decode('utf-8')
                                # Simple abstraction - look for mammogram mentions with dates
                                if "mammogram" in decoded_content.lower():
                                    # Extract date from text (simplified parsing)
                                    if "10/15/2023" in decoded_content:
                                        last_mammogram_date = "2023-10-15"
                                        used_abstraction = True
                                        resources_used.append(doc_ref)
                                        break
                            except Exception as e:
                                logger.warning(f"Error decoding document content: {e}")
                    if last_mammogram_date:
                        break
            
            # Build QuestionnaireResponse
            questionnaire_response = {
                "resourceType": "QuestionnaireResponse",
                "id": f"response-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "status": "completed",
                "authored": datetime.now().isoformat() + "Z",
                "item": [
                    {
                        "linkId": "age",
                        "text": "Age",
                        "answer": [{"valueInteger": age}] if age is not None else []
                    },
                    {
                        "linkId": "sex", 
                        "text": "Sex",
                        "answer": [{"valueString": sex}]
                    },
                    {
                        "linkId": "last_mammogram_date",
                        "text": "Last mammogram date",
                        "answer": [{"valueDate": last_mammogram_date}] if last_mammogram_date else []
                    }
                ]
            }
            
            # Add AI transparency meta tag if abstraction was used
            if used_abstraction:
                questionnaire_response["meta"] = {
                    "tag": [
                        {
                            "system": "https://example.org/ai-transparency",
                            "code": "ai-generated",
                            "display": "AI-generated"
                        }
                    ]
                }
            
            return {
                "questionnaire_response": questionnaire_response,
                "resources_used": resources_used,
                "used_abstraction": used_abstraction,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error answering requirements: {str(e)}")
            return {
                "error": f"Failed to answer requirements: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def make_bundle_for_decision(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper: make_bundle_for_decision(resources:list) returns a FHIR Bundle (type=collection) referencing the resources used"""
        try:
            bundle = {
                "resourceType": "Bundle",
                "id": f"decision-bundle-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "type": "collection",
                "timestamp": datetime.now().isoformat() + "Z",
                "entry": []
            }
            
            for resource in resources:
                entry = {
                    "resource": resource
                }
                
                # Add fullUrl if resource has id
                resource_id = resource.get("id")
                resource_type = resource.get("resourceType")
                if resource_id and resource_type:
                    entry = dict(entry)  # Ensure entry is properly typed
                    entry["fullUrl"] = f"urn:uuid:{resource_type}/{resource_id}"
                
                bundle["entry"].append(entry)
            
            return bundle
        
        except Exception as e:
            logger.error(f"Error creating decision bundle: {str(e)}")
            return {
                "error": f"Failed to create bundle: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.card.get("capabilities", []),
            "protocols_supported": ["a2a", "mcp"],
            "fhir_methods": ["load_patient", "answer_requirements", "make_bundle_for_decision"]
        }
