"""A2A proxy for remote messaging with streaming support"""
import httpx
import json
import uuid
from typing import Dict, Any, AsyncGenerator, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse


async def proxy_a2a_message(
    target_url: str,
    rpc_payload: Dict[str, Any], 
    stream: bool = False,
    timeout: float = 10.0
) -> Dict[str, Any]:
    """
    Proxy A2A message to remote endpoint.
    
    Args:
        target_url: Remote A2A JSON-RPC endpoint
        rpc_payload: JSON-RPC payload to send
        stream: Whether to expect streaming response
        timeout: Request timeout in seconds
    
    Returns:
        Response data or raises HTTPException
    """
    # Validate JSON-RPC payload
    if not isinstance(rpc_payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC payload")
    
    if not rpc_payload.get("jsonrpc") == "2.0":
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC version")
    
    if not rpc_payload.get("method"):
        raise HTTPException(status_code=400, detail="JSON-RPC method is required")
    
    # Ensure id is present
    if not rpc_payload.get("id"):
        rpc_payload["id"] = str(uuid.uuid4())
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if stream:
        headers["Accept"] = "text/event-stream"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if stream:
                # Handle streaming response
                async with client.stream(
                    "POST",
                    target_url,
                    json=rpc_payload,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Remote server error: {error_text.decode()}"
                        )
                    
                    # Return streaming response
                    return StreamingResponse(
                        stream_sse_response(response),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive"
                        }
                    )
            else:
                # Handle regular response
                response = await client.post(target_url, json=rpc_payload, headers=headers)
                
                if response.status_code != 200:
                    error_detail = create_jsonrpc_error(
                        rpc_payload.get("id"),
                        -32001,  # Server error
                        f"Remote server returned {response.status_code}",
                        {"status_code": response.status_code, "response": response.text}
                    )
                    raise HTTPException(status_code=response.status_code, detail=error_detail)
                
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    error_detail = create_jsonrpc_error(
                        rpc_payload.get("id"),
                        -32700,  # Parse error
                        "Invalid JSON response from remote server"
                    )
                    raise HTTPException(status_code=502, detail=error_detail)
                
                return {
                    "success": True,
                    "data": response_data,
                    "status_code": response.status_code
                }
    
    except httpx.TimeoutException:
        error_detail = create_jsonrpc_error(
            rpc_payload.get("id"),
            -32002,  # Timeout error
            f"Request timeout after {timeout} seconds"
        )
        raise HTTPException(status_code=504, detail=error_detail)
    
    except httpx.ConnectError:
        error_detail = create_jsonrpc_error(
            rpc_payload.get("id"),
            -32003,  # Connection error
            f"Cannot connect to remote server: {target_url}"
        )
        raise HTTPException(status_code=502, detail=error_detail)
    
    except Exception as e:
        error_detail = create_jsonrpc_error(
            rpc_payload.get("id"),
            -32000,  # Server error
            f"Proxy error: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=error_detail)


async def stream_sse_response(response: httpx.Response) -> AsyncGenerator[str, None]:
    """Stream Server-Sent Events from remote response"""
    async for chunk in response.aiter_text():
        yield chunk


def create_jsonrpc_error(
    request_id: Optional[str],
    code: int,
    message: str,
    data: Optional[Any] = None
) -> Dict[str, Any]:
    """Create JSON-RPC 2.0 error response"""
    error = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }
    
    if data is not None:
        error["error"]["data"] = data
    
    return error


def validate_jsonrpc_payload(payload: Dict[str, Any]) -> bool:
    """Validate JSON-RPC 2.0 payload format"""
    if not isinstance(payload, dict):
        return False
    
    # Required fields
    if payload.get("jsonrpc") != "2.0":
        return False
    
    if not payload.get("method"):
        return False
    
    # Optional but should be present for requests
    if "id" not in payload:
        return False
    
    return True


def create_message_send_payload(
    message_parts: list,
    task_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a message/send JSON-RPC payload"""
    if not request_id:
        request_id = str(uuid.uuid4())
    
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "parts": message_parts
            }
        }
    }
    
    if task_id:
        payload["params"]["taskId"] = task_id
    
    return payload


def create_message_stream_payload(
    message_parts: list,
    task_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a message/stream JSON-RPC payload"""
    if not request_id:
        request_id = str(uuid.uuid4())
    
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/stream",
        "params": {
            "message": {
                "parts": message_parts
            }
        }
    }
    
    if task_id:
        payload["params"]["taskId"] = task_id
    
    return payload


def create_tasks_get_payload(
    task_id: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a tasks/get JSON-RPC payload"""
    if not request_id:
        request_id = str(uuid.uuid4())
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tasks/get",
        "params": {
            "taskId": task_id
        }
    }


def create_tasks_cancel_payload(
    task_id: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a tasks/cancel JSON-RPC payload"""
    if not request_id:
        request_id = str(uuid.uuid4())
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tasks/cancel",
        "params": {
            "taskId": task_id
        }
    }