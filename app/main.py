from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Create FastAPI app
app = FastAPI(title="Multi-Agent Interoperability Demo", version="1.0.0")

# Mount static files (/static)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include routers from protocols
from app.protocols.a2a import router as a2a_router
from app.protocols.mcp import router as mcp_router

app.include_router(a2a_router, prefix="/api/a2a", tags=["A2A Protocol"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Protocol"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """GET / renders index.html"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)