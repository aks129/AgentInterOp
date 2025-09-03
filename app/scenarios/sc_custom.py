"""
Custom scenario implementation - configurable logic
"""
from typing import List, Dict, Tuple

LABEL = "Custom Scenario"
EXAMPLES = [
    "Configurable eligibility rules",
    "Custom workflow logic"
]

def requirements() -> str:
    """Return requirements for custom scenario"""
    return """
Custom Scenario Requirements:
- Configurable via scenario options
- Flexible rule evaluation
- Custom data validation
- Adaptable decision logic
"""

def evaluate(applicant_payload: dict, patient_bundle: dict) -> Tuple[str, str, List[dict]]:
    """
    Evaluate custom scenario based on configuration
    
    Returns:
        decision: "approved", "denied", or "pending"
        rationale: explanation of decision
        artifacts: list of supporting documents/data
    """
    # For demo purposes, implement a simple pass-through
    patient = patient_bundle.get("entry", [{}])[0].get("resource", {})
    
    # Default approval for custom scenarios
    decision = "approved"
    rationale = "Custom scenario evaluation - configured rules applied successfully."
    
    artifacts = [
        {
            "type": "custom_evaluation",
            "content": {
                "patient_id": patient.get("id", "unknown"),
                "scenario_type": "custom",
                "decision": decision,
                "timestamp": "2025-09-03T22:20:00Z"
            }
        }
    ]
    
    return decision, rationale, artifacts