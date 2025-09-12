#!/usr/bin/env python3
"""Test A2A specification compliance"""
import json
import requests
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_agent_card_compliance():
    """Test Agent Card spec compliance"""
    print("Testing Agent Card...")
    response = client.get("/.well-known/agent-card.json")
    assert response.status_code == 200
    
    card = response.json()
    
    # Standard required fields
    assert card["name"]
    assert card["description"] 
    assert card["version"]
    assert card["capabilities"]["streaming"] is True
    
    # A2A specific fields
    assert card["protocolVersion"] == "0.2.9"
    assert card["preferredTransport"] == "JSONRPC"
    
    # Endpoints - both formats supported
    assert "endpoints" in card
    assert card["endpoints"]["jsonrpc"]
    assert "/api/bridge/demo/a2a" in card["endpoints"]["jsonrpc"]
    
    # Skills structure (newer spec format)
    assert "skills" in card
    assert len(card["skills"]) > 0
    skill = card["skills"][0]
    assert "id" in skill
    assert "discovery" in skill
    assert "url" in skill["discovery"]
    assert "/api/bridge/demo/a2a" in skill["discovery"]["url"]
    assert "a2a" in skill
    assert "config64" in skill["a2a"]
    
    print("OK Agent Card is spec-compliant")

def test_message_send():
    """Test message/send method"""
    print("Testing message/send...")
    
    payload = {
        "jsonrpc": "2.0",
        "id": "test_send_1",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "Hello, I need breast cancer screening eligibility"}]
            }
        }
    }
    
    response = client.post("/api/bridge/demo/a2a", json=payload)
    assert response.status_code == 200
    
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == "test_send_1"
    assert "result" in result
    
    task = result["result"]
    
    # Task structure
    assert task["kind"] == "task"
    assert task["id"].startswith("task_")
    assert task["contextId"].startswith("ctx_")
    assert task["status"]["state"] in ["submitted", "working", "input-required", "completed"]
    assert "history" in task
    assert len(task["history"]) >= 2  # User message + agent reply
    
    # History structure
    for msg in task["history"]:
        assert "role" in msg
        assert "parts" in msg
        assert "messageId" in msg
        assert "taskId" in msg
        assert "contextId" in msg
        assert msg["kind"] == "message"
        assert "metadata" in msg
    
    print(f"OK message/send creates task {task['id']} with {len(task['history'])} messages")

def test_tasks_get():
    """Test tasks/get method"""
    print("Testing tasks/get...")
    
    # First create a task
    create_payload = {
        "jsonrpc": "2.0",
        "id": "create_task",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "Test message for task retrieval"}]
            }
        }
    }
    
    create_response = client.post("/api/bridge/demo/a2a", json=create_payload)
    task_id = create_response.json()["result"]["id"]
    
    # Now get the task
    get_payload = {
        "jsonrpc": "2.0",
        "id": "get_task",
        "method": "tasks/get",
        "params": {"id": task_id}
    }
    
    response = client.post("/api/bridge/demo/a2a", json=get_payload)
    assert response.status_code == 200
    
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == "get_task"
    
    task = result["result"]
    assert task["id"] == task_id
    assert "history" in task
    assert len(task["history"]) >= 2
    
    print(f"OK tasks/get retrieves full task snapshot with history")

def test_tasks_cancel():
    """Test tasks/cancel method"""
    print("Testing tasks/cancel...")
    
    # Create a task first
    create_payload = {
        "jsonrpc": "2.0",
        "id": "create_cancel",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "Task to cancel"}]
            }
        }
    }
    
    create_response = client.post("/api/bridge/demo/a2a", json=create_payload)
    task_id = create_response.json()["result"]["id"]
    
    # Cancel the task
    cancel_payload = {
        "jsonrpc": "2.0",
        "id": "cancel_task",
        "method": "tasks/cancel",
        "params": {"id": task_id}
    }
    
    response = client.post("/api/bridge/demo/a2a", json=cancel_payload)
    assert response.status_code == 200
    
    result = response.json()
    task = result["result"]
    assert task["status"]["state"] == "canceled"
    
    print("OK tasks/cancel updates status to canceled")

def test_message_stream_sse():
    """Test message/stream with SSE"""
    print("Testing message/stream SSE...")
    
    payload = {
        "jsonrpc": "2.0",
        "id": "stream_test",
        "method": "message/stream",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "Stream test message"}]
            }
        }
    }
    
    # Test with SSE header
    with client as c:
        response = c.post(
            "/api/bridge/demo/a2a", 
            json=payload,
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE stream
        lines = response.text.strip().split('\n')
        data_lines = [line[5:] for line in lines if line.startswith('data: ')]
        
        assert len(data_lines) >= 3  # Initial snapshot + message + status update
        
        # Parse first frame (initial snapshot)
        initial_frame = json.loads(data_lines[0])
        assert initial_frame["jsonrpc"] == "2.0"
        assert initial_frame["id"] == "stream_test"
        assert "result" in initial_frame
        task = initial_frame["result"]
        assert task["kind"] == "task"
        assert task["status"]["state"] == "working"
        
        # Parse last frame (terminal status)
        terminal_frame = json.loads(data_lines[-1])
        assert terminal_frame["result"]["kind"] == "status-update"
        assert terminal_frame["result"]["final"] is True
        assert terminal_frame["result"]["status"]["state"] in ["input-required", "completed"]
        
    print("OK message/stream returns proper SSE frames with terminal status-update")

def test_error_handling():
    """Test error responses"""
    print("Testing error handling...")
    
    # Test unknown method
    payload = {
        "jsonrpc": "2.0",
        "id": "error_test",
        "method": "unknown/method",
        "params": {}
    }
    
    response = client.post("/api/bridge/demo/a2a", json=payload)
    assert response.status_code == 404
    
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == "error_test"
    assert "error" in result
    assert result["error"]["code"] == -32601
    assert "Method not found" in result["error"]["message"]
    
    print("OK Unknown methods return proper JSON-RPC errors")

def test_alias_endpoint():
    """Test /a2a alias"""
    print("Testing /a2a alias...")
    
    payload = {
        "jsonrpc": "2.0",
        "id": "alias_test",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "Testing alias endpoint"}]
            }
        }
    }
    
    response = client.post("/a2a", json=payload)
    assert response.status_code == 200
    
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == "alias_test"
    assert "result" in result
    
    print("OK /a2a alias works correctly")

def test_inspector_compatibility():
    """Test compatibility with A2A Inspector"""
    print("Testing Inspector compatibility...")
    
    # Test content parameter format (used by inspector)
    payload = {
        "jsonrpc": "2.0",
        "id": "inspector_test",
        "method": "message/send",
        "params": {
            "content": "Direct content parameter test",
            "metadata": {"inspector": True}
        }
    }
    
    response = client.post("/api/bridge/demo/a2a", json=payload)
    assert response.status_code == 200
    
    result = response.json()
    task = result["result"]
    
    # Check that content was converted to proper message format
    user_message = next((msg for msg in task["history"] if msg["role"] == "user"), None)
    assert user_message is not None
    assert len(user_message["parts"]) > 0
    assert user_message["parts"][0]["text"] == "Direct content parameter test"
    
    print("OK Inspector content parameter format supported")

if __name__ == "__main__":
    print("Running A2A Specification Compliance Tests...")
    print("=" * 50)
    
    test_agent_card_compliance()
    test_message_send()
    test_tasks_get()
    test_tasks_cancel()
    test_message_stream_sse()
    test_error_handling()
    test_alias_endpoint()
    test_inspector_compatibility()
    
    print("=" * 50)
    print("All A2A specification tests passed!")