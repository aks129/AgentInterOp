"""
A2A (Agent-to-Agent) Protocol Router with JSON-RPC and SSE
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Literal, cast
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from app.store.memory import task_store, conversation_store, new_id, iso8601_now, encode_base64, decode_base64, trace

router = APIRouter()

# Pydantic models for A2A task snapshots and JSON-RPC structures

class FileModel(BaseModel):
    """File model for artifacts and message parts"""
    name: str
    mimeType: str
    bytes: str  # base64 encoded

class ArtifactModel(BaseModel):
    """Artifact model"""
    kind: Literal["file"] = "file"
    file: FileModel

class MessagePartText(BaseModel):
    """Text message part"""
    kind: Literal["text"] = "text"
    text: str

class MessagePartFile(BaseModel):
    """File message part"""
    kind: Literal["file"] = "file"
    file: FileModel

class HistoryMessage(BaseModel):
    """History message entry"""
    role: Literal["user", "agent"]
    parts: List[Union[MessagePartText, MessagePartFile]]

class TaskStatus(BaseModel):
    """Task status"""
    state: Literal["submitted", "working", "input-required", "completed", "failed", "canceled"]

class TaskSnapshot(BaseModel):
    """A2A Task snapshot shape"""
    id: str
    contextId: str
    status: TaskStatus
    artifacts: List[ArtifactModel] = Field(default_factory=list)
    history: List[HistoryMessage] = Field(default_factory=list)
    kind: Literal["task"] = "task"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request"""
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response"""
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class JsonRpcError(BaseModel):
    """JSON-RPC error"""
    code: int
    message: str
    data: Optional[Any] = None

# In-memory storage for tasks
_active_tasks: Dict[str, TaskSnapshot] = {}

# Conversation engine integration
from app.engine import conversation_engine

async def drive_turn_a2a(context_id: str, parts: List[Union[MessagePartText, MessagePartFile]]) -> tuple[List[Union[MessagePartText, MessagePartFile]], List[ArtifactModel], str]:
    """
    A2A conversation engine integration
    Returns: (agent_message_parts, artifacts, new_state)
    """
    # Extract text from message parts
    incoming_text = None
    incoming_files = []
    
    for part in parts:
        if isinstance(part, MessagePartText):
            incoming_text = part.text
        elif isinstance(part, MessagePartFile):
            incoming_files.append(part.file.name)
    
    # Drive conversation turn
    result = conversation_engine.drive_turn(
        context_id=context_id,
        incoming_text=incoming_text,
        incoming_files=incoming_files if incoming_files else None,
        role="applicant"
    )
    
    # Convert response messages to A2A message parts
    agent_parts: List[Union[MessagePartText, MessagePartFile]] = []
    for message in result["messages"]:
        agent_parts.append(MessagePartText(kind="text", text=message["content"]))
    
    # Convert artifacts to A2A format
    artifacts: List[ArtifactModel] = []
    for name, base64_content in result["artifacts"].items():
        # Determine MIME type
        mime_type = "application/fhir+json" if name.endswith(".json") else "application/octet-stream"
        
        artifact = ArtifactModel(
            kind="file",
            file=FileModel(
                name=name,
                mimeType=mime_type,
                bytes=base64_content
            )
        )
        artifacts.append(artifact)
    
    # Convert status to A2A state
    state = "completed" if result["status"] == "completed" else "working"
    
    return agent_parts, artifacts, state

# JSON-RPC method handlers

async def handle_message_send(params: Dict[str, Any], request_id: Optional[Union[str, int]]) -> JsonRpcResponse:
    """Handle message/send JSON-RPC method"""
    try:
        # Extract parameters
        task_id = params.get("taskId", new_id())
        context_id = params.get("contextId", new_id())
        parts = params.get("parts", [])
        
        # Trace wire inbound
        trace(context_id, "system", "wire_inbound", {
            "protocol": "a2a",
            "method": "message/send",
            "task_id": task_id,
            "parts_count": len(parts),
            "request_size": len(str(params))
        })
        
        # Create or get task
        if task_id not in _active_tasks:
            _active_tasks[task_id] = TaskSnapshot(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="submitted"),
                history=[],
                artifacts=[]
            )
        
        task = _active_tasks[task_id]
        
        # Add user message to history
        user_message = HistoryMessage(role="user", parts=parts)
        task.history.append(user_message)
        task.status.state = "working"
        
        # Process through conversation engine
        agent_parts, artifacts, new_state = await drive_turn_a2a(context_id, parts)
        
        # Add agent response to history
        agent_message = HistoryMessage(role="agent", parts=agent_parts)
        task.history.append(agent_message)
        
        # Update artifacts and status
        task.artifacts.extend(artifacts)
        valid_states = ["submitted", "working", "input-required", "completed", "failed", "canceled"]
        if new_state in valid_states:
            task.status = TaskStatus(state=cast(Literal["submitted", "working", "input-required", "completed", "failed", "canceled"], new_state))
        
        response_obj = JsonRpcResponse(id=request_id, result={"taskSnapshot": task.model_dump()})
        
        # Trace wire outbound
        trace(context_id, "system", "wire_outbound", {
            "protocol": "a2a", 
            "method": "message/send",
            "status": "success",
            "response_size": len(str(response_obj.model_dump())),
            "task_state": task.status.state
        })
        
        return response_obj
        
    except Exception as e:
        error_response = JsonRpcResponse(
            id=request_id,
            error=JsonRpcError(code=-32000, message="Internal error", data=str(e)).model_dump()
        )
        
        # Trace wire outbound error
        context_id = params.get("contextId", "unknown")
        trace(context_id, "system", "wire_outbound", {
            "protocol": "a2a",
            "method": "message/send", 
            "status": "error",
            "error": str(e)
        })
        
        return error_response

async def handle_tasks_get(params: Dict[str, Any], request_id: Optional[Union[str, int]]) -> JsonRpcResponse:
    """Handle tasks/get JSON-RPC method"""
    try:
        task_id = params.get("taskId")
        if not task_id:
            return JsonRpcResponse(
                id=request_id,
                error=JsonRpcError(code=-32602, message="Invalid params", data="taskId required").model_dump()
            )
        
        task = _active_tasks.get(task_id)
        if not task:
            return JsonRpcResponse(
                id=request_id,
                error=JsonRpcError(code=-32001, message="Task not found").model_dump()
            )
        
        return JsonRpcResponse(id=request_id, result={"taskSnapshot": task.model_dump()})
        
    except Exception as e:
        return JsonRpcResponse(
            id=request_id,
            error=JsonRpcError(code=-32000, message="Internal error", data=str(e)).model_dump()
        )

async def handle_tasks_cancel(params: Dict[str, Any], request_id: Optional[Union[str, int]]) -> JsonRpcResponse:
    """Handle tasks/cancel JSON-RPC method"""
    try:
        task_id = params.get("taskId")
        if not task_id:
            return JsonRpcResponse(
                id=request_id,
                error=JsonRpcError(code=-32602, message="Invalid params", data="taskId required").model_dump()
            )
        
        task = _active_tasks.get(task_id)
        if not task:
            return JsonRpcResponse(
                id=request_id,
                error=JsonRpcError(code=-32001, message="Task not found").model_dump()
            )

        # Capture the previous state before modification
        previous_state = task.status.state

        # Cancel the task and set terminal state
        task.status.state = "canceled"

        # Append trace event for cancellation
        trace(task.contextId, "system", "task_canceled", {
            "task_id": task_id,
            "previous_state": previous_state,
            "cancellation_time": iso8601_now()
        })
        
        return JsonRpcResponse(id=request_id, result={"taskSnapshot": task.model_dump()})
        
    except Exception as e:
        return JsonRpcResponse(
            id=request_id,
            error=JsonRpcError(code=-32000, message="Internal error", data=str(e)).model_dump()
        )

async def handle_tasks_resubscribe(params: Dict[str, Any], request_id: Optional[Union[str, int]]):
    """Handle tasks/resubscribe JSON-RPC method with SSE"""
    try:
        task_id = params.get("id")
        if not task_id:
            # Return error as SSE event
            async def error_generator():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": JsonRpcError(code=-32602, message="Invalid params", data="id required").model_dump()
                    })
                }
            return EventSourceResponse(error_generator())
        
        task = _active_tasks.get(task_id)
        if not task:
            # Return error as SSE event
            async def error_generator():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": JsonRpcError(code=-32001, message="Task not found").model_dump()
                    })
                }
            return EventSourceResponse(error_generator())
        
        # Trace resubscription
        trace(task.contextId, "system", "task_resubscribed", {
            "task_id": task_id,
            "current_state": task.status.state,
            "resubscribe_time": iso8601_now()
        })
        
        async def event_generator():
            # Emit current task snapshot
            yield {
                "event": "snapshot",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"taskSnapshot": task.model_dump()}
                })
            }
            
            # If task is still working, emit status update
            if task.status.state == "working":
                yield {
                    "event": "status-update",
                    "data": json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"status": task.status.model_dump()}
                    })
                }
            
            # Emit message frames for existing history
            for history_msg in task.history:
                if history_msg.role == "agent":
                    for part in history_msg.parts:
                        yield {
                            "event": "message-frame",
                            "data": json.dumps({
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {"messagePart": part.model_dump()}
                            })
                        }
            
            # Emit final snapshot with artifacts
            yield {
                "event": "snapshot-final",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"taskSnapshot": task.model_dump()}
                })
            }
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        # Return error as SSE event
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": JsonRpcError(code=-32000, message="Internal error", data=str(e)).model_dump()
                })
            }
        
        return EventSourceResponse(error_generator())

async def handle_message_stream(params: Dict[str, Any], request_id: Optional[Union[str, int]]):
    """Handle message/stream JSON-RPC method with SSE"""
    try:
        # Extract parameters
        task_id = params.get("taskId", new_id())
        context_id = params.get("contextId", new_id())
        parts = params.get("parts", [])
        
        # Create or get task
        if task_id not in _active_tasks:
            _active_tasks[task_id] = TaskSnapshot(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="submitted"),
                history=[],
                artifacts=[]
            )
        
        task = _active_tasks[task_id]
        
        async def event_generator():
            # Emit initial snapshot
            yield {
                "event": "snapshot",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"taskSnapshot": task.model_dump()}
                })
            }
            
            # Add user message to history
            user_message = HistoryMessage(role="user", parts=parts)
            task.history.append(user_message)
            task.status.state = "working"
            
            # Emit status update
            yield {
                "event": "status-update",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"status": task.status.model_dump()}
                })
            }
            
            # Process through conversation engine
            agent_parts, artifacts, new_state = await drive_turn_a2a(context_id, parts)
            
            # Emit message frame for each agent part
            for part in agent_parts:
                yield {
                    "event": "message-frame",
                    "data": json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"messagePart": part.model_dump()}
                    })
                }
            
            # Add agent response to history
            agent_message = HistoryMessage(role="agent", parts=agent_parts)
            task.history.append(agent_message)
            
            # Update artifacts and status
            task.artifacts.extend(artifacts)
            valid_states = ["submitted", "working", "input-required", "completed", "failed", "canceled"]
            if new_state in valid_states:
                task.status = TaskStatus(state=cast(Literal["submitted", "working", "input-required", "completed", "failed", "canceled"], new_state))
            
            # Emit final status with final=true
            yield {
                "event": "status-update",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "status": task.status.model_dump(),
                        "final": True,
                        "taskSnapshot": task.model_dump()
                    }
                })
            }
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        # Return error as SSE event
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": JsonRpcError(code=-32000, message="Internal error", data=str(e)).model_dump()
                })
            }
        
        return EventSourceResponse(error_generator())

# Route handlers

@router.post("/bridge/{config64}/a2a")
async def a2a_jsonrpc_handler(config64: str, request: Request):
    """
    Main A2A JSON-RPC handler with method inspection
    Base path: /api/bridge/{config64}/a2a (config64 may be ignored for now)
    """
    try:
        # Parse JSON-RPC request
        body = await request.json()
        rpc_request = JsonRpcRequest(**body)
        
        # Check for streaming requests that require SSE
        streaming_methods = ["message/stream", "tasks/resubscribe"]
        if rpc_request.method in streaming_methods:
            # Check Accept header for SSE
            accept_header = request.headers.get("accept", "")
            if "text/event-stream" in accept_header:
                if rpc_request.method == "message/stream":
                    return await handle_message_stream(rpc_request.params or {}, rpc_request.id)
                elif rpc_request.method == "tasks/resubscribe":
                    return await handle_tasks_resubscribe(rpc_request.params or {}, rpc_request.id)
            else:
                return JsonRpcResponse(
                    id=rpc_request.id,
                    error=JsonRpcError(code=-32600, message="Invalid request", data=f"{rpc_request.method} requires Accept: text/event-stream").model_dump()
                ).model_dump()
        
        # Handle other methods
        if rpc_request.method == "message/send":
            response = await handle_message_send(rpc_request.params or {}, rpc_request.id)
        elif rpc_request.method == "tasks/get":
            response = await handle_tasks_get(rpc_request.params or {}, rpc_request.id)
        elif rpc_request.method == "tasks/cancel":
            response = await handle_tasks_cancel(rpc_request.params or {}, rpc_request.id)
        else:
            response = JsonRpcResponse(
                id=rpc_request.id,
                error=JsonRpcError(code=-32601, message="Method not found").model_dump()
            )
        
        return response.model_dump()
        
    except Exception as e:
        return JsonRpcResponse(
            id=None,
            error=JsonRpcError(code=-32700, message="Parse error", data=str(e)).model_dump()
        ).model_dump()

# Legacy endpoints for compatibility (can be removed later)
@router.get("/tasks")
async def list_tasks():
    """Get all A2A tasks"""
    tasks = list(_active_tasks.values())
    return {"tasks": [{"id": task.id, "status": task.status.state} for task in tasks]}

@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific A2A task"""
    task = _active_tasks.get(task_id)
    if task:
        return {"taskSnapshot": task.model_dump()}
    raise HTTPException(status_code=404, detail="Task not found")