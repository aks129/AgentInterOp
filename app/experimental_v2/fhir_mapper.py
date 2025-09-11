"""
FHIR $everything to minimal facts mapper for autonomous BCS evaluation.
"""
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import asyncio


# Default mammogram procedure codes
DEFAULT_MAMMOGRAM_CODES = [
    {"system": "http://www.ama-assn.org/go/cpt", "code": "77067"},  # Screening mammography bilateral
    {"system": "http://www.ama-assn.org/go/cpt", "code": "77066"},  # Screening mammography unilateral  
    {"system": "http://loinc.org", "code": "24606-6"},             # Mammography study
    {"system": "http://loinc.org", "code": "36319-2"},             # Mammography
    {"system": "http://snomed.info/sct", "code": "71651007"},      # Mammography procedure
]


async def fetch_patient_everything(
    fhir_base_url: str, 
    patient_id: str, 
    bearer_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch patient $everything bundle from FHIR server.
    
    Args:
        fhir_base_url: Base URL of FHIR server
        patient_id: Patient resource ID
        bearer_token: Optional bearer token for authentication
        
    Returns:
        FHIR Bundle containing patient and related resources
    """
    url = f"{fhir_base_url.rstrip('/')}/Patient/{patient_id}/$everything"
    headers = {"Accept": "application/fhir+json"}
    
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"FHIR request failed: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        raise Exception(f"FHIR request error: {str(e)}")


def extract_minimal_facts(fhir_bundle: Dict[str, Any], mammogram_codes: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Extract minimal facts from FHIR bundle for BCS evaluation.
    
    Args:
        fhir_bundle: FHIR Bundle resource
        mammogram_codes: List of mammogram procedure codes to search for
        
    Returns:
        Minimal facts dictionary with sex, birthDate, and last_mammogram
    """
    if mammogram_codes is None:
        mammogram_codes = DEFAULT_MAMMOGRAM_CODES
    
    facts = {
        "sex": None,
        "birthDate": None,
        "last_mammogram": None,
        "extraction_timestamp": datetime.now().isoformat()
    }
    
    if not fhir_bundle.get("entry"):
        return facts
    
    patient_resource = None
    procedures = []
    observations = []
    
    # Find patient and relevant resources
    for entry in fhir_bundle["entry"]:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")
        
        if resource_type == "Patient":
            patient_resource = resource
        elif resource_type == "Procedure":
            procedures.append(resource)
        elif resource_type == "Observation":
            observations.append(resource)
    
    # Extract patient demographics
    if patient_resource:
        facts["sex"] = patient_resource.get("gender")
        facts["birthDate"] = patient_resource.get("birthDate")
    
    # Find most recent mammogram
    mammogram_dates = []
    
    # Check procedures
    for procedure in procedures:
        if is_mammogram_procedure(procedure, mammogram_codes):
            performed_date = extract_procedure_date(procedure)
            if performed_date:
                mammogram_dates.append(performed_date)
    
    # Check observations
    for observation in observations:
        if is_mammogram_observation(observation, mammogram_codes):
            effective_date = extract_observation_date(observation)
            if effective_date:
                mammogram_dates.append(effective_date)
    
    # Get most recent mammogram date
    if mammogram_dates:
        facts["last_mammogram"] = max(mammogram_dates)
    
    return facts


def is_mammogram_procedure(procedure: Dict[str, Any], mammogram_codes: List[Dict]) -> bool:
    """Check if procedure is a mammogram based on coding."""
    code_element = procedure.get("code", {})
    codings = code_element.get("coding", [])
    
    for coding in codings:
        system = coding.get("system")
        code = coding.get("code")
        
        for mammogram_code in mammogram_codes:
            if (mammogram_code.get("system") == system and 
                mammogram_code.get("code") == code):
                return True
    
    return False


def is_mammogram_observation(observation: Dict[str, Any], mammogram_codes: List[Dict]) -> bool:
    """Check if observation is mammogram-related based on coding."""
    code_element = observation.get("code", {})
    codings = code_element.get("coding", [])
    
    for coding in codings:
        system = coding.get("system")
        code = coding.get("code")
        
        for mammogram_code in mammogram_codes:
            if (mammogram_code.get("system") == system and 
                mammogram_code.get("code") == code):
                return True
    
    return False


def extract_procedure_date(procedure: Dict[str, Any]) -> Optional[str]:
    """Extract date from procedure resource."""
    # Try performedDateTime first
    if "performedDateTime" in procedure:
        return procedure["performedDateTime"][:10]  # YYYY-MM-DD
    
    # Try performedPeriod.start
    performed_period = procedure.get("performedPeriod", {})
    if "start" in performed_period:
        return performed_period["start"][:10]
    
    return None


def extract_observation_date(observation: Dict[str, Any]) -> Optional[str]:
    """Extract date from observation resource."""
    # Try effectiveDateTime first
    if "effectiveDateTime" in observation:
        return observation["effectiveDateTime"][:10]  # YYYY-MM-DD
    
    # Try effectivePeriod.start
    effective_period = observation.get("effectivePeriod", {})
    if "start" in effective_period:
        return effective_period["start"][:10]
    
    return None


def validate_minimal_facts(facts: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate extracted minimal facts for completeness.
    
    Returns:
        Dictionary with 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []
    
    if not facts.get("sex"):
        errors.append("Patient sex/gender not found")
    elif facts["sex"] not in ["male", "female"]:
        warnings.append(f"Unexpected sex value: {facts['sex']}")
    
    if not facts.get("birthDate"):
        errors.append("Patient birth date not found")
    else:
        try:
            birth_date = datetime.fromisoformat(facts["birthDate"]).date()
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 0 or age > 120:
                warnings.append(f"Unusual age calculated: {age} years")
        except ValueError:
            errors.append(f"Invalid birth date format: {facts['birthDate']}")
    
    if not facts.get("last_mammogram"):
        warnings.append("No mammogram history found in FHIR data")
    else:
        try:
            mammogram_date = datetime.fromisoformat(facts["last_mammogram"]).date()
            if mammogram_date > date.today():
                warnings.append("Mammogram date is in the future")
        except ValueError:
            errors.append(f"Invalid mammogram date format: {facts['last_mammogram']}")
    
    return {"errors": errors, "warnings": warnings}


# Test/demo functions
def create_demo_facts() -> Dict[str, Any]:
    """Create demo minimal facts for testing."""
    return {
        "sex": "female",
        "birthDate": "1969-08-10",
        "last_mammogram": "2024-05-01",
        "extraction_timestamp": datetime.now().isoformat()
    }


def create_test_cases() -> List[Dict[str, Any]]:
    """Create test cases for BCS evaluation."""
    return [
        {
            "name": "Eligible-RecentMammo",
            "description": "55-year-old female with recent mammogram - should be eligible",
            "facts": {
                "sex": "female",
                "birthDate": "1969-08-10", 
                "last_mammogram": "2024-05-01",
                "extraction_timestamp": datetime.now().isoformat()
            },
            "expected_outcome": "eligible"
        },
        {
            "name": "Needs-Info-NoHistory",
            "description": "60-year-old female with unknown mammogram history",
            "facts": {
                "sex": "female",
                "birthDate": "1964-03-15",
                "last_mammogram": None,
                "extraction_timestamp": datetime.now().isoformat()
            },
            "expected_outcome": "needs-more-info"
        },
        {
            "name": "Ineligible-Age", 
            "description": "40-year-old female - outside screening age range",
            "facts": {
                "sex": "female",
                "birthDate": "1984-06-20",
                "last_mammogram": "2023-06-01",
                "extraction_timestamp": datetime.now().isoformat()
            },
            "expected_outcome": "ineligible"
        }
    ]