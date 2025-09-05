from datetime import date, datetime
from typing import Dict, Any, Tuple, Optional, List

def _find_patient(bundle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the Patient resource in a FHIR Bundle"""
    for e in bundle.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") == "Patient":
            return r
    return None

def _by_code(bundle, rtype, system, code):
    """Find resources by type and coding"""
    out = []
    for e in bundle.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") == rtype:
            for c in (r.get("code", {}) or {}).get("coding", []):
                if c.get("system") == system and c.get("code") == code:
                    out.append(r)
    return out

def for_bcse(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Map FHIR Bundle to BCSE eligibility payload"""
    p = _find_patient(bundle) or {}
    birth = p.get("birthDate")
    sex = p.get("gender")
    mammo = None
    procs = _by_code(bundle, "Procedure", "http://www.ama-assn.org/go/cpt", "77067")
    if procs:
        mammo = procs[0].get("performedDateTime")
    return {"sex": sex, "birthDate": birth, "last_mammogram": mammo}

def for_trial(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Map FHIR Bundle to clinical trial payload"""
    # extremely simple placeholder; enrich later (Conditions, Observations)
    p = _find_patient(bundle) or {}
    return {"age_hint_birthDate": p.get("birthDate"), "condition": "", "biomarkers": {}}

def for_prior_auth(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Map FHIR Bundle to prior authorization payload"""
    return {"cpt": "", "diagnosis": "", "documentation": []}

def for_referral(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Map FHIR Bundle to referral specialist payload"""
    return {"specialty": "", "urgency": "routine", "patient_prefs": {}}

def map_for_scenario(scenario: str, bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Map FHIR Bundle to scenario-specific applicant payload"""
    return {
        "bcse": for_bcse,
        "clinical_trial": for_trial,
        "prior_auth": for_prior_auth,
        "referral_specialist": for_referral,
    }.get(scenario, lambda b: {})(bundle)