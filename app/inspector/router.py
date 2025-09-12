"""A2A Inspector router for testing and debugging A2A endpoints."""
import json
import uuid
import httpx
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspectortest", tags=["A2A Inspector"])

# WebSocket connections storage
active_connections: Dict[str, WebSocket] = {}

@router.get("/", response_class=HTMLResponse)
async def inspector_page(request: Request):
    """Serve the A2A Inspector interface."""
    try:
        from fastapi.templating import Jinja2Templates
        from pathlib import Path
        
        base = Path(__file__).resolve().parent.parent
        templates_dir = base / "web" / "templates"
        
        if templates_dir.exists():
            templates = Jinja2Templates(directory=str(templates_dir))
            return templates.TemplateResponse("inspector.html", {
                "request": request,
                "base_url": str(request.base_url).rstrip("/")
            })
        else:
            # Fallback minimal HTML if templates not available
            return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <title>A2A Inspector</title>
    <link rel="stylesheet" href="/static/inspector.css">
</head>
<body>
    <div id="app">
        <h1>A2A Protocol Inspector</h1>
        <p>Base URL: {request.base_url}</p>
        <div id="agent-card-section">
            <h2>Agent Card</h2>
            <pre id="agent-card-display">Loading...</pre>
        </div>
        <div id="chat-section">
            <h2>Live Chat</h2>
            <div id="messages"></div>
            <div>
                <input type="text" id="message-input" placeholder="Type your message..." />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        <div id="debug-console">
            <h2>Debug Console</h2>
            <pre id="debug-log"></pre>
        </div>
    </div>
    <script src="/static/inspector.js"></script>
</body>
</html>
            """)
    except Exception as e:
        logger.error(f"Error serving inspector page: {e}")
        return HTMLResponse(f"<h1>Inspector Error</h1><p>{e}</p>", status_code=500)

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication."""
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "fetch_agent_card":
                await handle_fetch_agent_card(client_id, message)
            elif message.get("type") == "send_message":
                await handle_send_message(client_id, message)
            elif message.get("type") == "validate_spec":
                await handle_validate_spec(client_id, message)
                
    except WebSocketDisconnect:
        active_connections.pop(client_id, None)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        await websocket.close(code=1011)

async def handle_fetch_agent_card(client_id: str, message: Dict[str, Any]):
    """Fetch and validate agent card."""
    websocket = active_connections.get(client_id)
    if not websocket:
        return
    
    base_url = message.get("base_url", "").rstrip("/")
    if not base_url:
        base_url = "http://localhost:8000"  # Default to self
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch agent card
            card_url = f"{base_url}/.well-known/agent-card.json"
            response = await client.get(card_url)
            response.raise_for_status()
            
            agent_card = response.json()
            
            # Log the request/response
            debug_info = {
                "type": "agent_card_fetch",
                "request": {
                    "method": "GET",
                    "url": card_url,
                    "timestamp": str(uuid.uuid4())
                },
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": agent_card
                }
            }
            
            # Send agent card to client
            await websocket.send_text(json.dumps({
                "type": "agent_card_response",
                "success": True,
                "data": agent_card,
                "debug": debug_info
            }))
            
            # Perform basic validation
            validation_result = validate_agent_card(agent_card)
            await websocket.send_text(json.dumps({
                "type": "validation_result",
                "success": True,
                "data": validation_result
            }))
            
    except Exception as e:
        logger.error(f"Error fetching agent card: {e}")
        await websocket.send_text(json.dumps({
            "type": "agent_card_response",
            "success": False,
            "error": str(e)
        }))

async def handle_send_message(client_id: str, message: Dict[str, Any]):
    """Send message to A2A endpoint."""
    websocket = active_connections.get(client_id)
    if not websocket:
        return
    
    base_url = message.get("base_url", "").rstrip("/")
    user_message = message.get("message", "")
    
    if not base_url:
        base_url = "http://localhost:8000"
    
    # Use canonical A2A endpoint
    a2a_url = f"{base_url}/api/bridge/demo/a2a"
    
    # Prepare JSON-RPC request
    request_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "content": user_message,
            "metadata": {
                "inspector": True,
                "client_id": client_id
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                a2a_url,
                json=request_payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_data = response.json()
            
            # Log the request/response
            debug_info = {
                "type": "message_send",
                "request": {
                    "method": "POST",
                    "url": a2a_url,
                    "headers": {"Content-Type": "application/json"},
                    "body": request_payload,
                    "timestamp": str(uuid.uuid4())
                },
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_data
                }
            }
            
            # Send response to client
            await websocket.send_text(json.dumps({
                "type": "message_response",
                "success": True,
                "data": response_data,
                "debug": debug_info
            }))
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        await websocket.send_text(json.dumps({
            "type": "message_response",
            "success": False,
            "error": str(e)
        }))

async def handle_validate_spec(client_id: str, message: Dict[str, Any]):
    """Validate A2A specification compliance."""
    websocket = active_connections.get(client_id)
    if not websocket:
        return
    
    agent_card = message.get("agent_card", {})
    validation_result = validate_agent_card(agent_card)
    
    await websocket.send_text(json.dumps({
        "type": "validation_result",
        "success": True,
        "data": validation_result
    }))

def validate_agent_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """Validate agent card against A2A specification."""
    issues = []
    warnings = []
    
    # Required fields
    required_fields = ["name", "description", "version", "capabilities"]
    for field in required_fields:
        if field not in card:
            issues.append(f"Missing required field: {field}")
    
    # Endpoints validation
    if "endpoints" in card:
        endpoints = card["endpoints"]
        if "jsonrpc" not in endpoints:
            warnings.append("Missing 'jsonrpc' endpoint - required for A2A protocol")
    else:
        issues.append("Missing 'endpoints' field")
    
    # Skills validation
    if "skills" in card:
        skills = card.get("skills", [])
        if not isinstance(skills, list):
            issues.append("'skills' must be an array")
        else:
            for i, skill in enumerate(skills):
                if not isinstance(skill, dict):
                    issues.append(f"Skill {i} must be an object")
                elif "id" not in skill:
                    issues.append(f"Skill {i} missing required 'id' field")
    
    # Capabilities validation
    if "capabilities" in card:
        caps = card["capabilities"]
        if not isinstance(caps, dict):
            issues.append("'capabilities' must be an object")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "score": max(0, 100 - len(issues) * 20 - len(warnings) * 5)
    }

@router.get("/health")
async def inspector_health():
    """Health check for inspector."""
    return {
        "ok": True,
        "active_connections": len(active_connections),
        "features": [
            "agent_card_fetch",
            "spec_validation", 
            "live_chat",
            "debug_console"
        ]
    }