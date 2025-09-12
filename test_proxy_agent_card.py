#!/usr/bin/env python3
"""Test the agent card proxy endpoint"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_proxy_agent_card():
    """Test fetching external agent card via proxy"""
    print("Testing agent card proxy...")
    
    # Test with care-commons URL
    test_url = "https://care-commons.meteorapp.com"
    response = client.get(f"/api/proxy/agent-card?url={test_url}")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("OK Successfully fetched agent card via proxy")
            agent_card = result["data"]
            print(f"Agent name: {agent_card.get('name', 'Unknown')}")
            print(f"Protocol version: {agent_card.get('protocolVersion', 'Unknown')}")
        else:
            print(f"FAIL Proxy returned error: {result.get('error')}")
    else:
        print(f"FAIL HTTP error: {response.status_code}")

if __name__ == "__main__":
    test_proxy_agent_card()