"""
MCP server for AgentInterOp.

Exposes the four production healthcare agents (Colonoscopy Scheduler, BCSE
Eligibility, Smart Scheduling, Clinical Informaticist / CQL Measure Builder)
as standards-compliant MCP tools over Streamable HTTP transport.

Mounted at /mcp on the main FastAPI app — see app/main.py.

Each tool is a thin wrapper that POSTs `message/send` to the corresponding
A2A JSON-RPC endpoint inside the same process. This keeps protocol logic in
one place (the A2A routers) and lets MCP and A2A stay in lock-step.

Also implements Prompt Opinion's FHIR context extension
(https://docs.promptopinion.ai/fhir-context/mcp-fhir-context):
  - Advertises `ai.promptopinion/fhir-context` in the initialize response.
  - Captures X-FHIR-Server-URL / X-FHIR-Access-Token / X-Patient-ID headers
    on every tool call and forwards them as message metadata to the A2A
    backend, so agents can fetch FHIR data using the caller's auth.
"""

import json
import os
from contextvars import ContextVar
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "agentinterop",
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    # Bind to 0.0.0.0 so FastMCP doesn't auto-enable DNS-rebinding protection,
    # which rejects requests behind reverse proxies (Railway / Vercel) with 421.
    host="0.0.0.0",
)

# Prompt Opinion FHIR extension declaration. Sent on every initialize response.
# Scopes use SMART-on-FHIR v2 syntax: <context>/<Resource>.<rights>
PO_FHIR_EXTENSION: dict = {
    "ai.promptopinion/fhir-context": {
        "scopes": [
            {"name": "patient/Patient.rs", "required": True},
            {"name": "patient/Condition.rs"},
            {"name": "patient/Observation.rs"},
            {"name": "patient/Coverage.rs"},
            {"name": "patient/Procedure.rs"},
        ]
    }
}

# Captured from request headers on every MCP request.
_fhir_server_url: ContextVar[str] = ContextVar("fhir_server_url", default="")
_fhir_access_token: ContextVar[str] = ContextVar("fhir_access_token", default="")
_fhir_patient_id: ContextVar[str] = ContextVar("fhir_patient_id", default="")


def _fhir_context_meta() -> dict:
    """Snapshot of the active FHIR context, omitting empty fields."""
    return {
        k: v
        for k, v in {
            "serverUrl": _fhir_server_url.get(),
            "accessToken": _fhir_access_token.get(),
            "patientId": _fhir_patient_id.get(),
        }.items()
        if v
    }


def _internal_base() -> str:
    return os.getenv(
        "INTERNAL_API_BASE",
        f"http://127.0.0.1:{os.getenv('PORT', '8000')}",
    )


async def _a2a_send(
    endpoint: str,
    text: str,
    task_id: Optional[str] = None,
) -> dict:
    """POST a JSON-RPC `message/send` to an in-process A2A endpoint.

    Forwards Prompt Opinion FHIR context (server URL, access token, patient id)
    as `message.metadata.fhir` so downstream agents can call the caller's
    FHIR server with their auth.
    """
    message: dict[str, Any] = {
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
    }
    if task_id:
        message["taskId"] = task_id

    fhir = _fhir_context_meta()
    if fhir:
        message["metadata"] = {"fhir": fhir}

    body = {
        "jsonrpc": "2.0",
        "id": "mcp-1",
        "method": "message/send",
        "params": {"message": message},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{_internal_base()}{endpoint}", json=body)
        r.raise_for_status()
        data = r.json()

    if "error" in data:
        raise RuntimeError(f"A2A error: {data['error']}")

    result = data.get("result") or {}
    return {
        "task_id": result.get("id"),
        "status": (result.get("status") or {}).get("state"),
        "messages": result.get("history", []),
        "artifacts": result.get("artifacts", []),
    }


@mcp.tool()
async def colonoscopy_schedule(
    message: str,
    task_id: str = "",
) -> dict:
    """
    Drive the colonoscopy scheduling workflow: 40+ question intake form
    completion, insurance verification, appointment search and booking,
    and prep instruction delivery.

    Multi-turn. The first call returns a `task_id`; pass it back on every
    subsequent call to continue the same scheduling conversation.

    Args:
        message: Natural-language input from the patient or coordinator
            (e.g. "I need to schedule a colonoscopy, my doctor referred me",
            or an intake answer).
        task_id: Optional task id returned from a prior call.

    Returns:
        Dict with `task_id`, `status` (working / input-required / completed),
        `messages` (conversation history), and `artifacts` (booking records).
    """
    return await _a2a_send("/api/colonoscopy-scheduler/a2a", message, task_id)


@mcp.tool()
async def bcse_check_eligibility(
    message: str,
    task_id: str = "",
) -> dict:
    """
    Check breast cancer screening eligibility against USPSTF guidelines.

    Accepts free-text patient context or a FHIR Bundle, returns an eligibility
    determination with constitutional reasoning (cited rule, guideline
    version, exceptions).

    Args:
        message: Patient context — age, screening history, risk factors;
            or a JSON FHIR Bundle.
        task_id: Optional task id from a prior call to continue.

    Returns:
        Dict with `task_id`, `status`, `messages`, `artifacts`.
    """
    return await _a2a_send("/api/bridge/demo/a2a", message, task_id)


@mcp.tool()
async def smart_scheduling_search(
    message: str,
    task_id: str = "",
) -> dict:
    """
    Search healthcare providers and find available appointment slots via
    SMART Scheduling Links.

    Supports filtering by specialty, location, insurance, language, and
    visit type. Returns provider listings plus bookable slot details
    (booking deep-links and phone numbers).

    Args:
        message: Natural-language search request
            (e.g. "Find a gastroenterologist near 02115 who takes BCBS").
        task_id: Optional task id from a prior call.

    Returns:
        Dict with `task_id`, `status`, `messages`, `artifacts`
        (provider lists, slot objects).
    """
    return await _a2a_send("/api/smart-scheduler/a2a", message, task_id)


@mcp.tool()
async def build_cql_measure(
    message: str,
    task_id: str = "",
) -> dict:
    """
    Generate an executable Clinical Quality Language (CQL) measure from a
    natural-language description. Returns a `Library.cql` artifact, an
    optional CQF Measure resource, and a narrative.

    Args:
        message: Description of the measure to build
            (e.g. "Build breast cancer screening CQL measure per USPSTF",
            or paste a clinical guideline).
        task_id: Optional task id from a prior call.

    Returns:
        Dict with `task_id`, `status`, `messages`, and `artifacts`
        containing the generated CQL files.
    """
    return await _a2a_send("/api/clinical-informaticist/a2a", message, task_id)


def _patch_initialize_response(body: bytes) -> bytes:
    """Inject the Po FHIR extension into a JSON-RPC initialize response.

    Pass-through if the body is not a JSON object with a result that looks
    like an initialize result. Idempotent.
    """
    try:
        data = json.loads(body)
    except Exception:
        return body
    if not isinstance(data, dict):
        return body
    result = data.get("result")
    if not isinstance(result, dict):
        return body
    # Heuristic: initialize result has serverInfo + protocolVersion.
    if "serverInfo" not in result or "protocolVersion" not in result:
        return body
    caps = result.get("capabilities")
    if not isinstance(caps, dict):
        caps = {}
        result["capabilities"] = caps
    ext = caps.get("extensions")
    if not isinstance(ext, dict):
        ext = {}
        caps["extensions"] = ext
    ext.update(PO_FHIR_EXTENSION)
    return json.dumps(data).encode("utf-8")


def streamable_http_app_with_po_fhir():
    """Wrap FastMCP's streamable_http_app with Po FHIR support.

    Responsibilities:
      1. Capture X-FHIR-* request headers into contextvars so tools can
         forward them to A2A backends as message metadata.
      2. Buffer JSON responses and inject the Po FHIR extension into
         initialize responses so Po marks the server as FHIR-aware.
    """
    inner = mcp.streamable_http_app()

    async def app(scope, receive, send):
        if scope["type"] != "http":
            await inner(scope, receive, send)
            return

        # Capture FHIR headers into contextvars (case-insensitive lookup).
        header_map = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        tok_url = _fhir_server_url.set(header_map.get("x-fhir-server-url", ""))
        tok_tok = _fhir_access_token.set(header_map.get("x-fhir-access-token", ""))
        tok_pid = _fhir_patient_id.set(header_map.get("x-patient-id", ""))

        # Buffer the response so we can patch the initialize body.
        response_start: Optional[dict] = None
        body_chunks: list[bytes] = []
        finalized = False

        async def buffered_send(message):
            nonlocal response_start, finalized
            if message["type"] == "http.response.start":
                response_start = message
                return
            if message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    finalized = True
                    full = b"".join(body_chunks)
                    patched = _patch_initialize_response(full)
                    if response_start is not None:
                        # Rewrite content-length to match patched body.
                        new_headers = [
                            (k, v)
                            for k, v in response_start.get("headers", [])
                            if k.lower() != b"content-length"
                        ]
                        new_headers.append(
                            (b"content-length", str(len(patched)).encode())
                        )
                        await send({**response_start, "headers": new_headers})
                    await send(
                        {
                            "type": "http.response.body",
                            "body": patched,
                            "more_body": False,
                        }
                    )
                    return
            else:
                # Pass through any other message types (trailers, etc).
                await send(message)

        try:
            await inner(scope, receive, buffered_send)
            # Edge case: inner finished without flushing body.
            if response_start is not None and not finalized:
                await send(response_start)
                await send(
                    {"type": "http.response.body", "body": b"", "more_body": False}
                )
        finally:
            _fhir_server_url.reset(tok_url)
            _fhir_access_token.reset(tok_tok)
            _fhir_patient_id.reset(tok_pid)

    return app
