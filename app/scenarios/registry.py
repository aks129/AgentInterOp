from typing import Dict, Callable, Tuple, Any, List
from datetime import datetime
from app.config import load_config
# signature all scenarios must implement:
#   requirements() -> str
#   evaluate(applicant_payload: dict, patient_bundle: dict) -> (decision: str, rationale: str, artifacts: List[dict])

_SCENARIOS: Dict[str, Dict[str, Any]] = {}

def register(name: str, mod: Any):
    _SCENARIOS[name] = {
        "requirements": getattr(mod, "requirements"),
        "evaluate": getattr(mod, "evaluate"),
        "label": getattr(mod, "LABEL", name),
        "examples": getattr(mod, "EXAMPLES", []),
    }

def get_active():
    cfg = load_config()
    key = cfg.scenario.active
    if key not in _SCENARIOS:
        raise ValueError(f"Scenario '{key}' not registered")
    return key, _SCENARIOS[key]

def list_scenarios():
    return {k: {"label": v["label"]} for k, v in _SCENARIOS.items()}