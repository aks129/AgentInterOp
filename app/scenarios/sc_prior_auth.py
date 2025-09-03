"""
Prior authorization scenario implementation
"""
from typing import List, Dict, Tuple

LABEL = "Prior Authorization"
EXAMPLES = [
    "Expensive medication approval",
    "Advanced imaging authorization"
]

def requirements() -> str:
    """Return requirements for prior authorization"""
    return """
Prior Authorization Requirements:
- Valid prescription or order
- Clinical documentation supporting medical necessity
- Failed trial of first-line treatments (if applicable)
- Provider credentials verification
- Insurance coverage confirmation
"""

def evaluate(applicant_payload: dict, patient_bundle: dict) -> Tuple[str, str, List[dict]]:
    """
    Evaluate prior authorization request
    
    Returns:
        decision: "approved", "denied", or "pending"
        rationale: explanation of decision
        artifacts: list of supporting documents/data
    """
    patient = patient_bundle.get("entry", [{}])[0].get("resource", {})
    
    # Check for prescription/order
    has_prescription = "prescription" in str(applicant_payload).lower() or "order" in str(applicant_payload).lower()
    
    # Check for clinical justification
    has_clinical_docs = any(
        doc in str(patient_bundle).lower()
        for doc in ["diagnosis", "treatment", "history", "condition"]
    )
    
    # Check for prior treatments (simplified)
    has_prior_treatments = "previous" in str(patient_bundle).lower() or "failed" in str(patient_bundle).lower()
    
    # Authorization decision
    if has_prescription and has_clinical_docs and has_prior_treatments:
        decision = "approved"
        rationale = "Request includes valid prescription, clinical documentation, and evidence of prior treatment attempts."
    elif not has_prescription:
        decision = "denied"
        rationale = "Missing required prescription or provider order."
    elif not has_clinical_docs:
        decision = "pending"
        rationale = "Additional clinical documentation required to establish medical necessity."
    else:
        decision = "pending"
        rationale = "Documentation of prior treatment attempts required for approval."
    
    artifacts = [
        {
            "type": "prior_auth_decision",
            "content": {
                "patient_id": patient.get("id", "unknown"),
                "request_type": "Medication",
                "medical_necessity": has_clinical_docs,
                "prior_treatments_documented": has_prior_treatments,
                "decision": decision,
                "timestamp": "2025-09-03T22:20:00Z"
            }
        }
    ]
    
    return decision, rationale, artifacts