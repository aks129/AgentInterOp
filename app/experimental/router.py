from fastapi import APIRouter, HTTPException, Body
from typing import Any, Dict, List
from app.experimental.claude_client import claude_call, get_claude_status

router = APIRouter(prefix="/api/experimental", tags=["experimental"])

@router.post("/agent/respond")
async def agent_respond(payload: Dict[str, Any] = Body(...)):
    """
    Generate a role-specific response suggestion using Claude AI.
    
    payload: {
      "role": "applicant|administrator",
      "context": [{"role": "user|assistant", "content": "..."}],  // transcript summary/plain
      "facts": {"scenario": "bcse", "applicant_payload": {...}, "ingested": {...}},
      "hint": "requirements|docs|decision|slots|free"
    }
    
    Returns:
        {
            "ok": true,
            "result": {
                "role": "applicant|administrator",
                "state": "working|input-required|completed",
                "message": "short markdown",
                "actions": [...],
                "artifacts": [...]
            }
        }
    """
    try:
        # Validate required fields
        role = payload.get('role')
        if role not in ['applicant', 'administrator']:
            raise HTTPException(status_code=400, detail="Role must be 'applicant' or 'administrator'")
        
        context = payload.get('context', [])
        facts = payload.get('facts', {})
        hint = payload.get('hint', 'free')
        
        # Build context for Claude
        context_str = ""
        if context:
            context_str = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in context])
        
        facts_str = ""
        if facts:
            facts_str = f"Scenario: {facts.get('scenario', 'unknown')}\n"
            if facts.get('applicant_payload'):
                facts_str += f"Applicant Data: {facts['applicant_payload']}\n"
            if facts.get('ingested'):
                facts_str += f"Ingested Data: {facts['ingested']}\n"
        
        # Construct Claude message
        prompt = f"""ROLE: {role}
HINT: {hint}
FACTS:
{facts_str}
TRANSCRIPT:
{context_str}

Please analyze this healthcare agent interaction and provide a structured response following the JSON schema. Focus on being helpful while maintaining healthcare compliance and safety."""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        result = await claude_call(messages)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {"ok": True, "result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/agent/status")
async def agent_status():
    """Get Claude AI agent status and configuration."""
    return get_claude_status()

# BCS (Breast Cancer Screening) test cases
BCS_TESTS = [
    {
        "name": "Eligible-RecentMammo",
        "description": "Female, age 55, recent mammogram - should be eligible",
        "payload": {
            "sex": "female",
            "birthDate": "1969-08-10",
            "last_mammogram": "2024-05-01"
        },
        "expect": "eligible"
    },
    {
        "name": "Needs-Info-NoMammo", 
        "description": "Female, age 46, no mammogram history - needs more info",
        "payload": {
            "sex": "female",
            "birthDate": "1978-09-01"
        },
        "expect": "needs-more-info"
    },
    {
        "name": "Ineligible-Age",
        "description": "Female, age 25, recent mammogram - too young, ineligible",
        "payload": {
            "sex": "female", 
            "birthDate": "1999-02-01",
            "last_mammogram": "2023-06-01"
        },
        "expect": "ineligible"
    }
]

@router.get("/tests/bcse")
def bcse_tests():
    """Get BCS (Breast Cancer Screening) test cases for validation."""
    return {"tests": BCS_TESTS}

@router.post("/tests/bcse/run")
async def run_bcse_test(test_case: Dict[str, Any] = Body(...)):
    """
    Run a single BCS test case through Claude analysis.
    
    Args:
        test_case: Test case object with name, payload, and expected result
        
    Returns:
        Test result with pass/fail status and Claude's analysis
    """
    try:
        test_name = test_case.get('name', 'Unknown')
        payload = test_case.get('payload', {})
        expected = test_case.get('expect', '')
        
        # Create facts for Claude analysis
        facts = {
            "scenario": "bcse",
            "applicant_payload": payload,
            "test_case": test_name
        }
        
        # Ask Claude to make a decision
        claude_payload = {
            "role": "administrator",
            "context": [
                {"role": "user", "content": f"Please evaluate this breast cancer screening eligibility case: {payload}"}
            ],
            "facts": facts,
            "hint": "decision"
        }
        
        result = await agent_respond(claude_payload)
        
        if not result.get('ok'):
            return {
                "test_name": test_name,
                "passed": False,
                "error": "Failed to get Claude response",
                "expected": expected,
                "actual": None
            }
        
        claude_result = result['result']
        
        # Extract decision from Claude's actions
        actual_decision = None
        for action in claude_result.get('actions', []):
            if action.get('kind') == 'propose_decision':
                actual_decision = action.get('decision')
                break
        
        # Check if it matches expected
        passed = actual_decision == expected
        
        return {
            "test_name": test_name,
            "passed": passed,
            "expected": expected,
            "actual": actual_decision,
            "claude_response": claude_result,
            "payload": payload
        }
        
    except Exception as e:
        return {
            "test_name": test_case.get('name', 'Unknown'),
            "passed": False,
            "error": str(e),
            "expected": test_case.get('expect'),
            "actual": None
        }

@router.post("/narrative/parse")
async def parse_narrative(request: Dict[str, Any] = Body(...)):
    """
    Parse a clinical narrative into structured JSON using Claude.
    
    Args:
        request: {"narrative": "free text clinical narrative", "target_schema": "bcse|clinical_trial|prior_auth"}
        
    Returns:
        Structured JSON payload parsed from the narrative
    """
    try:
        narrative = request.get('narrative', '')
        target_schema = request.get('target_schema', 'bcse')
        
        if not narrative.strip():
            raise HTTPException(status_code=400, detail="Narrative text is required")
        
        prompt = f"""Parse this clinical narrative into structured JSON for a {target_schema} scenario:

NARRATIVE:
{narrative}

Extract relevant clinical data and format it as a structured JSON object appropriate for healthcare interoperability. Focus on demographics, clinical history, and scenario-relevant information."""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        result = await claude_call(messages)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {"ok": True, "parsed_data": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse narrative: {str(e)}")