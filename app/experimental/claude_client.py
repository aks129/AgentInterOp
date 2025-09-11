import os
import httpx
import json
import asyncio
from typing import Dict, List, Any, Optional

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_AGENT = """You are a healthcare A2A agent. Be concise, safe, and cite inputs.
Output JSON:
{
 "role":"applicant|administrator",
 "state":"working|input-required|completed",
 "message":"short markdown",
 "actions":[
   {"kind":"request_info","fields":["..."]} |
   {"kind":"propose_decision","decision":"eligible|needs-more-info|ineligible","rationale":"..."} |
   {"kind":"request_docs","items":["..."]} |
   {"kind":"propose_slots","slots":[{"start":"...","end":"...","org":"...","location":"...","bookingLink":"..."}]}
 ],
 "artifacts": []
}
If you have nothing to do, set state to "input-required".
"""

async def claude_call(
    messages: List[Dict[str, str]], 
    model: str = "claude-3-5-sonnet-latest", 
    max_tokens: int = 800,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call the Anthropic Claude API with structured healthcare agent instructions.
    
    Args:
        messages: List of message objects with role and content
        model: Claude model to use
        max_tokens: Maximum tokens in response
        
    Returns:
        Parsed JSON response or error dict
    """
    # Use provided API key or fall back to environment variable
    effective_api_key = api_key or ANTHROPIC_API_KEY
    if not effective_api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}
        
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_AGENT,
        "messages": messages
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": effective_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            text_content = result["content"][0]["text"]
            
            # Parse the JSON response
            try:
                return json.loads(text_content)
            except json.JSONDecodeError as e:
                return {
                    "error": f"Failed to parse Claude response as JSON: {e}",
                    "raw_response": text_content
                }
                
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e.response.status_code} - {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Request error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def is_claude_available() -> bool:
    """Check if Claude API key is configured."""
    return bool(ANTHROPIC_API_KEY)

def get_claude_status() -> Dict[str, Any]:
    """Get Claude API status information."""
    return {
        "api_key_configured": is_claude_available(),
        "model": "claude-3-5-sonnet-latest",
        "ready": is_claude_available()
    }