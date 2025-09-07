from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse, PlainTextResponse, StreamingResponse
from datetime import datetime, timezone
from pathlib import Path
import os, json, time, base64

# Create FastAPI app
app = FastAPI(title="AgentInterOp", version="1.0.0-bcse")

# Guard static/templates setup for Vercel compatibility
templates = None
try:
    from fastapi.templating import Jinja2Templates
    from fastapi.staticfiles import StaticFiles
    base = Path(__file__).resolve().parent
    static_dir = base / "web" / "static"
    templates_dir = base / "web" / "templates"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        print(f"[WARN] no static dir: {static_dir}")
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))
    else:
        print(f"[WARN] no templates dir: {templates_dir}")
except Exception as e:
    print(f"[WARN] static/templates setup skipped: {e}")

# Include routers from protocols
from app.protocols.a2a import router as a2a_router
from app.protocols.mcp import router as mcp_router

app.include_router(a2a_router, prefix="/api/a2a", tags=["A2A Protocol"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Protocol"])

# Include BCS-specific routers
from app.protocols.a2a_bcse import router as a2a_bcse_router
from app.protocols.mcp_bcse import router as mcp_bcse_router
app.include_router(a2a_bcse_router)
app.include_router(mcp_bcse_router)

# In-memory artifact storage for demo
demo_artifacts = {
    "demo-task": {
        "QuestionnaireResponse.json": {
            "mimeType": "application/fhir+json",
            "bytes": base64.b64encode(b'{"resourceType":"QuestionnaireResponse","status":"completed"}').decode()
        },
        "DecisionBundle.json": {
            "mimeType": "application/fhir+json", 
            "bytes": base64.b64encode(b'{"resourceType":"Bundle","type":"collection","entry":[]}').decode()
        }
    }
}

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.get("/version")
def version():
    return {"name": "AgentInterOp", "version": app.version, "scenario": "bcse"}

@app.get("/.well-known/agent-card.json")
def agent_card(request: Request):
    base = str(request.base_url).rstrip("/")
    card = {
      "protocolVersion": "0.2.9",
      "preferredTransport": "JSONRPC",
      "capabilities": {"streaming": True},
      "skills": [
        { "id": "bcse", "a2a": { "config64": base64.b64encode(b'{"scenario":"bcse"}').decode() } }
      ],
      "endpoints": { "jsonrpc": f"{base}/api/bridge/bcse/a2a" }
    }
    return JSONResponse(card)

@app.get("/api/selftest")
def selftest():
    return {"ok": True,
            "a2a": ["message/send","message/stream","tasks/get","tasks/cancel"],
            "mcp": ["begin_chat_thread","send_message_to_chat_thread","check_replies"],
            "scenario": "bcse"}

@app.get("/api/loopback/sse")
def loop_sse():
    import time
    def gen():
        yield "event: message\ndata: {\"kind\":\"task\",\"status\":{\"state\":\"working\"}}\n\n"
        time.sleep(0.3)
        yield "event: message\ndata: {\"role\":\"agent\",\"parts\":[{\"kind\":\"text\",\"text\":\"hello\"}],\"kind\":\"message\"}\n\n"
        time.sleep(0.3)
        yield "event: status-update\ndata: {\"final\":true,\"status\":{\"state\":\"completed\"}}\n\n"
    from fastapi.responses import StreamingResponse
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/trace/{contextId}/download")
def download_trace(contextId: str):
    from app.store.persistence import list_traces
    from fastapi.responses import JSONResponse
    return JSONResponse(list_traces(contextId))

# BCS REST endpoints
from app.scenarios import bcse as BCS

@app.post("/api/bcse/ingest/demo")
def bcse_ingest_demo():
    p = Path(__file__).resolve().parent / "demo" / "patient_bcse.json"
    bundle = json.loads(p.read_text())
    return {"ok": True, "applicant_payload": BCS.map_fhir_bundle(bundle), "source": "demo"}

@app.post("/api/bcse/evaluate")
def bcse_evaluate(payload: dict):
    """
    Body: { "sex": "...", "birthDate": "YYYY-MM-DD", "last_mammogram": "YYYY-MM-DD" }
    """
    decision = BCS.evaluate(payload or {})
    return {"ok": True, "decision": decision}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """GET / renders index.html"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("<h1>Multi-Agent Demo</h1><p>Templates not available in this environment</p>")

@app.get("/partner_connect", response_class=HTMLResponse)
async def partner_connect(request: Request):
    """Partner Connect UI"""
    if templates:
        return templates.TemplateResponse("partner_connect.html", {"request": request})
    else:
        return HTMLResponse("<h1>Partner Connect</h1><p>Templates not available in this environment</p>")

@app.get("/test_harness", response_class=HTMLResponse)
async def test_harness(request: Request):
    """Test Harness UI"""
    if templates:
        return templates.TemplateResponse("test_harness.html", {"request": request})
    else:
        return HTMLResponse("<h1>Test Harness</h1><p>Templates not available in this environment</p>")

@app.get("/artifacts/{task_id}/{name}")
async def download_artifact(task_id: str, name: str):
    """Download artifact by task_id and filename"""
    
    # First, check if artifacts exist in the conversation engine
    from app.engine import conversation_engine
    conv_state = conversation_engine.get_conversation_state(task_id)
    
    if conv_state and "artifacts" in conv_state and name in conv_state["artifacts"]:
        # Use real artifacts from conversation engine
        base64_content = conv_state["artifacts"][name]
        mime_type = "application/fhir+json" if name.endswith(".json") else "application/octet-stream"
        
        try:
            content = base64.b64decode(base64_content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid artifact data")
        
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{name}"'
            }
        )
    
    # Fall back to demo artifacts for testing
    if task_id not in demo_artifacts:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if name not in demo_artifacts[task_id]:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    artifact = demo_artifacts[task_id][name]
    
    # Decode base64 content
    try:
        content = base64.b64decode(artifact["bytes"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid artifact data")
    
    # Return file with correct mime type and download headers
    return Response(
        content=content,
        media_type=artifact["mimeType"],
        headers={
            "Content-Disposition": f'attachment; filename="{name}"'
        }
    )

# Global state for protocol management
current_protocol = "a2a"

@app.get("/api/current_protocol")
async def get_current_protocol():
    """Get the current active protocol"""
    return {"protocol": current_protocol}

@app.post("/api/protocol")
async def switch_protocol(request: Request):
    """Switch between A2A and MCP protocols"""
    global current_protocol
    data = await request.json()
    new_protocol = data.get('protocol')
    
    if new_protocol in ['a2a', 'mcp']:
        current_protocol = new_protocol
        return {"success": True, "protocol": current_protocol}
    else:
        raise HTTPException(status_code=400, detail="Invalid protocol")

@app.post("/api/start_conversation")
async def start_conversation(request: Request):
    """Start a new conversation between agents"""
    data = await request.json()
    scenario = data.get('scenario', 'eligibility_check')
    
    # Mock response for demonstration - in real implementation this would
    # interact with the conversation engine
    import uuid
    session_id = str(uuid.uuid4())
    
    if current_protocol == "a2a":
        initial_exchange = {
            "applicant_request": {"method": "initiate_eligibility_check", "id": "req-1"},
            "applicant_response": {"result": "Request submitted", "id": "req-1"},
            "admin_response": {"method": "process_application", "result": "Application received", "id": "req-2"}
        }
    else:
        initial_exchange = {
            "eligibility_call": {"tool": "eligibility_check", "parameters": {"scenario": scenario}},
            "applicant_response": {"result": "Eligibility check initiated"},
            "process_call": {"tool": "process_application", "parameters": {"data": "application_data"}},
            "admin_response": {"result": "Application processed successfully"}
        }
    
    return {
        "success": True,
        "result": {
            "session_id": session_id,
            "protocol": current_protocol,
            "initial_exchange": initial_exchange
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)