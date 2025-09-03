"""
Clinical Trial enrollment scenario implementation
"""
from typing import List, Dict, Tuple

LABEL = "Clinical Trial Enrollment"
EXAMPLES = [
    "Oncology trial eligibility",
    "Cardiovascular study screening"
]

def requirements() -> str:
    """Return requirements for clinical trial enrollment"""
    return """
Clinical Trial Enrollment Requirements:
- Age: 21-75 years
- Specific medical condition diagnosis
- No prior participation in conflicting studies
- Informed consent capability
- Geographic accessibility to trial site
"""

def evaluate(applicant_payload: dict, patient_bundle: dict) -> Tuple[str, str, List[dict]]:
    """
    Evaluate clinical trial eligibility
    
    Returns:
        decision: "approved", "denied", or "pending"
        rationale: explanation of decision
        artifacts: list of supporting documents/data
    """
    patient = patient_bundle.get("entry", [{}])[0].get("resource", {})
    
    # Check age requirement for trial
    birth_date = patient.get("birthDate", "")
    age = 2025 - int(birth_date.split("-")[0]) if birth_date else 0
    
    # Check for relevant conditions (simplified)
    has_target_condition = any(
        condition in str(patient_bundle).lower() 
        for condition in ["cancer", "diabetes", "hypertension"]
    )
    
    # Eligibility decision
    if 21 <= age <= 75 and has_target_condition:
        decision = "approved"
        rationale = f"Patient meets age criteria ({age} years) and has relevant medical condition for trial participation."
    elif age < 21 or age > 75:
        decision = "denied"
        rationale = f"Patient age ({age}) is outside trial criteria (21-75 years)."
    else:
        decision = "pending"
        rationale = "Requires medical review to confirm trial-specific condition criteria."
    
    artifacts = [
        {
            "type": "trial_screening_report",
            "content": {
                "patient_id": patient.get("id", "unknown"),
                "age": age,
                "condition_match": has_target_condition,
                "trial_phase": "Phase II",
                "decision": decision,
                "timestamp": "2025-09-03T22:20:00Z"
            }
        }
    ]
    
    return decision, rationale, artifacts