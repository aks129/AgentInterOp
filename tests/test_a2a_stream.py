import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_jsonrpc_ok():
    """Test normal JSON-RPC request without Content-Length requirement"""
    client = TestClient(app)
    payload = {"jsonrpc": "2.0", "method": "tasks/cancel", "params": {"id": "x"}, "id": 3}

    # Send request without Content-Length header (TestClient handles this)
    resp = client.post(
        "/api/bridge/demo/a2a",
        json=payload
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    # Do NOT assert Content-Length presence

    data = resp.json()
    assert "jsonrpc" in data
    assert data["jsonrpc"] == "2.0"

def test_streaming_ok():
    """Test streaming response without Content-Length"""
    client = TestClient(app)
    payload = {"jsonrpc": "2.0", "method": "message/stream", "params": {}, "id": 1}

    # Request streaming with event-stream accept header
    with client as c:
        resp = c.post(
            "/api/bridge/demo/a2a",
            json=payload,
            headers={"Accept": "text/event-stream"}
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        # Streaming responses should NOT have Content-Length
        assert "content-length" not in resp.headers
        assert resp.headers.get("cache-control") == "no-cache"
        assert resp.headers.get("connection") == "keep-alive"

def test_context_endpoint_json():
    """Test context-aware endpoint with JSON response"""
    client = TestClient(app)
    payload = {"jsonrpc": "2.0", "method": "tasks/get", "params": {"id": "test"}, "id": 5}

    resp = client.post(
        "/api/bridge/custom/a2a",
        json=payload
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    # Do NOT require Content-Length

def test_context_endpoint_stream():
    """Test context-aware endpoint with streaming"""
    client = TestClient(app)
    payload = {"jsonrpc": "2.0", "method": "message/stream", "params": {}, "id": 7}

    with client as c:
        resp = c.post(
            "/api/bridge/custom/a2a",
            json=payload,
            headers={"Accept": "text/event-stream"}
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert "content-length" not in resp.headers

def test_empty_body():
    """Test empty body handling"""
    client = TestClient(app)

    resp = client.post(
        "/api/bridge/demo/a2a",
        content=b"",
        headers={"Content-Type": "application/json"}
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data

def test_large_body():
    """Test body size limit"""
    client = TestClient(app)

    # Create a payload larger than 5MB
    large_data = "x" * (5_000_001)
    payload = {"jsonrpc": "2.0", "method": "test", "params": {"data": large_data}, "id": 9}

    resp = client.post(
        "/api/bridge/demo/a2a",
        json=payload
    )

    assert resp.status_code == 413
    data = resp.json()
    assert "error" in data

def test_a2a_accepts_chunked():
    """Test that A2A endpoint accepts chunked transfer encoding"""
    client = TestClient(app)
    payload = b'{"jsonrpc":"2.0","method":"tasks/cancel","params":{"id":"x"},"id":3}'

    # Simulate chunked transfer (TestClient may not truly chunk, but tests header handling)
    headers = {
        "Content-Type": "application/json",
        "Transfer-Encoding": "chunked"
    }

    resp = client.post("/api/bridge/demo/a2a", headers=headers, content=payload)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")

    data = resp.json()
    assert "jsonrpc" in data
    assert data["jsonrpc"] == "2.0"

def test_helpful_error_for_missing_content_length_and_chunked():
    """Test helpful error message when neither Content-Length nor chunked is provided"""
    client = TestClient(app)

    # Send empty body with JSON content-type but no transfer encoding
    resp = client.post(
        "/api/bridge/demo/a2a",
        content=b"",
        headers={"Content-Type": "application/json"}
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    # Should contain helpful message about chunked encoding
    error_msg = data["error"]["message"].lower()
    assert "empty body" in error_msg

def test_context_endpoint_chunked():
    """Test context-aware endpoint with chunked encoding"""
    client = TestClient(app)
    payload = b'{"jsonrpc":"2.0","method":"tasks/get","params":{"id":"test"},"id":5}'

    headers = {
        "Content-Type": "application/json",
        "Transfer-Encoding": "chunked"
    }

    resp = client.post(
        "/api/bridge/custom/a2a",
        headers=headers,
        content=payload
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")

    data = resp.json()
    assert "jsonrpc" in data
    assert data["jsonrpc"] == "2.0"