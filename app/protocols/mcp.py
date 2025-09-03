"""
MCP (Model Context Protocol) Router
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.store.memory import conversation_store, new_id

router = APIRouter()

class MCPMessageRequest(BaseModel):
    conversation_id: str = ""
    role: str = "user"
    content: str

class MCPConversationResponse(BaseModel):
    conversation_id: str

@router.get("/conversations")
async def list_conversations():
    """Get all MCP conversations"""
    conversations = conversation_store.list_conversations()
    return {"conversations": [{"id": conv.conversation_id, "message_count": len(conv.messages)} for conv in conversations]}

@router.post("/conversations", response_model=MCPConversationResponse)
async def create_conversation():
    """Create a new MCP conversation"""
    conversation = conversation_store.create_conversation()
    return MCPConversationResponse(conversation_id=conversation.conversation_id)

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific MCP conversation"""
    conversation = conversation_store.get_conversation(conversation_id)
    if conversation:
        return {"id": conversation.conversation_id, "messages": [{"role": msg.role, "content": msg.content} for msg in conversation.messages]}
    return {"error": "Conversation not found"}

@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, request: MCPMessageRequest):
    """Add a message to a conversation"""
    message = conversation_store.add_message(conversation_id, request.role, request.content)
    if message:
        return {"message_id": message.id, "role": message.role, "content": message.content}
    return {"error": "Conversation not found"}