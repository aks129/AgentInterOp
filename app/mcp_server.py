"""
MCP server for AgentInterOp.

Exposes the four production healthcare agents (Colonoscopy Scheduler, BCSE
Eligibility, Smart Scheduling, Clinical Informaticist / CQL Measure Builder)
as standards-compliant MCP tools over Streamable HTTP transport.

Mounted at /mcp on the main FastAPI app — see app/main.py.

Each tool is a thin wrapper that POSTs `message/send` to the corresponding
A2A JSON-RPC endpoint inside the same process. This keeps protocol logic in
one place (the A2A routers) and lets MCP and A2A stay in lock-step.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "agentinterop",
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)


def _internal_base() -> str:
    return os.getenv(
        "INTERNAL_API_BASE",
        f"http://127.0.0.1:{os.getenv('PORT', '8000')}",
    )


async def _a2a_send(
    endpoint: str,
    text: str,
    task_id: Optional[str] = None,
) -> dict[str, Any]:
    """POST a JSON-RPC `message/send` to an in-process A2A endpoint."""
    message: dict[str, Any] = {
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
    }
    if task_id:
        message["taskId"] = task_id

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
    return await _a2a_send(
        "/api/colonoscopy-scheduler/a2a", message, task_id
    )


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
    return await _a2a_send(
        "/api/clinical-informaticist/a2a", message, task_id
    )
