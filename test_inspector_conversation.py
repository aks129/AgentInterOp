#!/usr/bin/env python3
"""Test the inspector conversation flow with task ID preservation"""
import json
import requests
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_inspector_conversation_flow():
    """Test that task IDs are properly preserved in inspector conversations"""
    print("Testing inspector conversation with task ID preservation...")
    
    # Message 1: Initial greeting (no taskId, should create new task)
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
    assert response1.status_code == 200
    result1 = response1.json()["result"]
    task_id = result1["id"]
    
    print(f"Created task: {task_id}")
    print(f"Agent response: {result1['history'][-1]['parts'][0]['text']}")
    assert len(result1["history"]) == 2  # User + Agent message
    assert "age" in result1["history"][-1]["parts"][0]["text"].lower()
    
    # Message 2: Provide age (with taskId to continue conversation)
    payload2 = {
        "jsonrpc": "2.0", 
        "id": "inspector2",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,  # Continue same conversation
                "parts": [{"kind": "text", "text": "I am 55 years old"}]
            }
        }
    }
    
    response2 = client.post("/api/bridge/demo/a2a", json=payload2)
    assert response2.status_code == 200
    result2 = response2.json()["result"]
    
    print(f"Task ID should be same: {result2['id']} == {task_id}")
    assert result2["id"] == task_id  # Same task
    print(f"Agent response: {result2['history'][-1]['parts'][0]['text']}")
    assert len(result2["history"]) == 4  # 2 user + 2 agent messages
    assert "mammogram" in result2["history"][-1]["parts"][0]["text"].lower()
    
    # Message 3: Provide mammogram date (with taskId)
    payload3 = {
        "jsonrpc": "2.0",
        "id": "inspector3", 
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,  # Continue same conversation
                "parts": [{"kind": "text", "text": "01/01/2021"}]
            }
        }
    }
    
    response3 = client.post("/api/bridge/demo/a2a", json=payload3)
    assert response3.status_code == 200
    result3 = response3.json()["result"]
    
    print(f"Final task ID: {result3['id']} == {task_id}")
    assert result3["id"] == task_id  # Same task
    print(f"Final agent response: {result3['history'][-1]['parts'][0]['text']}")
    assert len(result3["history"]) == 6  # 3 user + 3 agent messages
    assert "based on your information" in result3["history"][-1]["parts"][0]["text"].lower()
    assert result3["status"]["state"] == "completed"
    
    print("OK Inspector conversation flow with task ID preservation works!")

if __name__ == "__main__":
    test_inspector_conversation_flow()