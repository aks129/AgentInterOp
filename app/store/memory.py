"""
In-memory stores for TaskStore and ConversationStore with helper utilities
"""
import uuid
import base64
from datetime import datetime, timedelta
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
class TraceEvent:
    """Decision trace event"""
    timestamp: str = field(default_factory=iso8601_now)
    actor: str = ""  # applicant, administrator, scenario, system
    action: str = ""  # evaluate, decision, wire_inbound, wire_outbound
    detail: Dict[str, Any] = field(default_factory=dict)

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
    
    def __init__(self, max_tasks: int = 100, cleanup_hours: int = 1):
        self._tasks: Dict[str, A2ATask] = {}
        self.max_tasks = max_tasks
        self.cleanup_hours = cleanup_hours
    
    def create_task(self, method: str, params: Optional[Dict[str, Any]] = None) -> A2ATask:
        """Create a new task"""
        # Clean up old tasks if at capacity
        if len(self._tasks) >= self.max_tasks:
            self._cleanup_old_tasks()
        
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
    
    def _cleanup_old_tasks(self) -> int:
        """Remove old completed/failed tasks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cleanup_hours)
        tasks_to_remove = []
        
        for task_id, task in self._tasks.items():
            task_time = datetime.fromisoformat(task.updated_at.replace('Z', '+00:00'))
            if (task.status in ['completed', 'failed'] and 
                task_time < cutoff_time):
                tasks_to_remove.append(task_id)
        
        # Remove oldest tasks first if still over limit
        if len(tasks_to_remove) < len(self._tasks) - self.max_tasks // 2:
            all_tasks = sorted(self._tasks.items(), 
                             key=lambda x: x[1].updated_at)
            for task_id, _ in all_tasks[:len(self._tasks) - self.max_tasks // 2]:
                if task_id not in tasks_to_remove:
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
        
        return len(tasks_to_remove)


class ConversationStore:
    """In-memory store for MCP chat threads (dict by conversationId)"""
    
    def __init__(self, max_conversations: int = 100, cleanup_hours: int = 1):
        self._conversations: Dict[str, MCPConversation] = {}
        self.max_conversations = max_conversations
        self.cleanup_hours = cleanup_hours
    
    def create_conversation(self) -> MCPConversation:
        """Create a new conversation"""
        # Clean up old conversations if at capacity
        if len(self._conversations) >= self.max_conversations:
            self._cleanup_old_conversations()
        
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
    
    def _cleanup_old_conversations(self) -> int:
        """Remove old conversations"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cleanup_hours)
        convs_to_remove = []
        
        for conv_id, conv in self._conversations.items():
            conv_time = datetime.fromisoformat(conv.updated_at.replace('Z', '+00:00'))
            if conv_time < cutoff_time:
                convs_to_remove.append(conv_id)
        
        # Remove oldest conversations first if still over limit
        if len(convs_to_remove) < len(self._conversations) - self.max_conversations // 2:
            all_convs = sorted(self._conversations.items(), 
                             key=lambda x: x[1].updated_at)
            for conv_id, _ in all_convs[:len(self._conversations) - self.max_conversations // 2]:
                if conv_id not in convs_to_remove:
                    convs_to_remove.append(conv_id)
        
        for conv_id in convs_to_remove:
            del self._conversations[conv_id]
        
        return len(convs_to_remove)


class TraceStore:
    """In-memory store for decision traces per context"""
    
    def __init__(self, max_traces_per_context: int = 100, cleanup_hours: int = 2):
        self._traces: Dict[str, list[TraceEvent]] = {}  # context_id -> list of events
        self.max_traces_per_context = max_traces_per_context
        self.cleanup_hours = cleanup_hours
    
    def trace(self, context_id: str, actor: str, action: str, detail_dict: Dict[str, Any]) -> TraceEvent:
        """Add a trace event for a context"""
        if context_id not in self._traces:
            self._traces[context_id] = []
        
        event = TraceEvent(actor=actor, action=action, detail=detail_dict)
        self._traces[context_id].append(event)
        
        # Limit events per context
        if len(self._traces[context_id]) > self.max_traces_per_context:
            self._traces[context_id] = self._traces[context_id][-self.max_traces_per_context:]
        
        return event
    
    def get_trace(self, context_id: str) -> list[TraceEvent]:
        """Get all trace events for a context"""
        return self._traces.get(context_id, [])
    
    def list_contexts(self) -> list[str]:
        """Get all context IDs with traces"""
        return list(self._traces.keys())
    
    def delete_trace(self, context_id: str) -> bool:
        """Delete all traces for a context"""
        if context_id in self._traces:
            del self._traces[context_id]
            return True
        return False
    
    def cleanup_old_traces(self) -> int:
        """Remove old trace events"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cleanup_hours)
        removed_count = 0
        
        for context_id in list(self._traces.keys()):
            events = self._traces[context_id]
            # Keep events newer than cutoff
            filtered_events = []
            for event in events:
                event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                if event_time >= cutoff_time:
                    filtered_events.append(event)
                else:
                    removed_count += 1
            
            if filtered_events:
                self._traces[context_id] = filtered_events
            else:
                del self._traces[context_id]
        
        return removed_count


# Global store instances
task_store = TaskStore()
conversation_store = ConversationStore()
trace_store = TraceStore()

# Helper function for easy tracing
def trace(context_id: str, actor: str, action: str, detail_dict: Dict[str, Any]) -> TraceEvent:
    """Global helper function to add trace events"""
    return trace_store.trace(context_id, actor, action, detail_dict)