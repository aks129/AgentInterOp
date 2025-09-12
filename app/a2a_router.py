from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# Import or implement your existing JSON-RPC dispatcher
# This should return a dict envelope: {"jsonrpc":"2.0","id":...,"result":{...}} or {"error":{...}}
async def handle_jsonrpc(payload: dict) -> dict:
    """Handle JSON-RPC A2A requests with proper routing to existing logic."""
    method = payload.get("method")
    jid = payload.get("id")
    params = payload.get("params", {})
    
    try:
        # Route to existing A2A protocol handling
        if method == "message/send":
            # Extract message content
            content = params.get("content", "")
            if not content and "message" in params:
                message_parts = params["message"].get("parts", [])
                if message_parts and message_parts[0].get("kind") == "text":
                    content = message_parts[0].get("text", "")
            
            # Create A2A task response compatible with existing system
            return {
                "jsonrpc": "2.0",
                "id": jid,
                "result": {
                    "id": f"task_{jid}",
                    "contextId": f"ctx_{jid}",
                    "status": {"state": "submitted"},
                    "artifacts": [],
                    "history": [
                        {
                            "role": "user",
                            "parts": [{"kind": "text", "text": content}] if content else [],
                            "messageId": f"msg_{jid}",
                            "taskId": f"task_{jid}",
                            "contextId": f"ctx_{jid}",
                            "kind": "message",
                            "metadata": {}
                        }
                    ],
                    "kind": "task",
                    "metadata": {
                        "autoRespond": False,
                        "scenario": params.get("metadata", {}).get("scenario", "unknown")
                    }
                }
            }
        elif method == "message/stream":
            return {
                "jsonrpc": "2.0",
                "id": jid,
                "result": {
                    "streamUrl": f"/api/stream/{jid}",
                    "status": "streaming"
                }
            }
        elif method == "tasks/get":
            task_id = params.get("taskId")
            return {
                "jsonrpc": "2.0",
                "id": jid,
                "result": {
                    "id": task_id,
                    "status": {"state": "completed"},
                    "kind": "task"
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": jid,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                    "data": {"supported_methods": ["message/send", "message/stream", "tasks/get"]}
                }
            }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": jid,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"error": str(e)}
            }
        }

@router.post("/api/bridge/demo/a2a")
async def a2a_jsonrpc(request: Request):
    """Canonical A2A JSON-RPC endpoint."""
    payload = await request.json()
    result = await handle_jsonrpc(payload)
    return JSONResponse(result)

# Convenience alias for quick partner testing
@router.post("/a2a")
async def a2a_alias(request: Request):
    """Convenience alias for A2A endpoint."""
    return await a2a_jsonrpc(request)