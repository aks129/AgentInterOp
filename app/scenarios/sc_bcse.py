"""
BCSE (Benefits Coverage Support Eligibility) scenario implementation
"""
from typing import Tuple, List, Dict, Any
from app.eligibility.bcse import evaluate_bcse
LABEL = "Breast Cancer Screening (BCS-E)"
EXAMPLES = [{"age": 56, "sex": "female", "last_mammogram": "2024-05-01"}]

def requirements() -> str:
    return ("Provide: sex, age (or birthDate), and last screening mammogram date "
            "(FHIR Procedure 77067, Observation, or abstracted note).")

def evaluate(applicant_payload: Dict[str, Any], patient_bundle: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, Any]]]:
    decision, rationale, used = evaluate_bcse(patient_bundle, applicant_payload)
    artifacts = used  # already FHIR resources
    return decision, rationale, artifacts