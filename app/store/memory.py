"""
In-memory stores for TaskStore and ConversationStore with helper utilities
"""
import uuid
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel


# Helper functions
def new_id() -> str:
    """Generate a new UUID4 ID"""
    return str(uuid.uuid4())


def iso8601_now() -> str:
    """Get current time in ISO8601 format"""
    return datetime.utcnow().isoformat() + "Z"


def encode_base64(data: str) -> str:
    """Encode string to base64"""
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def decode_base64(encoded: str) -> str:
    """Decode base64 to string"""
    return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')


# Data models
@dataclass
class A2ATask:
    """A2A Task model"""
    id: str = field(default_factory=new_id)
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, completed, failed
    created_at: str = field(default_factory=iso8601_now)
    updated_at: str = field(default_factory=iso8601_now)


class MCPMessage(BaseModel):
    """MCP Chat message model"""
    id: str = ""
    role: str = "user"  # user, assistant, system
    content: str = ""
    timestamp: str = ""
    
    def __init__(self, **data):
        if not data.get('id'):
            data['id'] = new_id()
        if not data.get('timestamp'):
            data['timestamp'] = iso8601_now()
        super().__init__(**data)


@dataclass 
class MCPConversation:
    """MCP Conversation thread"""
    conversation_id: str = field(default_factory=new_id)
    messages: list[MCPMessage] = field(default_factory=list)
    created_at: str = field(default_factory=iso8601_now)
    updated_at: str = field(default_factory=iso8601_now)


# Store classes
class TaskStore:
    """In-memory store for A2A tasks (dict by id)"""
    
    def __init__(self):
        self._tasks: Dict[str, A2ATask] = {}
    
    def create_task(self, method: str, params: Optional[Dict[str, Any]] = None) -> A2ATask:
        """Create a new task"""
        task = A2ATask(method=method, params=params or {})
        self._tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[A2ATask]:
        """Get task by ID"""
        return self._tasks.get(task_id)
    
    def update_task(self, task_id: str, **updates) -> Optional[A2ATask]:
        """Update task fields"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = iso8601_now()
            return task
        return None
    
    def list_tasks(self) -> list[A2ATask]:
        """Get all tasks"""
        return list(self._tasks.values())
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task by ID"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


class ConversationStore:
    """In-memory store for MCP chat threads (dict by conversationId)"""
    
    def __init__(self):
        self._conversations: Dict[str, MCPConversation] = {}
    
    def create_conversation(self) -> MCPConversation:
        """Create a new conversation"""
        conversation = MCPConversation()
        self._conversations[conversation.conversation_id] = conversation
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[MCPConversation]:
        """Get conversation by ID"""
        return self._conversations.get(conversation_id)
    
    def add_message(self, conversation_id: str, role: str, content: str) -> Optional[MCPMessage]:
        """Add message to conversation"""
        if conversation_id in self._conversations:
            conversation = self._conversations[conversation_id]
            message = MCPMessage(role=role, content=content)
            conversation.messages.append(message)
            conversation.updated_at = iso8601_now()
            return message
        return None
    
    def list_conversations(self) -> list[MCPConversation]:
        """Get all conversations"""
        return list(self._conversations.values())
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation by ID"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False


# Global store instances
task_store = TaskStore()
conversation_store = ConversationStore()