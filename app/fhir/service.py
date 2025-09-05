from typing import Optional, Dict, Any
from app.config import load_config, save_config, update_config
from .connector import FhirConnector


async def build_connector():
    cfg = load_config()
    fhir_options = cfg.data.options if hasattr(cfg.data, 'options') else {}
    base = fhir_options.get("fhir_base")
    token = fhir_options.get("fhir_token")
    if not base:
        raise ValueError("FHIR base URL not configured")
    return FhirConnector(base, token)