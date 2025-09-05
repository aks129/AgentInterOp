import os, httpx, json

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_NARRATIVE_TO_SCHEMA = """You are an expert health IT architect. Convert the following scenario NARRATIVE into a JSON config with keys:
{
 "requirements": "string for admin opening requirements",
 "inputs": ["list of applicant fields"],
 "decision_rules": [{"if": "...", "then": "..."}],
 "fhir_hints": ["Patient", "Observation:code=...", "Procedure:77067"],
 "examples": [ { ... } ]
}
Only output JSON."""

async def narrative_to_json(narrative: str) -> dict:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1200,
        "system": SYSTEM_NARRATIVE_TO_SCHEMA,
        "messages": [{"role": "user", "content": narrative}]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post("https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY, 
                "anthropic-version": "2023-06-01", 
                "content-type": "application/json"
            },
            json=payload)
        r.raise_for_status()
        data = r.json()
        text = data["content"][0]["text"]
        return json.loads(text)