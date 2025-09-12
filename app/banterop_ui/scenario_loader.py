"""Scenario loading and caching"""
import json
import os
from typing import Dict, Optional
from urllib.parse import urlparse
import httpx
from .scenario_models import Scenario

# In-memory cache for scenarios
_scenario_cache: Dict[str, Scenario] = {}


async def fetch_scenario(url: str) -> Scenario:
    """
    Fetch and parse scenario from URL or local file.
    Caches results in memory keyed by URL.
    """
    # Check cache first
    if url in _scenario_cache:
        return _scenario_cache[url]
    
    scenario_data = None
    
    # Handle local files under /scenarios/*.json
    if url.startswith('file://') or url.startswith('./') or url.startswith('../'):
        file_path = url.replace('file://', '')
        if not os.path.isabs(file_path):
            # Relative paths are resolved from project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            file_path = os.path.join(base_dir, 'scenarios', file_path.lstrip('./'))
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
        else:
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
    
    # Handle HTTP(S) URLs
    elif url.startswith('http://') or url.startswith('https://'):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            scenario_data = response.json()
    
    else:
        # Try as local file name in scenarios directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        file_path = os.path.join(base_dir, 'scenarios', f"{url}.json")
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
        else:
            raise ValueError(f"Invalid scenario URL or file not found: {url}")
    
    if not scenario_data:
        raise ValueError(f"No scenario data found for: {url}")
    
    # Parse and validate scenario
    try:
        scenario = Scenario.parse_obj(scenario_data)
    except Exception as e:
        raise ValueError(f"Invalid scenario format: {e}")
    
    # Validate required fields
    if not scenario.metadata.id:
        raise ValueError("Scenario metadata.id is required")
    
    if not scenario.agents:
        raise ValueError("Scenario must have at least one agent")
    
    for agent in scenario.agents:
        if not agent.agentId:
            raise ValueError(f"Agent missing agentId: {agent}")
        if not agent.systemPrompt:
            raise ValueError(f"Agent {agent.agentId} missing systemPrompt")
    
    # Cache and return
    _scenario_cache[url] = scenario
    return scenario


def clear_scenario_cache():
    """Clear the scenario cache"""
    global _scenario_cache
    _scenario_cache = {}


def get_cached_scenarios() -> Dict[str, Scenario]:
    """Get all cached scenarios"""
    return _scenario_cache.copy()


def create_sample_bcs_scenario() -> Scenario:
    """Create a sample BCS scenario for testing"""
    return Scenario(
        metadata={
            "id": "bcs_eligibility_screening",
            "name": "Breast Cancer Screening Eligibility",
            "description": "Scenario for breast cancer screening eligibility evaluation",
            "version": "1.0.0",
            "tags": ["healthcare", "screening", "bcs"]
        },
        agents=[
            {
                "agentId": "applicant",
                "name": "Healthcare Consumer",
                "role": "applicant",
                "systemPrompt": "You are a healthcare consumer seeking breast cancer screening. Provide accurate information about your age, medical history, and previous screenings.",
                "goals": ["Get screening eligibility evaluation", "Schedule screening if eligible"],
                "messageToUseWhenInitiatingConversation": "Hello, I would like to know if I'm eligible for breast cancer screening."
            },
            {
                "agentId": "administrator",
                "name": "Healthcare Administrator",
                "role": "administrator", 
                "systemPrompt": "You are a healthcare administrator evaluating breast cancer screening eligibility. Follow AMA guidelines and provide clear guidance on screening recommendations.",
                "goals": ["Evaluate screening eligibility", "Provide scheduling guidance"],
                "tools": ["fhir_lookup", "bcs_evaluation", "scheduling_search"]
            }
        ],
        settings={
            "enableFhir": True,
            "enableBcsEvaluation": True,
            "enableScheduling": True
        }
    )