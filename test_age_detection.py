#!/usr/bin/env python3
"""Test age detection accuracy"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_age_detection():
    """Test that age 50 is detected correctly"""
    print("Testing age detection accuracy...")
    
    # Start conversation
    payload1 = {
        "jsonrpc": "2.0",
        "id": "age1",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "hello"}]
            }
        }
    }
    
    response1 = client.post("/api/bridge/demo/a2a", json=payload1)
    task_id = response1.json()["result"]["id"]
    
    # Provide age 50
    payload2 = {
        "jsonrpc": "2.0",
        "id": "age2",
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
    
    agent_msg = result2["history"][-1]["parts"][0]["text"]
    print(f"Agent response: {agent_msg}")
    
    # Should mention age 50, not 55
    assert "age 50" in agent_msg.lower()
    assert "age 55" not in agent_msg.lower()
    
    # Provide old mammogram date
    payload3 = {
        "jsonrpc": "2.0", 
        "id": "age3",
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
    
    final_msg = result3["history"][-1]["parts"][0]["text"]
    print(f"Final evaluation: {final_msg}")
    
    # Should show correct age in evaluation
    assert "age: 50" in final_msg.lower()
    assert "age: 55" not in final_msg.lower()
    
    print("OK Age detection works correctly!")

if __name__ == "__main__":
    test_age_detection()