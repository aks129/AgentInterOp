#!/usr/bin/env python3
"""Test the complete conversation flow with scheduling integration"""
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_complete_flow_with_scheduling():
    """Test complete BCS evaluation and scheduling flow"""
    print("Testing complete BCS conversation with scheduling...")
    
    # Message 1: Initial greeting
    payload1 = {
        "jsonrpc": "2.0",
        "id": "sched1",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "hello"}]
            }
        }
    }
    
    response1 = client.post("/api/bridge/demo/a2a", json=payload1)
    assert response1.status_code == 200
    result1 = response1.json()["result"]
    task_id = result1["id"]
    
    print(f"Agent: {result1['history'][-1]['parts'][0]['text']}")
    assert "age" in result1["history"][-1]["parts"][0]["text"].lower()
    
    # Message 2: Provide age  
    payload2 = {
        "jsonrpc": "2.0",
        "id": "sched2", 
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
    
    print(f"Agent: {result2['history'][-1]['parts'][0]['text']}")
    assert "mammogram" in result2["history"][-1]["parts"][0]["text"].lower()
    
    # Message 3: Provide mammogram date (old date to trigger eligible)
    payload3 = {
        "jsonrpc": "2.0",
        "id": "sched3",
        "method": "message/send", 
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "01/01/2020"}]  # 4+ years ago
            }
        }
    }
    
    response3 = client.post("/api/bridge/demo/a2a", json=payload3)
    result3 = response3.json()["result"]
    
    agent_msg3 = result3["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg3}")
    
    # Should show ELIGIBLE and offer scheduling
    assert "eligible" in agent_msg3.lower()
    assert "would you like me to help" in agent_msg3.lower()
    assert result3["status"]["state"] == "scheduling-offer"
    
    # Message 4: Request scheduling
    payload4 = {
        "jsonrpc": "2.0",
        "id": "sched4",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "yes, schedule my screening"}]
            }
        }
    }
    
    response4 = client.post("/api/bridge/demo/a2a", json=payload4)
    result4 = response4.json()["result"]
    
    agent_msg4 = result4["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg4}")
    
    # Should ask for location
    assert "zip code" in agent_msg4.lower() or "city" in agent_msg4.lower()
    assert result4["status"]["state"] == "location-request"
    
    # Message 5: Provide location
    payload5 = {
        "jsonrpc": "2.0",
        "id": "sched5",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "10001"}]  # NYC ZIP
            }
        }
    }
    
    response5 = client.post("/api/bridge/demo/a2a", json=payload5)
    result5 = response5.json()["result"]
    
    agent_msg5 = result5["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg5}")
    
    # Should show search results or explain no results found
    assert ("available" in agent_msg5.lower() or 
            "searched" in agent_msg5.lower() or 
            "didn't find" in agent_msg5.lower())
    assert result5["status"]["state"] == "completed"
    
    print("OK Complete BCS evaluation and scheduling flow works!")

if __name__ == "__main__":
    test_complete_flow_with_scheduling()