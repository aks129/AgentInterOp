"""
Minimal smoke tests - fast checks that catch obvious breakage.
These run on every PR to prevent /docs, discovery, and core endpoints from silently breaking.
"""

import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    """Health endpoint must always work"""
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "ts" in data

def test_openapi_schema():
    """OpenAPI schema must be valid for /docs to work"""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "info" in schema
    # Verify some critical paths exist
    assert "/.well-known/agent-card.json" in schema["paths"]
    assert "/healthz" in schema["paths"]

def test_docs_endpoint():
    """Swagger UI docs page must load"""
    r = client.get("/docs")
    assert r.status_code == 200
    # Content should be HTML with Swagger UI
    assert "text/html" in r.headers.get("content-type", "")

def test_agent_card_a2a_compliance():
    """Agent Card must be A2A compliant"""
    r = client.get("/.well-known/agent-card.json")
    assert r.status_code == 200
    
    card = r.json()
    
    # Required A2A fields
    required_fields = ["name", "description", "url", "version", "capabilities", "skills"]
    for field in required_fields:
        assert field in card, f"Missing required A2A field: {field}"
    
    # Must have at least one skill
    assert len(card["skills"]) > 0, "Agent must have at least one skill"
    
    # Skill must have required fields
    skill = card["skills"][0]
    skill_required = ["id", "name", "description", "a2a.config64"]
    for field in skill_required:
        assert field in skill, f"Missing required skill field: {field}"
    
    # Verify no non-standard endpoints at root (should be under x-demo-endpoints)
    assert "endpoints" not in card, "Found non-standard 'endpoints' field - should be 'x-demo-endpoints'"
    
    # Capabilities should be proper format
    caps = card["capabilities"]
    assert isinstance(caps["streaming"], bool)
    assert isinstance(caps.get("pushNotifications", False), bool)

def test_bcse_evaluate_demo():
    """BCSE evaluation endpoint with demo payload"""
    demo_payload = {
        "sex": "female",
        "birthDate": "1968-05-10", 
        "last_mammogram": "2024-12-01"
    }
    
    r = client.post("/api/bcse/evaluate", json=demo_payload)
    assert r.status_code == 200
    
    result = r.json()
    assert result["ok"] is True
    assert "decision" in result
    
    # Decision should have eligibility info
    decision = result["decision"]
    assert "eligible" in decision
    assert isinstance(decision["eligible"], bool)

def test_version_endpoint():
    """Version endpoint for deployment tracking"""
    r = client.get("/version")
    assert r.status_code == 200
    
    version_info = r.json()
    assert "name" in version_info
    assert "version" in version_info
    assert version_info["name"] == "AgentInterOp"

def test_selftest_endpoint():
    """Self-test endpoint shows system status"""
    r = client.get("/api/selftest")
    assert r.status_code == 200
    
    selftest = r.json()
    assert selftest["ok"] is True
    assert "a2a" in selftest
    assert "mcp" in selftest
    assert "endpoints" in selftest
    
    # Should list available A2A methods
    assert "message/send" in selftest["a2a"]
    assert "tasks/get" in selftest["a2a"]

def test_root_endpoint():
    """Root endpoint should serve the main UI"""
    r = client.get("/")
    assert r.status_code == 200
    # Should be HTML response
    assert "text/html" in r.headers.get("content-type", "")