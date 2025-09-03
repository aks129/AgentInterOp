"""
Prior authorization scenario implementation
"""
from typing import Tuple, List, Dict, Any
LABEL = "Prior Authorization"
EXAMPLES = [{"cpt":"97110", "diagnosis":"M54.5", "documentation":["PT_plan.pdf"], "site_of_service":"11"}]

def requirements() -> str:
    return ("Provide: procedure code (CPT/HCPCS), diagnosis (ICD-10), site of service (POS), "
            "and documentation (conservative therapy tried/failed).")

def evaluate(applicant_payload: Dict[str, Any], patient_bundle: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, Any]]]:
    cpt = applicant_payload.get("cpt")
    docs = applicant_payload.get("documentation",[])
    if not cpt:
        return "needs-more-info", "Missing CPT/HCPCS.", []
    if cpt in ["77067","70551"] or ("PT_plan.pdf" in docs):
        return "eligible", "Criteria met or adequate documentation provided.", []
    return "ineligible", "Insufficient documentation for coverage per simplified rule.", []