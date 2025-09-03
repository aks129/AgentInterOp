import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from datetime import datetime
from typing import Dict, Any, Optional

from app.protocols.a2a import A2AProtocol
from app.protocols.mcp import MCPProtocol
from app.store.memory import ConversationMemory
from app.agents.applicant import ApplicantAgent
from app.agents.administrator import AdministratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Interoperability Demo", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/web/templates")

# Initialize components
memory = ConversationMemory()
applicant_agent = ApplicantAgent()
administrator_agent = AdministratorAgent()

# Initialize protocols
a2a_protocol = A2AProtocol(memory, applicant_agent, administrator_agent)
mcp_protocol = MCPProtocol(memory, applicant_agent, administrator_agent)

# Current active protocol
current_protocol = "a2a"

# Pydantic models for request/response
class ProtocolSwitchRequest(BaseModel):
    protocol: str

class ConversationStartRequest(BaseModel):
    scenario: str = "eligibility_check"

class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class ProtocolResponse(BaseModel):
    success: bool
    protocol: str

class ConversationResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main application page"""
    return templates.TemplateResponse("simple_index.html", {"request": request})

@app.get("/api/conversations")
async def get_conversations():
    """Get all conversations from memory"""
    try:
        conversations = memory.get_all_conversations()
        return conversations
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return []

@app.post("/api/protocol", response_model=ProtocolResponse)
async def switch_protocol(request: ProtocolSwitchRequest):
    """Switch between A2A and MCP protocols"""
    global current_protocol
    
    if request.protocol in ['a2a', 'mcp']:
        current_protocol = request.protocol
        logger.info(f"Protocol switched to: {current_protocol}")
        return ProtocolResponse(success=True, protocol=current_protocol)
    else:
        raise HTTPException(status_code=400, detail="Invalid protocol")

@app.post("/api/start_conversation", response_model=ConversationResponse)
async def start_conversation(request: ConversationStartRequest):
    """Start a new conversation between agents"""
    try:
        if current_protocol == "a2a":
            result = a2a_protocol.start_conversation(request.scenario)
        else:
            result = mcp_protocol.start_conversation(request.scenario)
        
        return ConversationResponse(success=True, result=result)
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return ConversationResponse(success=False, error=str(e))

@app.get("/api/current_protocol")
async def current_protocol_status():
    """Get current protocol status"""
    return {"protocol": current_protocol}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Multi-Agent Interoperability Demo with FastAPI")
    logger.info(f"Current protocol: {current_protocol}")
    uvicorn.run(app, host="0.0.0.0", port=5000)