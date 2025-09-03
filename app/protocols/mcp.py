"""
MCP (Model Context Protocol) Tools Router
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal, Union, cast
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.store.memory import conversation_store, new_id, iso8601_now

router = APIRouter()

# Import the shared conversation engine from A2A
from app.protocols.a2a import drive_turn, MessagePartText, MessagePartFile

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
        
        # Convert message to drive_turn format
        parts: List[Union[MessagePartText, MessagePartFile]] = [
            MessagePartText(kind="text", text=request.message)
        ]
        
        # Add attachments as file parts
        if request.attachments:
            for attachment in request.attachments:
                from app.protocols.a2a import FileModel
                file_model = FileModel(
                    name=attachment.name,
                    mimeType=attachment.contentType,
                    bytes=attachment.content
                )
                file_part = MessagePartFile(
                    kind="file",
                    file=file_model
                )
                parts.append(file_part)
        
        # Process through shared conversation engine
        agent_parts, artifacts, new_state = await drive_turn(parts)
        
        # Add agent response to conversation
        agent_text = ""
        for part in agent_parts:
            if isinstance(part, MessagePartText):
                agent_text += part.text + " "
        
        agent_message = MCPMessage(
            **{"from": "administrator"},
            at=iso8601_now(),
            text=agent_text.strip(),
            attachments=[]  # Artifacts could be converted to attachments if needed
        )
        conversation["messages"].append(agent_message.model_dump())
        
        # Update conversation status and guidance
        valid_states = ["working", "input-required", "completed"]
        status = new_state if new_state in valid_states else "completed"
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
        
        return MCPToolResponse(
            content=[MCPTextContent(text=response_data.model_dump_json())]
        )
        
    except Exception as e:
        error_response = {"error": f"Failed to send message: {str(e)}"}
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