"""
MCP (Model Context Protocol) Tools Router
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal, Union, cast
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.store.memory import conversation_store, new_id, iso8601_now, trace

router = APIRouter()

# Import the shared conversation engine
from app.engine import conversation_engine

# MCP Tool Response Models

class MCPTextContent(BaseModel):
    """MCP text content format"""
    type: Literal["text"] = "text"
    text: str

class MCPToolResponse(BaseModel):
    """Standard MCP tool response format"""
    content: List[MCPTextContent]

# MCP Data Models

class MCPAttachment(BaseModel):
    """MCP message attachment"""
    name: str
    contentType: str
    content: str  # base64 encoded
    summary: Optional[str] = None

class MCPMessage(BaseModel):
    """MCP chat message"""
    from_: str = Field(alias="from")
    at: str  # ISO timestamp
    text: str
    attachments: List[MCPAttachment] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True

# Input Models

class BeginChatThreadRequest(BaseModel):
    """Empty request for beginning chat thread"""
    pass

class SendMessageRequest(BaseModel):
    """Send message to chat thread request"""
    conversationId: str
    message: str
    attachments: Optional[List[MCPAttachment]] = None

class CheckRepliesRequest(BaseModel):
    """Check replies request"""
    conversationId: str
    waitMs: Optional[int] = None

# Response Models

class BeginChatResponse(BaseModel):
    """Begin chat thread response"""
    conversationId: str

class SendMessageResponse(BaseModel):
    """Send message response"""
    guidance: str
    status: Literal["working", "input-required", "completed"]

class CheckRepliesResponse(BaseModel):
    """Check replies response"""
    messages: List[MCPMessage]
    guidance: str
    status: Literal["working", "input-required", "completed"]
    conversation_ended: bool

# In-memory storage for MCP conversations
_mcp_conversations: Dict[str, Dict[str, Any]] = {}

# MCP Tool Implementations

@router.post("/begin_chat_thread")
async def begin_chat_thread(request: BeginChatThreadRequest) -> MCPToolResponse:
    """
    Tool: begin_chat_thread
    Returns: { "conversationId": "<string>" }
    """
    try:
        conversation_id = new_id()
        
        # Initialize conversation in storage
        _mcp_conversations[conversation_id] = {
            "id": conversation_id,
            "messages": [],
            "status": "working",
            "guidance": "Conversation started. You can now send messages.",
            "conversation_ended": False,
            "created_at": iso8601_now()
        }
        
        # Create response
        response_data = BeginChatResponse(conversationId=conversation_id)
        return MCPToolResponse(
            content=[MCPTextContent(text=response_data.model_dump_json())]
        )
        
    except Exception as e:
        error_response = {"error": f"Failed to begin chat thread: {str(e)}"}
        return MCPToolResponse(
            content=[MCPTextContent(text=str(error_response))]
        )

@router.post("/send_message_to_chat_thread")
async def send_message_to_chat_thread(request: SendMessageRequest) -> MCPToolResponse:
    """
    Tool: send_message_to_chat_thread
    Input: { conversationId, message, attachments? }
    Returns: { guidance, status }
    """
    try:
        conversation_id = request.conversationId
        
        # Trace wire inbound for MCP
        trace(conversation_id, "system", "wire_inbound", {
            "protocol": "mcp",
            "method": "send_message_to_chat_thread",
            "message_length": len(request.message),
            "attachments_count": len(request.attachments) if request.attachments else 0
        })
        
        # Check if conversation exists
        if conversation_id not in _mcp_conversations:
            error_response = {"error": "Conversation not found"}
            return MCPToolResponse(
                content=[MCPTextContent(text=str(error_response))]
            )
        
        conversation = _mcp_conversations[conversation_id]
        
        # Add user message to conversation
        user_message = MCPMessage(
            **{"from": "user"},
            at=iso8601_now(),
            text=request.message,
            attachments=request.attachments or []
        )
        conversation["messages"].append(user_message.model_dump())
        
        # Extract attachment file names if any
        incoming_files = []
        if request.attachments:
            incoming_files = [att.name for att in request.attachments]
        
        # Process through conversation engine
        result = conversation_engine.drive_turn(
            context_id=conversation_id,
            incoming_text=request.message,
            incoming_files=incoming_files if incoming_files else None,
            role="applicant"
        )
        
        # Add agent response messages to conversation
        for message in result["messages"]:
            agent_message = MCPMessage(
                **{"from": message["role"]},
                at=message["timestamp"],
                text=message["content"],
                attachments=[]
            )
            conversation["messages"].append(agent_message.model_dump())
        
        # Update conversation status and guidance based on engine result
        status = "completed" if result["status"] == "completed" else "working"
        conversation["status"] = status
        
        if status == "completed":
            conversation["guidance"] = "Task completed successfully."
            conversation["conversation_ended"] = True
        elif status == "input-required":
            conversation["guidance"] = "Additional input required to continue."
        else:
            conversation["guidance"] = "Processing your request..."
        
        # Create response
        response_data = SendMessageResponse(
            guidance=conversation["guidance"],
            status=cast(Literal["working", "input-required", "completed"], status)
        )
        
        response_obj = MCPToolResponse(
            content=[MCPTextContent(text=response_data.model_dump_json())]
        )
        
        # Trace wire outbound for MCP
        trace(conversation_id, "system", "wire_outbound", {
            "protocol": "mcp",
            "method": "send_message_to_chat_thread",
            "status": "success",
            "response_status": status,
            "response_size": len(response_data.model_dump_json())
        })
        
        return response_obj
        
    except Exception as e:
        error_response = {"error": f"Failed to send message: {str(e)}"}
        
        # Trace wire outbound error for MCP  
        trace(conversation_id, "system", "wire_outbound", {
            "protocol": "mcp",
            "method": "send_message_to_chat_thread",
            "status": "error",
            "error": str(e)
        })
        
        return MCPToolResponse(
            content=[MCPTextContent(text=str(error_response))]
        )

@router.post("/check_replies")
async def check_replies(request: CheckRepliesRequest) -> MCPToolResponse:
    """
    Tool: check_replies
    Input: { conversationId, waitMs? }
    Returns: { messages, guidance, status, conversation_ended }
    """
    try:
        conversation_id = request.conversationId
        
        # Check if conversation exists
        if conversation_id not in _mcp_conversations:
            error_response = {"error": "Conversation not found"}
            return MCPToolResponse(
                content=[MCPTextContent(text=str(error_response))]
            )
        
        conversation = _mcp_conversations[conversation_id]
        
        # Simulate wait time if specified
        if request.waitMs and request.waitMs > 0:
            await asyncio.sleep(min(request.waitMs / 1000.0, 5.0))  # Max 5 seconds
        
        # Get messages from administrator only (as specified in the spec)
        admin_messages = []
        for msg in conversation["messages"]:
            if msg.get("from") == "administrator":
                admin_messages.append(MCPMessage(**msg))
        
        # Create response
        response_data = CheckRepliesResponse(
            messages=admin_messages,
            guidance=conversation.get("guidance", "No new updates."),
            status=cast(Literal["working", "input-required", "completed"], conversation.get("status", "working")),
            conversation_ended=conversation.get("conversation_ended", False)
        )
        
        return MCPToolResponse(
            content=[MCPTextContent(text=response_data.model_dump_json())]
        )
        
    except Exception as e:
        error_response = {"error": f"Failed to check replies: {str(e)}"}
        return MCPToolResponse(
            content=[MCPTextContent(text=str(error_response))]
        )

# Legacy endpoints for compatibility (can be removed later)
@router.get("/conversations")
async def list_conversations():
    """Get all MCP conversations"""
    conversations = list(_mcp_conversations.values())
    return {"conversations": [{"id": conv["id"], "message_count": len(conv["messages"])} for conv in conversations]}

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific MCP conversation"""
    conversation = _mcp_conversations.get(conversation_id)
    if conversation:
        return {"conversation": conversation}
    raise HTTPException(status_code=404, detail="Conversation not found")