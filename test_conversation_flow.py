#!/usr/bin/env python3
"""Test the conversation flow for BCS evaluation"""
import json
import requests
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_complete_conversation():
    """Test a complete BCS evaluation conversation"""
    print("Testing complete BCS conversation flow...")
    
    # Message 1: Initial greeting
    payload1 = {
        "jsonrpc": "2.0",
        "id": "msg1",
        "method": "message/send",
        "params": {
            "content": "hello"
        }
    }
    
    response1 = client.post("/api/bridge/demo/a2a", json=payload1)
    assert response1.status_code == 200
    result1 = response1.json()["result"]
    task_id = result1["id"]
    
    # Check agent asks for age
    agent_msg1 = result1["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg1}")
    assert "age" in agent_msg1.lower()
    
    # Message 2: Provide age
    payload2 = {
        "jsonrpc": "2.0", 
        "id": "msg2",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "I am 55 years old"}]
            }
        }
    }
    
    response2 = client.post("/api/bridge/demo/a2a", json=payload2)
    assert response2.status_code == 200
    result2 = response2.json()["result"]
    
    # Check agent asks for mammogram date
    agent_msg2 = result2["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg2}")
    assert "mammogram" in agent_msg2.lower()
    
    # Message 3: Provide mammogram date
    payload3 = {
        "jsonrpc": "2.0",
        "id": "msg3", 
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "01/01/2021"}]
            }
        }
    }
    
    response3 = client.post("/api/bridge/demo/a2a", json=payload3)
    assert response3.status_code == 200
    result3 = response3.json()["result"]
    
    # Check agent provides evaluation
    agent_msg3 = result3["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg3}")
    assert "based on your information" in agent_msg3.lower()
    assert "age: 55" in agent_msg3.lower()
    assert result3["status"]["state"] == "completed"
    
    print("OK Complete conversation flow works correctly!")

def test_never_had_mammogram():
    """Test conversation when user never had a mammogram"""
    print("Testing 'never had mammogram' flow...")
    
    # Start conversation
    payload1 = {
        "jsonrpc": "2.0",
        "id": "never1",
        "method": "message/send", 
        "params": {"content": "hello"}
    }
    
    response1 = client.post("/api/bridge/demo/a2a", json=payload1)
    task_id = response1.json()["result"]["id"]
    
    # Provide age
    payload2 = {
        "jsonrpc": "2.0",
        "id": "never2",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "I am 60"}]
            }
        }
    }
    
    response2 = client.post("/api/bridge/demo/a2a", json=payload2)
    
    # Say never had mammogram
    payload3 = {
        "jsonrpc": "2.0",
        "id": "never3",
        "method": "message/send", 
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "I've never had one"}]
            }
        }
    }
    
    response3 = client.post("/api/bridge/demo/a2a", json=payload3)
    result3 = response3.json()["result"]
    
    # Check evaluation for never had mammogram
    agent_msg3 = result3["history"][-1]["parts"][0]["text"]
    print(f"Agent: {agent_msg3}")
    assert "never" in agent_msg3.lower() or "no previous" in agent_msg3.lower()
    assert result3["status"]["state"] == "completed"
    
    print("OK 'Never had mammogram' flow works correctly!")

if __name__ == "__main__":
    print("Testing BCS Conversation Flow...")
    print("=" * 50)
    test_complete_conversation()
    print()
    test_never_had_mammogram()
    print("=" * 50)
    print("All conversation flow tests passed!")