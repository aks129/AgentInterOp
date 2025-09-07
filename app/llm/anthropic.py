import os, httpx, json

def get_anthropic_api_key() -> str:
    """Safely retrieve Anthropic API key from environment"""
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    if len(key) < 20 or not key.startswith("sk-"):
        raise ValueError("Invalid ANTHROPIC_API_KEY format")
    return key

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
    # Input validation
    if not narrative or len(narrative.strip()) < 10:
        raise ValueError("Narrative text too short or empty")
    if len(narrative) > 10000:  # Prevent abuse
        raise ValueError("Narrative text too long (max 10,000 characters)")
    
    api_key = get_anthropic_api_key()
    
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1200,
        "system": SYSTEM_NARRATIVE_TO_SCHEMA,
        "messages": [{"role": "user", "content": narrative}]
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:  # Reduced timeout
        r = await client.post("https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key, 
                "anthropic-version": "2023-06-01", 
                "content-type": "application/json"
            },
            json=payload)
        r.raise_for_status()
        data = r.json()
        text = data["content"][0]["text"]
        return json.loads(text)