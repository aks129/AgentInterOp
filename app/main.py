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

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)