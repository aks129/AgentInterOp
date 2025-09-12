#!/usr/bin/env python3
"""Test A2A message proxy endpoint"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_message_proxy():
    """Test sending A2A message via proxy"""
    print("Testing A2A message proxy...")
    
    # Test payload for local agent first
    payload = {
        "target_url": "http://testserver/api/bridge/demo/a2a",
        "payload": {
            "jsonrpc": "2.0",
            "id": "proxy-test",
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{"kind": "text", "text": "hello from proxy"}]
                }
            }
        }
    }
    
    response = client.post("/api/proxy/a2a-message", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        if result.get("success"):
            print("OK Message proxy works locally")
            # Check if we got a proper A2A response
            data = result.get("data", {})
            if isinstance(data, dict) and "jsonrpc" in data:
                print(f"Got JSON-RPC response with ID: {data.get('id')}")
        else:
            print(f"FAIL Proxy returned unsuccessful response: {result}")
    else:
        print(f"FAIL HTTP error: {response.status_code}")
        try:
            print(f"Error details: {response.json()}")
        except:
            print(f"Response text: {response.text}")

if __name__ == "__main__":
    test_message_proxy()