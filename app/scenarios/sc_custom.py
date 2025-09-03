"""
Custom scenario implementation - configurable logic
"""
from typing import Tuple, List, Dict, Any
from app.config import load_config
LABEL = "Custom (Config-Driven)"
EXAMPLES = [{"note": "Define custom rules in config.scenario.options"}]

def requirements() -> str:
    return ("Provide fields as specified by custom scenario options. "
            "Organizer can edit config.scenario.options to define keys & validations.")

def evaluate(applicant_payload: Dict[str, Any], patient_bundle: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, Any]]]:
    cfg = load_config().scenario.options or {}
    required = cfg.get("required_fields", [])
    for f in required:
        if f not in applicant_payload:
            return "needs-more-info", f"Missing required field: {f}", []
    return cfg.get("decision","eligible"), cfg.get("rationale","Custom rule passed."), []