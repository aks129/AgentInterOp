"""
Specialist referral scenario implementation
"""
from typing import List, Dict, Tuple

LABEL = "Specialist Referral"
EXAMPLES = [
    "Cardiology referral for chest pain",
    "Dermatology consultation request"
]

def requirements() -> str:
    """Return requirements for specialist referral"""
    return """
Specialist Referral Requirements:
- Primary care physician referral
- Relevant clinical documentation
- Insurance pre-authorization (if required)
- Medical necessity justification
- Patient consent for specialist consultation
"""

def evaluate(applicant_payload: dict, patient_bundle: dict) -> Tuple[str, str, List[dict]]:
    """
    Evaluate specialist referral request
    
    Returns:
        decision: "approved", "denied", or "pending"
        rationale: explanation of decision
        artifacts: list of supporting documents/data
    """
    patient = patient_bundle.get("entry", [{}])[0].get("resource", {})
    
    # Check for referral documentation
    has_referral = "referral" in str(applicant_payload).lower()
    has_symptoms = any(
        symptom in str(patient_bundle).lower()
        for symptom in ["pain", "symptoms", "condition", "diagnosis"]
    )
    
    # Check insurance status (simplified)
    has_insurance = patient.get("insurance", True)  # Default assume covered
    
    # Referral decision logic
    if has_referral and has_symptoms and has_insurance:
        decision = "approved"
        rationale = "Referral request includes proper documentation, medical justification, and insurance coverage."
    elif not has_referral:
        decision = "denied"
        rationale = "Missing required primary care physician referral documentation."
    elif not has_insurance:
        decision = "pending"
        rationale = "Insurance pre-authorization required before specialist consultation."
    else:
        decision = "pending"
        rationale = "Additional clinical documentation needed to support medical necessity."
    
    artifacts = [
        {
            "type": "referral_authorization",
            "content": {
                "patient_id": patient.get("id", "unknown"),
                "referring_provider": "Primary Care",
                "specialist_type": "Cardiology",
                "medical_necessity": has_symptoms,
                "decision": decision,
                "timestamp": "2025-09-03T22:20:00Z"
            }
        }
    ]
    
    return decision, rationale, artifacts