"""
Specialist referral scenario implementation
"""
from typing import Tuple, List, Dict, Any
LABEL = "Referral to Specialist"
EXAMPLES = [{"specialty":"cardiology", "urgency":"urgent", "patient_prefs":{"distance_max_km":25}}]

def requirements() -> str:
    return ("Provide: specialty, urgency (routine/urgent), patient prefs (distance, language), "
            "and availability windows. Administrator may check capacity and propose slots.")

def evaluate(applicant_payload: Dict[str, Any], patient_bundle: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, Any]]]:
    urgency = (applicant_payload.get("urgency") or "routine").lower()
    # Fake capacity logic: urgent requests get first available; routine may wait
    if urgency == "urgent":
        return "eligible", "Slot proposed in 48 hours at nearest in-network provider.", []
    return "eligible", "Slot proposed next week per routine scheduling.", []