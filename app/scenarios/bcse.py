from datetime import datetime, timedelta, date
from typing import Dict, Any

def _parse_date(d: str|None) -> date|None:
    if not d: return None
    try: return date.fromisoformat(d[:10])
    except: return None

def evaluate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal BCS: eligible if female AND 50-74 AND last_mammogram within 27 months.
    """
    sex = (payload.get("sex") or "").lower()
    birth = _parse_date(payload.get("birthDate"))
    last = _parse_date(payload.get("last_mammogram"))

    reasons = []
    now = date.today()
    age = None
    if birth:
        age = now.year - birth.year - ((now.month, now.day) < (birth.month, birth.day))

    # Checks
    if sex != "female": reasons.append("Requires female sex.")
    if age is None: reasons.append("Missing birthDate.")
    elif age < 50 or age > 74: reasons.append(f"Age {age} outside 50-74 window.")
    if not last: reasons.append("Missing last_mammogram date.")

    if reasons:
        # If only missing mammogram, ask for info; else ineligible
        if len(reasons)==1 and "Missing last_mammogram" in reasons[0]:
            return {"status":"needs-more-info","rationale":reasons,"request":"Provide prior mammogram date (CPT 77067) within last 27 months."}
        return {"status":"ineligible","rationale":reasons}

    months27 = last is not None and (now - last).days <= int(27*30.44)
    if months27:
        return {"status":"eligible","rationale":[f"Age {age}, female, mammogram within 27 months."]}
    else:
        return {"status":"needs-more-info","rationale":[f"Last mammogram older than 27 months."],"request":"Schedule screening mammogram."}

def map_fhir_bundle(bundle: Dict[str,Any]) -> Dict[str,Any]:
    """Very small mapper: Patient.birthDate, Patient.gender, Procedure CPT 77067 performedDateTime."""
    sex, birth, last = None, None, None
    for e in (bundle.get("entry") or []):
        r = e.get("resource") or {}
        rt = r.get("resourceType")
        if rt == "Patient":
            birth = r.get("birthDate") or birth
            sex = r.get("gender") or sex
        elif rt == "Procedure":
            code = (r.get("code") or {}).get("coding") or []
            for c in code:
                if c.get("system") == "http://www.ama-assn.org/go/cpt" and c.get("code") == "77067":
                    last = r.get("performedDateTime") or last
    return {"sex": sex, "birthDate": birth, "last_mammogram": last}