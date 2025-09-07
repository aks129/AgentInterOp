# Security Patches - Actionable Fix Set

## Critical Patches (Apply Before Demo)

### Patch 1: Add Rate Limiting
**File: `app/main.py`** (Add after imports)

```python
# Add rate limiting imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter (add after app creation)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add to api/requirements.txt:
# slowapi==0.1.9
```

**Apply to endpoints:**
```python
# Add decorator to sensitive endpoints
@limiter.limit("30/minute")
@app.post("/api/bridge/bcse/a2a")
async def bcse_a2a_handler(request: Request, ...):

@limiter.limit("100/hour") 
@app.post("/api/mcp/bcse/send_message_to_chat_thread")
async def mcp_send_message(request: Request, ...):
```

### Patch 2: Input Validation & Size Limits
**File: `app/protocols/a2a.py`** (Replace line 134-210)

```python
# Add size validation
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
MAX_PARTS_COUNT = 100

async def handle_message_send(params: Dict[str, Any], request_id: Optional[Union[str, int]]) -> JsonRpcResponse:
    """Handle message/send JSON-RPC method with validation"""
    try:
        # Validate request size
        request_size = len(str(params))
        if request_size > MAX_MESSAGE_SIZE:
            return JsonRpcResponse(
                id=request_id,
                error=JsonRpcError(code=-32602, message="Request too large", data=f"Size: {request_size} bytes").model_dump()
            )
        
        # Extract and validate parameters
        task_id = params.get("taskId", new_id())
        context_id = params.get("contextId", new_id())
        parts = params.get("parts", [])
        
        # Validate parts count
        if len(parts) > MAX_PARTS_COUNT:
            return JsonRpcResponse(
                id=request_id,
                error=JsonRpcError(code=-32602, message="Too many message parts", data=f"Max: {MAX_PARTS_COUNT}").model_dump()
            )
        
        # Validate each part
        for i, part in enumerate(parts):
            if not isinstance(part, dict):
                return JsonRpcResponse(
                    id=request_id,
                    error=JsonRpcError(code=-32602, message=f"Invalid part format at index {i}").model_dump()
                )
            
            if part.get("kind") == "text":
                text = part.get("text", "")
                if len(text) > MAX_MESSAGE_SIZE:
                    return JsonRpcResponse(
                        id=request_id,
                        error=JsonRpcError(code=-32602, message=f"Text part {i} too large").model_dump()
                    )
        
        # Continue with existing logic...
        # [Rest of original function]
```

### Patch 3: Base64 Validation  
**File: `app/main.py`** (Replace line 156-192)

```python
import base64
import binascii

MAX_ARTIFACT_SIZE = 10 * 1024 * 1024  # 10MB

@app.get("/artifacts/{task_id}/{name}")
async def download_artifact(task_id: str, name: str):
    """Download artifact by task_id and filename with validation"""
    
    # Validate task_id format (prevent path traversal)
    if not re.match(r'^[a-zA-Z0-9_-]+$', task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    # Validate filename (prevent path traversal)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name) or '..' in name:
        raise HTTPException(status_code=400, detail="Invalid filename format")
    
    # First, check conversation engine artifacts
    from app.engine import conversation_engine
    conv_state = conversation_engine.get_conversation_state(task_id)
    
    if conv_state and "artifacts" in conv_state and name in conv_state["artifacts"]:
        base64_content = conv_state["artifacts"][name]
        
        # Validate base64 content
        if not base64_content or not isinstance(base64_content, str):
            raise HTTPException(status_code=400, detail="Invalid artifact data")
        
        # Check size before decoding
        if len(base64_content) > MAX_ARTIFACT_SIZE * 4 / 3:  # Base64 expansion factor
            raise HTTPException(status_code=413, detail="Artifact too large")
        
        try:
            # Validate and decode base64 with strict validation
            content = base64.b64decode(base64_content, validate=True)
        except (binascii.Error, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 encoding: {str(e)}")
        
        # Determine safe MIME type
        mime_type = "application/fhir+json" if name.endswith(".json") else "application/octet-stream"
        
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache"
            }
        )
    
    # Continue with demo artifacts fallback...
```

### Patch 4: Secure Error Handling
**File: `app/protocols/mcp.py`** (Replace error handling sections)

```python
def sanitize_error_message(error: Exception, context: str = "") -> str:
    """Sanitize error messages to prevent information disclosure"""
    safe_messages = {
        "FileNotFoundError": "Resource not found",
        "PermissionError": "Access denied", 
        "ConnectionError": "Service unavailable",
        "TimeoutError": "Request timeout",
        "ValueError": "Invalid input",
        "KeyError": "Missing required field"
    }
    
    error_type = type(error).__name__
    safe_message = safe_messages.get(error_type, "Internal server error")
    
    # Log full error details for debugging (but don't return to client)
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    
    return safe_message

# Update error handling in MCP endpoints:
except Exception as e:
    safe_message = sanitize_error_message(e, "send_message_to_chat_thread")
    return MCPToolResponse(
        content=[MCPTextContent(text=json.dumps({"error": safe_message}))]
    )
```

### Patch 5: FHIR Token Redaction
**File: `app/config.py`** (Add after line 50)

```python
def redact_sensitive_config(config_dict: dict) -> dict:
    """Redact sensitive information from config dictionary"""
    redacted = config_dict.copy()
    
    # Redact FHIR tokens
    if "data" in redacted and "options" in redacted["data"]:
        options = redacted["data"]["options"]
        if "fhir_token" in options and options["fhir_token"]:
            options["fhir_token"] = "•••" + options["fhir_token"][-4:] if len(options["fhir_token"]) > 4 else "•••"
    
    # Redact any other tokens
    if "anthropic" in redacted and "api_key" in redacted["anthropic"]:
        key = redacted["anthropic"]["api_key"]
        redacted["anthropic"]["api_key"] = "•••" + key[-4:] if len(key) > 4 else "•••"
    
    return redacted
```

**Update config endpoints in `main.py`:**
```python
@app.route('/api/config')
def get_config():
    config = load_config()
    config_dict = json.loads(config.model_dump_json())
    
    if config.logging.redact_tokens:
        config_dict = redact_sensitive_config(config_dict)
    
    return jsonify(config_dict)
```

### Patch 6: HTTPS Enforcement
**File: `app/main.py`** (Add middleware)

```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

# Add security middleware (after app creation)
if os.getenv("APP_ENV") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["agent-inter-op.vercel.app", "*.vercel.app"]
    )

# Add CORS with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agent-inter-op.vercel.app"] if os.getenv("APP_ENV") == "production" else ["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("APP_ENV") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### Patch 7: Schema Validation
**File: `app/protocols/mcp.py`** (Add validation models)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional

class ValidatedSendMessageRequest(BaseModel):
    """Validated MCP send message request"""
    conversationId: str = Field(..., min_length=1, max_length=100, regex=r'^[a-zA-Z0-9_-]+$')
    message: str = Field(..., min_length=1, max_length=10000)
    attachments: Optional[List[MCPAttachment]] = Field(default=None, max_items=10)
    
    @validator('message')
    def validate_message_content(cls, v):
        # Basic XSS prevention
        if '<script' in v.lower() or 'javascript:' in v.lower():
            raise ValueError('Invalid message content')
        return v

class ValidatedCheckRepliesRequest(BaseModel):
    """Validated MCP check replies request"""  
    conversationId: str = Field(..., min_length=1, max_length=100, regex=r'^[a-zA-Z0-9_-]+$')
    waitMs: Optional[int] = Field(default=None, ge=0, le=30000)  # Max 30 second wait

# Update endpoint signatures:
@router.post("/send_message_to_chat_thread")
async def send_message_to_chat_thread(request: ValidatedSendMessageRequest) -> MCPToolResponse:
    # Function body remains the same, but input is now validated
```

## Medium Priority Patches

### Patch 8: Connection Timeouts
**File: `app/fhir/connector.py`**

```python
import httpx
from httpx import Timeout

class FHIRConnector:
    def __init__(self, base_url: str, token: str = None):
        timeout = Timeout(
            connect=10.0,  # 10 seconds to establish connection
            read=30.0,     # 30 seconds to read response  
            write=10.0,    # 10 seconds to write request
            pool=60.0      # 60 seconds total timeout
        )
        
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
```

### Patch 9: Memory Cleanup
**File: `app/store/memory.py`**

```python
import threading
import time
from datetime import datetime, timedelta

class MemoryStore:
    def __init__(self, max_size: int = 1000, cleanup_interval: int = 3600):
        self._data = {}
        self._access_times = {}
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()
    
    def _periodic_cleanup(self):
        """Periodic cleanup of old entries"""
        while True:
            time.sleep(self._cleanup_interval)
            self.cleanup_old_entries()
    
    def cleanup_old_entries(self, max_age_hours: int = 24):
        """Remove entries older than max_age_hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._lock:
            keys_to_remove = []
            for key, access_time in self._access_times.items():
                if access_time < cutoff_time:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._data.pop(key, None)
                self._access_times.pop(key, None)
    
    def _enforce_size_limit(self):
        """Enforce maximum size limit using LRU eviction"""
        if len(self._data) > self._max_size:
            # Remove oldest accessed items
            sorted_items = sorted(self._access_times.items(), key=lambda x: x[1])
            items_to_remove = len(self._data) - self._max_size
            
            for i in range(items_to_remove):
                key = sorted_items[i][0]
                self._data.pop(key, None)
                self._access_times.pop(key, None)
```

## Deployment Instructions

### 1. Install Dependencies
```bash
# Add to api/requirements.txt:
slowapi==0.1.9
httpx[http2]==0.27.2
```

### 2. Environment Variables
```bash
# Production environment variables
export APP_ENV=production
export SESSION_SECRET=$(openssl rand -base64 32)
export RATE_LIMIT_STORAGE_URL=redis://localhost:6379
export MAX_REQUEST_SIZE=10485760  # 10MB
```

### 3. Apply Patches in Order
1. Apply security middleware patches first
2. Add input validation to all endpoints  
3. Update error handling throughout
4. Add memory management cleanup
5. Deploy and test each patch

### 4. Testing After Patches
```bash
# Run security tests
pytest tests/ -v -k security
bandit -r app/
safety check

# Run integration tests  
pytest tests/test_protocols_integration.py -v

# Load testing
ab -n 1000 -c 10 https://agent-inter-op.vercel.app/api/selftest
```

### 5. Monitoring Setup
```python
# Add to app/main.py
import logging
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logging.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response with timing
    process_time = time.time() - start_time
    logging.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response
```

## Post-Demo Security Improvements

1. **Authentication System**: Implement OAuth2/JWT
2. **Database Migration**: Replace in-memory storage  
3. **API Gateway**: Add proper API management layer
4. **Audit Logging**: Comprehensive audit trail
5. **Dependency Scanning**: Automated vulnerability scanning
6. **Penetration Testing**: Third-party security assessment