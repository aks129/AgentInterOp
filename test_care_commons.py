#!/usr/bin/env python3
"""Test care-commons integration via proxy"""
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_care_commons_agent_card():
    """Test fetching care-commons agent card"""
    print("Testing care-commons agent card proxy...")
    
    response = client.get("/api/proxy/agent-card?url=https://care-commons.meteorapp.com")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            agent_card = result["data"]
            print(f"Agent name: {agent_card.get('name')}")
            print(f"A2A endpoint: {agent_card.get('url')}")
            return agent_card.get('url')
        else:
            print(f"FAIL: {result.get('error')}")
    else:
        print(f"HTTP Error: {response.status_code}")
        print(response.text)
    return None

def test_care_commons_message(a2a_endpoint):
    """Test sending message to care-commons"""
    if not a2a_endpoint:
        print("No A2A endpoint available, skipping message test")
        return
        
    print(f"\nTesting message send to: {a2a_endpoint}")
    
    payload = {
        "target_url": a2a_endpoint,
        "payload": {
            "jsonrpc": "2.0",
            "id": "test-care-commons",
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{"kind": "text", "text": "hello from inspector test"}]
                }
            }
        }
    }
    
    response = client.post("/api/proxy/a2a-message", json=payload)
    print(f"Message proxy status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        if result.get("success"):
            print("OK Message sent successfully via proxy")
            data = result.get("data", {})
            if isinstance(data, dict):
                print(f"Response type: {type(data)}")
                print(f"Response keys: {list(data.keys()) if hasattr(data, 'keys') else 'Not a dict'}")
        else:
            print(f"FAIL: {result}")
    else:
        print(f"HTTP Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    endpoint = test_care_commons_agent_card()
    test_care_commons_message(endpoint)