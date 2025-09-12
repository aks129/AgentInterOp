#!/usr/bin/env python3
"""Debug the conversation flow issue"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_debug_conversation():
    """Debug why evaluation isn't showing"""
    print("Debugging conversation flow...")
    
    # Message 1: hello
    payload1 = {
        "jsonrpc": "2.0",
        "id": "debug1",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "hello"}]
            }
        }
    }
    
    response1 = client.post("/api/bridge/demo/a2a", json=payload1)
    task_id = response1.json()["result"]["id"]
    print(f"Stage 1 done, task: {task_id}")
    
    # Message 2: age
    payload2 = {
        "jsonrpc": "2.0",
        "id": "debug2",
        "method": "message/send",
        "params": {
            "message": {
                "taskId": task_id,
                "parts": [{"kind": "text", "text": "50"}]
            }
        }
    }
    
    response2 = client.post("/api/bridge/demo/a2a", json=payload2)
    print(f"Stage 2 done")
    
    # Message 3: mammogram date
    payload3 = {
        "jsonrpc": "2.0",
        "id": "debug3",
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
    
    print(f"Stage 3 response: {result3['history'][-1]['parts'][0]['text']}")
    print(f"Status: {result3['status']['state']}")

if __name__ == "__main__":
    test_debug_conversation()