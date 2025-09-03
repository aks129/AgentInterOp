"""
Clinical Trial enrollment scenario implementation
"""
from typing import Tuple, List, Dict, Any
from datetime import date
LABEL = "Clinical Trial Matching (Oncology)"
EXAMPLES = [{
  "condition": "metastatic breast cancer",
  "stage": "IV",
  "biomarkers": {"HER2": "positive", "ER": "positive"},
  "age": 56,
  "prior_lines_of_therapy": 2
}]

def requirements() -> str:
    return ("Provide: primary diagnosis, stage, key biomarkers (e.g., HER2/ER/PR), "
            "ECOG performance status if available, prior lines of therapy, and inclusion/exclusion red flags "
            "(e.g., prior T-DXd).")

def evaluate(applicant_payload: Dict[str, Any], patient_bundle: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, Any]]]:
    # Simplified match rule for demo only
    cond = (applicant_payload.get("condition","") or "").lower()
    biomarkers = applicant_payload.get("biomarkers", {})
    lines = applicant_payload.get("prior_lines_of_therapy", 0)
    if "breast" in cond and biomarkers.get("HER2","").lower() in ["positive","pos","+"] and lines <= 2:
        return "eligible", "Matches HER2+ breast trial; ≤2 prior lines.", []
    if not cond or not biomarkers:
        return "needs-more-info", "Missing condition or biomarkers.", []
    return "ineligible", "Does not meet simplified biomarker/line criteria.", []