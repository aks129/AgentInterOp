#!/usr/bin/env python3
"""Test script for A2A canonical endpoints"""
import json
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    """Test health endpoint"""
    response = client.get("/healthz")
    print("OK /healthz:", response.json())
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_agent_card():
    """Test agent card endpoint"""
    response = client.get("/.well-known/agent-card.json")
    print("OK /.well-known/agent-card.json endpoints:", response.json()["endpoints"])
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data
    assert "jsonrpc" in data["endpoints"]
    assert "/api/bridge/demo/a2a" in data["endpoints"]["jsonrpc"]

def test_canonical_a2a():
    """Test canonical A2A endpoint"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test_1",
        "method": "message/send",
        "params": {
            "content": "Hello, test message",
            "metadata": {"scenario": "bcse", "agent_role": "applicant"}
        }
    }
    response = client.post("/api/bridge/demo/a2a", json=payload)
    print("OK /api/bridge/demo/a2a:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test_1"
    assert "result" in data

def test_a2a_alias():
    """Test A2A alias endpoint"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test_2",
        "method": "message/send",
        "params": {
            "message": {
                "parts": [{"kind": "text", "text": "Hello via alias"}]
            }
        }
    }
    response = client.post("/a2a", json=payload)
    print("OK /a2a:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test_2"

def test_root_post_guidance():
    """Test root POST guidance"""
    response = client.post("/")
    print("OK POST / guidance:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "hint" in data

def test_unsupported_method():
    """Test unsupported A2A method"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test_error",
        "method": "unsupported/method",
        "params": {}
    }
    response = client.post("/api/bridge/demo/a2a", json=payload)
    print("OK Unsupported method error:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32601

if __name__ == "__main__":
    print("Testing A2A canonical endpoints...")
    test_health()
    test_agent_card()
    test_canonical_a2a()
    test_a2a_alias()
    test_root_post_guidance()
    test_unsupported_method()
    print("\nAll tests passed successfully!")