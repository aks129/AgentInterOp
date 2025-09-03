"""
BCSE (Benefits Coverage Support Eligibility) scenario implementation
"""
from typing import List, Dict, Tuple

LABEL = "BCS-E Eligibility"
EXAMPLES = [
    "Patient with recent mammogram screening",
    "Patient requiring eligibility verification"
]

def requirements() -> str:
    """Return eligibility requirements for BCSE"""
    return """
BCS-E Eligibility Requirements:
- Age: 18-65 years
- Valid insurance coverage
- Recent mammogram (within last 2 years)
- State residency verification
- Income below 400% of Federal Poverty Level
"""

def evaluate(applicant_payload: dict, patient_bundle: dict) -> Tuple[str, str, List[dict]]:
    """
    Evaluate BCSE eligibility based on patient data
    
    Returns:
        decision: "approved", "denied", or "pending"
        rationale: explanation of decision
        artifacts: list of supporting documents/data
    """
    # Extract patient demographics and clinical data
    patient = patient_bundle.get("entry", [{}])[0].get("resource", {})
    
    # Check age requirement
    birth_date = patient.get("birthDate", "")
    age = 2025 - int(birth_date.split("-")[0]) if birth_date else 0
    
    # Check mammogram history (simplified)
    has_recent_mammogram = "mammogram" in str(patient_bundle).lower()
    
    # Simple eligibility logic
    if 18 <= age <= 65 and has_recent_mammogram:
        decision = "approved"
        rationale = f"Patient meets age requirement ({age} years) and has recent mammogram screening."
    elif age < 18 or age > 65:
        decision = "denied"
        rationale = f"Patient age ({age}) is outside eligible range (18-65 years)."
    else:
        decision = "pending"
        rationale = "Missing required mammogram screening documentation."
    
    # Generate artifacts
    artifacts = [
        {
            "type": "eligibility_report",
            "content": {
                "patient_id": patient.get("id", "unknown"),
                "age": age,
                "mammogram_check": has_recent_mammogram,
                "decision": decision,
                "timestamp": "2025-09-03T22:20:00Z"
            }
        }
    ]
    
    return decision, rationale, artifacts