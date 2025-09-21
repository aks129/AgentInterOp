from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime, timezone
from pathlib import Path
import os, json, time, base64

# Feature flags
UI_EXPERIMENTAL = os.getenv("UI_EXPERIMENTAL", "false").lower() == "true"

# Security constants
MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

def validate_json_size(content: bytes) -> None:
    """Validate JSON content size to prevent DoS attacks"""
    if len(content) > MAX_JSON_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Request too large. Maximum JSON size: {MAX_JSON_SIZE} bytes"
        )

# Create FastAPI app
app = FastAPI(
    title="AgentInterOp",
    version="1.0.0-bcse",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions and return JSON-RPC error for A2A endpoints"""
    # Check if this is an A2A endpoint
    if "/api/bridge/" in str(request.url.path) and request.url.path.endswith("/a2a"):
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(exc)}"
            }
        }
        return JSONResponse(content=error_response, status_code=500)

    # For other endpoints, return generic error
    return JSONResponse(
        content={"error": "Internal server error"},
        status_code=500
    )

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Configure for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for A2A interoperability
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],  # Include OPTIONS for preflight
    allow_headers=[
        "Content-Type",
        "Accept",
        "Authorization",
        "Transfer-Encoding",
        "X-Requested-With",
        "Cache-Control"
    ],
    max_age=600,
)

# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    # Content length validation
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        return JSONResponse(
            status_code=413,
            content={"error": f"Request too large. Maximum size: {MAX_CONTENT_LENGTH} bytes"}
        )
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com"
    return response

# Guard static/templates setup for Vercel compatibility
templates = None
try:
    from fastapi.templating import Jinja2Templates
    from fastapi.staticfiles import StaticFiles
    base = Path(__file__).resolve().parent
    static_dir = base / "web" / "static"
    templates_dir = base / "web" / "templates"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        print(f"[WARN] no static dir: {static_dir}")
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))
    else:
        print(f"[WARN] no templates dir: {templates_dir}")
except Exception as e:
    print(f"[WARN] static/templates setup skipped: {e}")

# Register scenarios first before including routers
from app.scenarios import registry
from app.scenarios import sc_bcse, sc_clinical_trial, sc_referral_specialist, sc_prior_auth, sc_custom

# Register scenarios - force registration at module load time
print(f"[INIT] Registering scenarios...", flush=True)
registry.register("bcse", sc_bcse)
registry.register("clinical_trial", sc_clinical_trial)
registry.register("referral_specialist", sc_referral_specialist)
registry.register("prior_auth", sc_prior_auth)
registry.register("custom", sc_custom)
print(f"[INIT] Scenarios registered: {list(registry._SCENARIOS.keys())}", flush=True)

# Include routers from protocols
from app.protocols.a2a import router as a2a_router
from app.protocols.mcp import router as mcp_router

app.include_router(a2a_router, prefix="/api/a2a", tags=["A2A Protocol"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Protocol"])

# Include BCS-specific routers
from app.protocols.a2a_bcse import router as a2a_bcse_router
from app.protocols.mcp_bcse import router as mcp_bcse_router
app.include_router(a2a_bcse_router)
app.include_router(mcp_bcse_router)

# Include scheduling router
from app.routers.scheduling import router as scheduling_router
app.include_router(scheduling_router)

# Include experimental router
from app.experimental.router import router as experimental_router
from app.experimental_v2.router import router as experimental_v2_router
app.include_router(experimental_router)
app.include_router(experimental_v2_router)

# Include canonical A2A router for Vercel deployment
from app.a2a_router import router as canonical_a2a_router
app.include_router(canonical_a2a_router)

# Include A2A Inspector for testing and debugging
from app.inspector.router import router as inspector_router
app.include_router(inspector_router)

# Include Banterop UI (experimental)
from app.banterop_ui.router import router as banterop_router
app.include_router(banterop_router)

# In-memory artifact storage for demo
demo_artifacts = {
    "demo-task": {
        "QuestionnaireResponse.json": {
            "mimeType": "application/fhir+json",
            "bytes": base64.b64encode(b'{"resourceType":"QuestionnaireResponse","status":"completed"}').decode()
        },
        "DecisionBundle.json": {
            "mimeType": "application/fhir+json", 
            "bytes": base64.b64encode(b'{"resourceType":"Bundle","type":"collection","entry":[]}').decode()
        }
    }
}

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.get("/version")
def version():
    return {"name": "AgentInterOp", "version": app.version, "scenario": "bcse"}

# Compatibility route for broken external inspectors that append /agent.json incorrectly
@app.get("/.well-known/agent-card.json/.well-known/agent.json")
@app.get("/.well-known/agent-card.json/agent.json")
def agent_card_compatibility_fallback(request: Request):
    """Handle malformed URLs from external inspectors that incorrectly append paths"""
    return agent_card(request)

@app.get("/.well-known/agent-card.json")
def agent_card(request: Request):
    base = str(request.base_url).rstrip("/")
    card = {
      "name": "AgentInterOp Healthcare Platform",
      "description": "A healthcare interoperability platform supporting A2A protocol for agent-to-agent communication with specialized healthcare scenarios including FHIR integration and BCS eligibility evaluation.",
      "version": "2.0.0-banterop",
      "protocolVersion": "0.4.0",
      "preferredTransport": "JSONRPC",
      "url": f"{base}/api/bridge/demo/a2a",
      "capabilities": {
        "streaming": True,
        "supportedMethods": [
          "message/send",
          "message/stream",
          "tasks/get",
          "tasks/cancel",
          "tasks/resubscribe"
        ]
      },
      "defaultInputModes": [
        "text/plain",
        "application/json",
        "application/fhir+json"
      ],
      "defaultOutputModes": [
        "text/plain",
        "application/json",
        "application/fhir+json"
      ],
      "supportsAuthenticatedExtendedCard": False,
      "skills": [
        {
          "id": "scenario",
          "name": "Healthcare Scenario Processing",
          "description": "Processes healthcare scenarios including breast cancer screening eligibility evaluation",
          "tags": ["healthcare", "interoperability", "bcs", "eligibility"],
          "discovery": {
            "url": f"{base}/api/bridge/demo/a2a"
          },
          "a2a.config64": base64.b64encode(b'{"scenario":"demo"}').decode()
        }
      ]
    }
    return JSONResponse(card)

@app.get("/.well-known/agent.json")
def adk_agent_metadata(request: Request):
    """ADK-compliant agent metadata endpoint for Google Agent Development Kit compliance"""
    base = str(request.base_url).rstrip("/")

    # ADK-compliant agent metadata
    adk_metadata = {
        "name": "AgentInterOp Healthcare Platform",
        "description": "Healthcare interoperability platform with A2A protocol support and FHIR integration",
        "version": "2.0.0-adk",
        "adk_version": "1.0",
        "endpoints": {
            "run": f"{base}/api/adk/run",
            "a2a": f"{base}/api/bridge/demo/a2a"
        },
        "capabilities": {
            "streaming": True,
            "healthcare_scenarios": True,
            "fhir_integration": True,
            "bcs_evaluation": True,
            "multi_protocol": ["A2A", "MCP"]
        },
        "models": ["healthcare-assistant"],
        "tools": [
            {
                "name": "fhir_patient_lookup",
                "description": "Fetch patient data from FHIR servers"
            },
            {
                "name": "bcs_eligibility_check",
                "description": "Evaluate breast cancer screening eligibility"
            },
            {
                "name": "healthcare_scheduling",
                "description": "Schedule healthcare appointments"
            }
        ],
        "protocols": {
            "a2a": {
                "version": "0.3.0",
                "transport": "JSONRPC",
                "endpoint": f"{base}/api/bridge/demo/a2a"
            },
            "mcp": {
                "version": "1.0",
                "transport": "HTTP",
                "endpoint": f"{base}/api/mcp"
            }
        },
        "interoperability": {
            "agent_discovery": True,
            "cross_platform": True,
            "standard_compliance": ["A2A", "FHIR-R4", "HL7"]
        }
    }

    return JSONResponse(adk_metadata)

@app.get("/api/selftest")
def selftest():
    from app.config import load_config
    try:
        config = load_config()
        active_scenario = config.scenario.active
        from app.scenarios.registry import list_scenarios
        available_scenarios = list(list_scenarios().keys())
    except Exception as e:
        active_scenario = f"ERROR: {e}"
        available_scenarios = []
        
    return {"ok": True,
            "a2a": ["message/send","message/stream","tasks/get","tasks/cancel"],
            "mcp": ["begin_chat_thread","send_message_to_chat_thread","check_replies"],
            "scenario": active_scenario,
            "available_scenarios": available_scenarios,
            "endpoints": {
                "a2a_comprehensive": "/api/a2a/bridge/{config64}/a2a",
                "a2a_bcse_simple": "/api/bridge/bcse/a2a", 
                "mcp_bcse": "/api/mcp/bcse/"
            }}

@app.get("/api/loopback/sse")
def loop_sse():
    import time
    def gen():
        yield "event: message\ndata: {\"kind\":\"task\",\"status\":{\"state\":\"working\"}}\n\n"
        time.sleep(0.3)
        yield "event: message\ndata: {\"role\":\"agent\",\"parts\":[{\"kind\":\"text\",\"text\":\"hello\"}],\"kind\":\"message\"}\n\n"
        time.sleep(0.3)
        yield "event: status-update\ndata: {\"final\":true,\"status\":{\"state\":\"completed\"}}\n\n"
    from fastapi.responses import StreamingResponse
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/trace/{contextId}/download")
def download_trace(contextId: str):
    from app.store.persistence import list_traces
    from fastapi.responses import JSONResponse
    return JSONResponse(list_traces(contextId))

# BCS REST endpoints
from app.scenarios import bcse as BCS

@app.post("/api/bcse/ingest/demo")
def bcse_ingest_demo():
    p = Path(__file__).resolve().parent / "demo" / "patient_bcse.json"
    bundle = json.loads(p.read_text())
    return {"ok": True, "applicant_payload": BCS.map_fhir_bundle(bundle), "source": "demo"}

@app.post("/api/bcse/evaluate")
def bcse_evaluate(payload: dict):
    """
    Body: { "sex": "...", "birthDate": "YYYY-MM-DD", "last_mammogram": "YYYY-MM-DD" }
    """
    decision = BCS.evaluate(payload or {})
    return {"ok": True, "decision": decision}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """GET / renders Banterop V2 UI as default interface"""
    base = Path(__file__).resolve().parent
    banterop_dir = base / "web" / "experimental" / "banterop"

    if (banterop_dir / "index.html").exists():
        with open(banterop_dir / "index.html", 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    else:
        # Fallback to legacy UI if Banterop V2 not available
        if templates:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "UI_EXPERIMENTAL": UI_EXPERIMENTAL
            })
        else:
            return HTMLResponse("<h1>Multi-Agent Demo</h1><p>Templates not available in this environment</p>")

@app.get("/legacy", response_class=HTMLResponse)
async def legacy_ui(request: Request):
    """GET /legacy renders legacy index.html interface"""
    if templates:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "UI_EXPERIMENTAL": UI_EXPERIMENTAL
        })
    else:
        return HTMLResponse("<h1>Multi-Agent Demo</h1><p>Templates not available in this environment</p>")

@app.get("/experimental/banterop", response_class=HTMLResponse)
async def experimental_banterop(request: Request):
    """GET /experimental/banterop renders Banterop-style scenario UI"""
    base = Path(__file__).resolve().parent
    banterop_dir = base / "web" / "experimental" / "banterop"

    if (banterop_dir / "index.html").exists():
        with open(banterop_dir / "index.html", 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    else:
        return HTMLResponse("<h1>Experimental Banterop UI</h1><p>Frontend files not found</p>")

@app.get("/experimental/banterop/banterop.js")
async def experimental_banterop_js():
    """Serve banterop.js file"""
    base = Path(__file__).resolve().parent
    js_file = base / "web" / "experimental" / "banterop" / "banterop.js"

    if js_file.exists():
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, media_type="application/javascript")
    else:
        return Response("// banterop.js not found", media_type="application/javascript")

@app.get("/banterop.js")
async def banterop_js():
    """Serve banterop.js file from root for default UI"""
    base = Path(__file__).resolve().parent
    js_file = base / "web" / "experimental" / "banterop" / "banterop.js"

    if js_file.exists():
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, media_type="application/javascript")
    else:
        return Response("// banterop.js not found", media_type="application/javascript")

@app.get("/partner_connect", response_class=HTMLResponse)
async def partner_connect(request: Request):
    """Partner Connect UI"""
    if templates:
        return templates.TemplateResponse("partner_connect.html", {"request": request})
    else:
        return HTMLResponse("<h1>Partner Connect</h1><p>Templates not available in this environment</p>")

@app.get("/test_harness", response_class=HTMLResponse)
async def test_harness(request: Request):
    """Test Harness UI"""
    if templates:
        return templates.TemplateResponse("test_harness.html", {"request": request})
    else:
        return HTMLResponse("<h1>Test Harness</h1><p>Templates not available in this environment</p>")

@app.get("/artifacts/{task_id}/{name}")
async def download_artifact(task_id: str, name: str):
    """Download artifact by task_id and filename"""
    
    # First, check if artifacts exist in the conversation engine
    from app.engine import conversation_engine
    conv_state = conversation_engine.get_conversation_state(task_id)
    
    if conv_state and "artifacts" in conv_state and name in conv_state["artifacts"]:
        # Use real artifacts from conversation engine
        base64_content = conv_state["artifacts"][name]
        mime_type = "application/fhir+json" if name.endswith(".json") else "application/octet-stream"
        
        try:
            content = base64.b64decode(base64_content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid artifact data")
        
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{name}"'
            }
        )
    
    # Fall back to demo artifacts for testing
    if task_id not in demo_artifacts:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if name not in demo_artifacts[task_id]:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    artifact = demo_artifacts[task_id][name]
    
    # Decode base64 content
    try:
        content = base64.b64decode(artifact["bytes"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid artifact data")
    
    # Return file with correct mime type and download headers
    return Response(
        content=content,
        media_type=artifact["mimeType"],
        headers={
            "Content-Disposition": f'attachment; filename="{name}"'
        }
    )

# Global state for protocol management
current_protocol = "a2a"

@app.get("/api/current_protocol")
async def get_current_protocol():
    """Get the current active protocol"""
    return {"protocol": current_protocol}

@app.post("/api/protocol")
async def switch_protocol(request: Request):
    """Switch between A2A and MCP protocols"""
    global current_protocol
    data = await request.json()
    new_protocol = data.get('protocol')
    
    if new_protocol in ['a2a', 'mcp']:
        current_protocol = new_protocol
        return {"success": True, "protocol": current_protocol}
    else:
        raise HTTPException(status_code=400, detail="Invalid protocol")

@app.post("/api/start_conversation")
async def start_conversation(request: Request):
    """Start a new conversation between agents"""
    data = await request.json()
    scenario = data.get('scenario', 'eligibility_check')
    
    # Mock response for demonstration - in real implementation this would
    # interact with the conversation engine
    import uuid
    session_id = str(uuid.uuid4())
    
    if current_protocol == "a2a":
        initial_exchange = {
            "applicant_request": {"method": "initiate_eligibility_check", "id": "req-1"},
            "applicant_response": {"result": "Request submitted", "id": "req-1"},
            "admin_response": {"method": "process_application", "result": "Application received", "id": "req-2"}
        }
    else:
        initial_exchange = {
            "eligibility_call": {"tool": "eligibility_check", "parameters": {"scenario": scenario}},
            "applicant_response": {"result": "Eligibility check initiated"},
            "process_call": {"tool": "process_application", "parameters": {"data": "application_data"}},
            "admin_response": {"result": "Application processed successfully"}
        }
    
    return {
        "success": True,
        "result": {
            "session_id": session_id,
            "protocol": current_protocol,
            "initial_exchange": initial_exchange
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/proxy/agent-card")
async def proxy_agent_card(url: str):
    """Proxy endpoint to fetch external agent cards (CORS workaround)"""
    import httpx
    from urllib.parse import urlparse
    
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Ensure it's requesting an agent card
        if not url.endswith('/.well-known/agent-card.json'):
            # Remove any existing agent-card.json path to avoid duplication
            if '/.well-known/agent-card.json' in url:
                url = url.split('/.well-known/agent-card.json')[0]
            
            if url.endswith('/'):
                url = url.rstrip('/') + '/.well-known/agent-card.json'
            else:
                url = url + '/.well-known/agent-card.json'
                
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={
                'Accept': 'application/json',
                'User-Agent': 'AgentInterOp-Inspector/1.0'
            })
            
            if response.status_code == 200:
                try:
                    agent_card = response.json()
                    return {
                        "success": True,
                        "data": agent_card,
                        "url": url,
                        "status_code": response.status_code
                    }
                except Exception as e:
                    raise HTTPException(status_code=502, detail=f"Invalid JSON response: {str(e)}")
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.reason_phrase}",
                    "url": url,
                    "status_code": response.status_code
                }
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout - server took too long to respond")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Connection failed - unable to reach server")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

@app.post("/api/proxy/a2a-message")
async def proxy_a2a_message(request: Request):
    """Proxy endpoint to send A2A messages to external agents (CORS workaround)"""
    import httpx
    from urllib.parse import urlparse
    
    try:
        body = await request.json()
        target_url = body.get('target_url')
        message_payload = body.get('payload')
        
        if not target_url or not message_payload:
            raise HTTPException(status_code=400, detail="Missing target_url or payload")
        
        # Validate URL
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid target URL format")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                target_url,
                json=message_payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'AgentInterOp-Inspector/1.0'
                }
            )
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": response_data,
                "target_url": target_url
            }
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout - agent took too long to respond")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Connection failed - unable to reach agent")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

# Friendly guidance for partners
@app.post("/")
def root_post_hint():
    """Guidance for partners posting to root."""
    return {
        "ok": False, 
        "hint": "POST to /api/bridge/demo/a2a (canonical JSON-RPC) or /a2a (alias).",
        "endpoints": {
            "canonical": "/api/bridge/demo/a2a",
            "alias": "/a2a",
            "agent_card": "/.well-known/agent-card.json"
        }
    }

if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)