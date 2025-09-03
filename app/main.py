from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import base64
import os

# Create FastAPI app
app = FastAPI(title="Multi-Agent Interoperability Demo", version="1.0.0")

# Mount static files (/static) - correct paths for web directory
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Jinja2 templates - correct path for web directory
templates = Jinja2Templates(directory="app/web/templates")

# Include routers from protocols
from app.protocols.a2a import router as a2a_router
from app.protocols.mcp import router as mcp_router

app.include_router(a2a_router, prefix="/api/a2a", tags=["A2A Protocol"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Protocol"])

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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """GET / renders index.html"""
    return templates.TemplateResponse("index.html", {"request": request})

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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)