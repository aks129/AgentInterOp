"""Agent card loading and A2A endpoint resolution"""
import httpx
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse

# In-memory cache for agent cards
_agentcard_cache: Dict[str, Dict[str, Any]] = {}


async def fetch_agent_card(url: str) -> Dict[str, Any]:
    """
    Fetch agent card and extract A2A endpoint information.
    
    Returns:
        {
            "url": "https://example.com/api/a2a",  # Resolved A2A endpoint
            "details": {
                "protocolVersion": "0.3.0",
                "name": "Agent Name", 
                "preferredTransport": "JSONRPC",
                "streaming": True,
                "raw": {...}  # Full agent card
            }
        }
    """
    # Check cache first
    if url in _agentcard_cache:
        return _agentcard_cache[url]
    
    # Sanitize URL - handle full agent card URLs
    clean_url = url
    if '/.well-known/agent-card.json' in url:
        clean_url = url.split('/.well-known/agent-card.json')[0]
    
    # Construct agent card URL
    if not clean_url.endswith('/.well-known/agent-card.json'):
        card_url = urljoin(clean_url + '/', '.well-known/agent-card.json')
    else:
        card_url = clean_url
    
    # Fetch agent card
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(card_url)
            response.raise_for_status()
            agent_card = response.json()
        except Exception as e:
            raise ValueError(f"Failed to fetch agent card from {card_url}: {e}")
    
    # Extract A2A endpoint and details
    result = extract_a2a_info(agent_card)
    
    # Cache and return
    _agentcard_cache[url] = result
    return result


def extract_a2a_info(agent_card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract A2A endpoint and relevant details from agent card.
    Supports various agent card formats.
    """
    details = {
        "protocolVersion": agent_card.get("protocolVersion"),
        "name": agent_card.get("name", "Unknown Agent"),
        "description": agent_card.get("description"),
        "preferredTransport": agent_card.get("preferredTransport", "JSONRPC"),
        "streaming": False,
        "raw": agent_card
    }
    
    # Extract streaming capability
    capabilities = agent_card.get("capabilities", {})
    if isinstance(capabilities, dict):
        details["streaming"] = capabilities.get("streaming", False)
    
    # Method 1: Direct url field (common in newer specs)
    a2a_url = agent_card.get("url")
    if a2a_url:
        return {"url": a2a_url, "details": details}
    
    # Method 2: endpoints.jsonrpc (older spec format)
    endpoints = agent_card.get("endpoints", {})
    if isinstance(endpoints, dict) and endpoints.get("jsonrpc"):
        return {"url": endpoints["jsonrpc"], "details": details}
    
    # Method 3: skills discovery URL (newer spec format)
    skills = agent_card.get("skills", [])
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict):
                discovery = skill.get("discovery", {})
                if isinstance(discovery, dict) and discovery.get("url"):
                    return {"url": discovery["url"], "details": details}
    
    # Method 4: additionalInterfaces
    additional_interfaces = agent_card.get("additionalInterfaces", [])
    if isinstance(additional_interfaces, list):
        for interface in additional_interfaces:
            if isinstance(interface, dict):
                transport = interface.get("transport", "").lower()
                if transport in ["jsonrpc", "json-rpc"] and interface.get("url"):
                    return {"url": interface["url"], "details": details}
    
    # Method 5: Try to construct from base URL
    provider = agent_card.get("provider", {})
    if isinstance(provider, dict) and provider.get("url"):
        base_url = provider["url"].rstrip('/')
        constructed_url = f"{base_url}/api/a2a"
        return {"url": constructed_url, "details": details}
    
    raise ValueError(f"Could not extract A2A endpoint from agent card: {agent_card.get('name', 'Unknown')}")


def clear_agentcard_cache():
    """Clear the agent card cache"""
    global _agentcard_cache
    _agentcard_cache = {}


def get_cached_agent_cards() -> Dict[str, Dict[str, Any]]:
    """Get all cached agent cards"""
    return _agentcard_cache.copy()


def get_preset_agent_cards() -> Dict[str, str]:
    """Get preset agent card URLs for quick testing"""
    return {
        "CareCommons": "https://care-commons.meteorapp.com",
        "AgentInterOp Local": "http://localhost:8000",
        "AgentInterOp Vercel": "https://agent-inter-op.vercel.app"
    }