"""MCP-FHIR bridge for patient data retrieval"""
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import re


async def fetch_patient_everything(
    base_url: str, 
    patient_id: str, 
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch patient $everything bundle from FHIR server.
    
    Args:
        base_url: FHIR server base URL
        patient_id: Patient identifier
        token: Optional Bearer token for authentication
    
    Returns:
        Dictionary with patient bundle data
    """
    # Construct $everything URL
    everything_url = f"{base_url.rstrip('/')}/Patient/{patient_id}/$everything"
    
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(everything_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise ValueError(f"Failed to fetch patient data from {everything_url}: {e}")


def extract_minimal_facts(fhir_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract minimal patient facts from FHIR $everything bundle.
    
    Returns:
        {
            "patientId": "123",
            "sex": "female", 
            "birthDate": "1970-01-01",
            "age": 54,
            "last_mammogram_date": "2023-01-15",
            "relevant_procedures": [...],
            "relevant_observations": [...]
        }
    """
    facts = {
        "patientId": None,
        "sex": None,
        "birthDate": None,
        "age": None,
        "last_mammogram_date": None,
        "relevant_procedures": [],
        "relevant_observations": []
    }
    
    if not isinstance(fhir_bundle, dict):
        return facts
    
    entries = fhir_bundle.get("entry", [])
    if not isinstance(entries, list):
        return facts
    
    # Process each resource in the bundle
    for entry in entries:
        resource = entry.get("resource", {})
        if not isinstance(resource, dict):
            continue
        
        resource_type = resource.get("resourceType")
        
        # Extract patient demographics
        if resource_type == "Patient":
            facts["patientId"] = resource.get("id")
            facts["sex"] = resource.get("gender")
            birth_date = resource.get("birthDate")
            if birth_date:
                facts["birthDate"] = birth_date
                facts["age"] = calculate_age(birth_date)
        
        # Extract procedures (looking for mammograms)
        elif resource_type == "Procedure":
            code = resource.get("code", {})
            if is_mammogram_procedure(code):
                performed_date = extract_date_from_procedure(resource)
                if performed_date:
                    facts["relevant_procedures"].append({
                        "type": "mammogram",
                        "date": performed_date,
                        "status": resource.get("status"),
                        "code": code
                    })
                    
                    # Update last mammogram date
                    if not facts["last_mammogram_date"] or performed_date > facts["last_mammogram_date"]:
                        facts["last_mammogram_date"] = performed_date
        
        # Extract observations (looking for breast cancer screening related)
        elif resource_type == "Observation":
            code = resource.get("code", {})
            if is_breast_screening_observation(code):
                effective_date = extract_date_from_observation(resource)
                facts["relevant_observations"].append({
                    "type": "breast_screening",
                    "date": effective_date,
                    "status": resource.get("status"),
                    "code": code,
                    "value": resource.get("valueString") or resource.get("valueCodeableConcept")
                })
    
    return facts


def calculate_age(birth_date: str) -> Optional[int]:
    """Calculate age from birth date string"""
    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth.year
        if today.month < birth.month or (today.month == birth.month and today.day < birth.day):
            age -= 1
        return age
    except:
        return None


def is_mammogram_procedure(code: Dict[str, Any]) -> bool:
    """Check if procedure code indicates a mammogram"""
    if not isinstance(code, dict):
        return False
    
    # Common mammogram CPT codes
    mammogram_codes = [
        "77067",  # Screening mammography
        "77066",  # Diagnostic mammography
        "77065",  # Digital breast tomosynthesis
        "G0202",  # Screening mammography
        "G0204",  # Diagnostic mammography
    ]
    
    codings = code.get("coding", [])
    if not isinstance(codings, list):
        return False
    
    for coding in codings:
        if isinstance(coding, dict):
            code_value = coding.get("code", "")
            system = coding.get("system", "")
            
            # Check CPT codes
            if "cpt" in system.lower() and code_value in mammogram_codes:
                return True
            
            # Check for mammogram in display text
            display = coding.get("display", "").lower()
            if any(term in display for term in ["mammogram", "mammography", "breast imaging"]):
                return True
    
    return False


def is_breast_screening_observation(code: Dict[str, Any]) -> bool:
    """Check if observation code is related to breast cancer screening"""
    if not isinstance(code, dict):
        return False
    
    # Common breast screening LOINC codes
    screening_codes = [
        "72133-2",  # Breast cancer screening
        "72134-0",  # Mammography screening
        "33747-0",  # Mammography report
    ]
    
    codings = code.get("coding", [])
    if not isinstance(codings, list):
        return False
    
    for coding in codings:
        if isinstance(coding, dict):
            code_value = coding.get("code", "")
            system = coding.get("system", "")
            
            # Check LOINC codes
            if "loinc" in system.lower() and code_value in screening_codes:
                return True
            
            # Check for breast screening in display text
            display = coding.get("display", "").lower()
            if any(term in display for term in ["breast", "mammogram", "screening"]):
                return True
    
    return False


def extract_date_from_procedure(procedure: Dict[str, Any]) -> Optional[str]:
    """Extract performed date from procedure resource"""
    if not isinstance(procedure, dict):
        return None
    
    # Try performedDateTime
    performed_date = procedure.get("performedDateTime")
    if performed_date:
        return performed_date[:10]  # Extract YYYY-MM-DD
    
    # Try performedPeriod.start
    performed_period = procedure.get("performedPeriod", {})
    if isinstance(performed_period, dict):
        start_date = performed_period.get("start")
        if start_date:
            return start_date[:10]
    
    return None


def extract_date_from_observation(observation: Dict[str, Any]) -> Optional[str]:
    """Extract effective date from observation resource"""
    if not isinstance(observation, dict):
        return None
    
    # Try effectiveDateTime
    effective_date = observation.get("effectiveDateTime")
    if effective_date:
        return effective_date[:10]  # Extract YYYY-MM-DD
    
    # Try effectivePeriod.start
    effective_period = observation.get("effectivePeriod", {})
    if isinstance(effective_period, dict):
        start_date = effective_period.get("start")
        if start_date:
            return start_date[:10]
    
    return None


def get_configurable_codes() -> Dict[str, List[str]]:
    """Get configurable procedure and observation codes"""
    return {
        "mammogram_cpt_codes": [
            "77067",  # Screening mammography
            "77066",  # Diagnostic mammography
            "77065",  # Digital breast tomosynthesis
            "G0202",  # Screening mammography
            "G0204",  # Diagnostic mammography
        ],
        "breast_screening_loinc_codes": [
            "72133-2",  # Breast cancer screening
            "72134-0",  # Mammography screening
            "33747-0",  # Mammography report
        ]
    }