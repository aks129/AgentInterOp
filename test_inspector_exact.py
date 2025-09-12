#!/usr/bin/env python3
"""Test exact inspector behavior to debug evaluation display"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_inspector_exact_flow():
    """Test exactly what the inspector should be doing"""
    print("Testing exact inspector flow...")
    
    # Message 1: hello (new conversation)
    payload1 = {
        "jsonrpc": "2.0",
        "id": "inspector1",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "hello"}]
            }
        }
    }
    
    response1 = client.post("/api/bridge/demo/a2a", json=payload1)
    result1 = response1.json()["result"]
    task_id = result1["id"]
    
    print(f"Message 1 - Agent: {result1['history'][-1]['parts'][0]['text']}")
    print(f"Task ID: {task_id}")
    print(f"History length: {len(result1['history'])}")
    print()
    
    # Message 2: age (continue conversation)
    payload2 = {
        "jsonrpc": "2.0",
        "id": "inspector2",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "50"}]
            }
        }
    }
    
    response2 = client.post("/api/bridge/demo/a2a", json=payload2)
    result2 = response2.json()["result"]
    
    print(f"Message 2 - Agent: {result2['history'][-1]['parts'][0]['text']}")
    print(f"Task ID: {result2['id']} (should be same)")
    print(f"History length: {len(result2['history'])}")
    print()
    
    # Message 3: date (continue conversation)
    payload3 = {
        "jsonrpc": "2.0",
        "id": "inspector3",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "01/01/2021"}]
            }
        }
    }
    
    response3 = client.post("/api/bridge/demo/a2a", json=payload3)
    result3 = response3.json()["result"]
    
    print(f"Message 3 - Agent: {result3['history'][-1]['parts'][0]['text']}")
    print(f"Task ID: {result3['id']} (should be same)")
    print(f"History length: {len(result3['history'])}")
    print(f"Status: {result3['status']['state']}")
    
    # Check if evaluation is shown
    agent_response = result3['history'][-1]['parts'][0]['text']
    if "ELIGIBLE" in agent_response or "eligible" in agent_response:
        print("✓ Evaluation result is displayed correctly")
    else:
        print("✗ Evaluation result is NOT displayed - got generic message")
        print(f"Full response: '{agent_response}'")

if __name__ == "__main__":
    test_inspector_exact_flow()