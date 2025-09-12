#!/usr/bin/env python3
"""Test local inspector endpoint extraction"""
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_local_agent_card():
    """Test that our local agent card provides correct endpoint"""
    print("Testing local agent card endpoint extraction...")
    
    # Get our local agent card
    response = client.get("/.well-known/agent-card.json")
    assert response.status_code == 200
    
    agent_card = response.json()
    print(f"Local agent card: {json.dumps(agent_card, indent=2)}")
    
    # Check if it has the expected endpoints
    if "endpoints" in agent_card:
        print(f"Endpoints: {agent_card['endpoints']}")
    if "skills" in agent_card:
        print(f"Skills: {agent_card['skills']}")

def test_external_agent_card():
    """Test external agent card via proxy"""
    print("\nTesting external agent card endpoint extraction...")
    
    response = client.get("/api/proxy/agent-card?url=https://care-commons.meteorapp.com")
    assert response.status_code == 200
    
    result = response.json()
    agent_card = result["data"]
    
    print(f"External agent card URL field: {agent_card.get('url')}")
    print(f"External agent card endpoints: {agent_card.get('endpoints')}")
    print(f"External agent card additionalInterfaces: {agent_card.get('additionalInterfaces')}")

if __name__ == "__main__":
    test_local_agent_card()
    test_external_agent_card()