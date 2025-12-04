"""
Clinical Informaticist Agent Router

Exposes the Clinical Informaticist Agent capabilities via REST and A2A endpoints.
This demonstrates how specialized agents can be integrated into the platform.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import asyncio

from app.agents.clinical_informaticist import (
    ClinicalInformaticistAgent,
    create_clinical_informaticist_agent,
    BREAST_CANCER_SCREENING_GUIDELINES
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clinical-informaticist", tags=["Clinical Informaticist"])

# Default Medplum credentials (can be overridden via request)
DEFAULT_MEDPLUM_CLIENT_ID = "0a0fe17a-6013-4c65-a2ab-e8eecf328bbb"
DEFAULT_MEDPLUM_CLIENT_SECRET = "0f9286290fd9d27c07eeb2bb4e84c624ebf08b5be8a0dbdfda6c42f775e167cd"


class LearnGuidelinesRequest(BaseModel):
    guideline_type: str = "breast_cancer_screening"
    source: str = "USPSTF"


class BuildMeasureRequest(BaseModel):
    guideline_type: str = "breast_cancer_screening"
    source: str = "USPSTF"


class ValidateCQLRequest(BaseModel):
    cql: Optional[str] = None
    guideline_type: str = "breast_cancer_screening"


class PublishRequest(BaseModel):
    guideline_type: str = "breast_cancer_screening"
    medplum_client_id: Optional[str] = None
    medplum_client_secret: Optional[str] = None


class ExecuteWorkflowRequest(BaseModel):
    guideline_type: str = "breast_cancer_screening"
    publish_to_fhir: bool = False
    medplum_client_id: Optional[str] = None
    medplum_client_secret: Optional[str] = None


class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


# Global agent instance (can be replaced per-request with credentials)
_default_agent = None


def get_agent(client_id: str = None, client_secret: str = None) -> ClinicalInformaticistAgent:
    """Get or create an agent instance."""
    global _default_agent

    if client_id and client_secret:
        # Create new agent with provided credentials
        return create_clinical_informaticist_agent(client_id, client_secret)

    if _default_agent is None:
        _default_agent = create_clinical_informaticist_agent(
            DEFAULT_MEDPLUM_CLIENT_ID,
            DEFAULT_MEDPLUM_CLIENT_SECRET
        )

    return _default_agent


@router.get("/info")
async def get_agent_info():
    """Get information about the Clinical Informaticist Agent."""
    agent = get_agent()
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "domain": agent.domain,
        "capabilities": agent.get_capabilities(),
        "supported_guidelines": [
            {
                "type": "breast_cancer_screening",
                "name": BREAST_CANCER_SCREENING_GUIDELINES["name"],
                "source": BREAST_CANCER_SCREENING_GUIDELINES["source"],
                "cms_id": BREAST_CANCER_SCREENING_GUIDELINES["quality_measure"]["cms_id"]
            }
        ],
        "endpoints": {
            "info": "/api/clinical-informaticist/info",
            "guidelines": "/api/clinical-informaticist/guidelines",
            "learn": "/api/clinical-informaticist/learn",
            "build": "/api/clinical-informaticist/build",
            "validate": "/api/clinical-informaticist/validate",
            "publish": "/api/clinical-informaticist/publish",
            "workflow": "/api/clinical-informaticist/workflow",
            "a2a": "/api/clinical-informaticist/a2a"
        }
    }


@router.get("/guidelines")
async def get_available_guidelines():
    """Get available clinical guidelines."""
    return {
        "available_guidelines": [
            {
                "type": "breast_cancer_screening",
                "name": BREAST_CANCER_SCREENING_GUIDELINES["name"],
                "source": BREAST_CANCER_SCREENING_GUIDELINES["source"],
                "version": BREAST_CANCER_SCREENING_GUIDELINES["version"],
                "recommendations_count": len(BREAST_CANCER_SCREENING_GUIDELINES["recommendations"]),
                "quality_measure": BREAST_CANCER_SCREENING_GUIDELINES["quality_measure"]
            }
        ]
    }


@router.get("/guidelines/{guideline_type}")
async def get_guideline_details(guideline_type: str):
    """Get detailed information about a specific guideline."""
    if guideline_type == "breast_cancer_screening":
        return BREAST_CANCER_SCREENING_GUIDELINES
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Guideline type '{guideline_type}' not found. Available: breast_cancer_screening"
        )


@router.post("/learn")
async def learn_guidelines(request: LearnGuidelinesRequest):
    """Learn and internalize clinical guidelines."""
    agent = get_agent()
    result = agent.learn_guidelines({
        "type": request.guideline_type,
        "source": request.source
    })
    return result


@router.post("/build")
async def build_cql_measure(request: BuildMeasureRequest):
    """Build CQL measure from guidelines."""
    agent = get_agent()

    # First learn the guidelines
    learn_result = agent.learn_guidelines({
        "type": request.guideline_type,
        "source": request.source
    })

    if learn_result["status"] != "learned":
        raise HTTPException(
            status_code=400,
            detail=f"Failed to learn guidelines: {learn_result.get('message', 'Unknown error')}"
        )

    # Then build the measure
    build_result = agent.build_cql_measure({})

    # Include full artifacts
    result = build_result.copy()
    if hasattr(agent, '_current_cql'):
        result["cql_full"] = agent._current_cql
    if hasattr(agent, '_current_library'):
        result["library_resource"] = agent._current_library
    if hasattr(agent, '_current_measure'):
        result["measure_resource"] = agent._current_measure

    return result


@router.post("/validate")
async def validate_cql(request: ValidateCQLRequest):
    """Validate CQL syntax and semantics."""
    agent = get_agent()

    if request.cql:
        # Validate provided CQL
        from app.agents.clinical_informaticist import CQLBuilder
        validation_result = CQLBuilder.validate_cql(request.cql)
        return {
            "status": "validated" if validation_result["valid"] else "invalid",
            **validation_result
        }
    else:
        # Build and validate from guidelines
        agent.learn_guidelines({"type": request.guideline_type})
        agent.build_cql_measure({})
        return agent.validate_cql({})


@router.post("/publish")
async def publish_to_fhir(request: PublishRequest):
    """Publish validated CQL measure to FHIR server."""
    client_id = request.medplum_client_id or DEFAULT_MEDPLUM_CLIENT_ID
    client_secret = request.medplum_client_secret or DEFAULT_MEDPLUM_CLIENT_SECRET

    agent = get_agent(client_id, client_secret)

    # Run full workflow first
    agent.learn_guidelines({"type": request.guideline_type})
    agent.build_cql_measure({})
    validation = agent.validate_cql({})

    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"CQL validation failed: {validation['errors']}"
        )

    # Publish (async operation)
    result = await agent.publish_to_fhir({})
    return result


@router.post("/workflow")
async def execute_full_workflow(request: ExecuteWorkflowRequest):
    """Execute the complete CQL measure development workflow."""
    client_id = request.medplum_client_id or DEFAULT_MEDPLUM_CLIENT_ID
    client_secret = request.medplum_client_secret or DEFAULT_MEDPLUM_CLIENT_SECRET

    agent = get_agent(client_id, client_secret)

    # Execute workflow
    workflow_result = agent.execute_full_workflow({
        "guideline_type": request.guideline_type
    })

    # Optionally publish
    if request.publish_to_fhir and workflow_result["status"] == "ready_to_publish":
        publish_result = await agent.publish_to_fhir({})
        workflow_result["publish_result"] = publish_result

    return workflow_result


@router.get("/status")
async def get_workflow_status():
    """Get current workflow status."""
    agent = get_agent()
    return agent.get_workflow_status()


@router.post("/a2a")
async def a2a_endpoint(request: A2ARequest):
    """A2A JSON-RPC endpoint for the Clinical Informaticist Agent."""
    agent = get_agent()

    message = {
        "jsonrpc": request.jsonrpc,
        "method": request.method,
        "params": request.params or {},
        "id": request.id
    }

    result = agent.process_message(message, "a2a")
    return JSONResponse(content=result)


@router.post("/mcp/tools/{tool_name}")
async def mcp_tool_endpoint(tool_name: str, request: Request):
    """MCP tool endpoint for the Clinical Informaticist Agent."""
    agent = get_agent()

    try:
        body = await request.json()
    except:
        body = {}

    tool_call = {
        "type": "tool_call",
        "id": f"mcp-{tool_name}",
        "function": {
            "name": tool_name,
            "arguments": body if isinstance(body, str) else (body.get("arguments", "{}") if isinstance(body.get("arguments"), str) else "{}")
        }
    }

    # Handle arguments properly
    if isinstance(body, dict) and "arguments" not in body:
        import json
        tool_call["function"]["arguments"] = json.dumps(body)

    result = agent.process_message(tool_call, "mcp")
    return JSONResponse(content=result)


# Agent card endpoint
@router.get("/.well-known/agent-card.json")
async def get_agent_card(request: Request):
    """Get the A2A agent card for the Clinical Informaticist Agent."""
    base_url = str(request.base_url).rstrip("/")

    return {
        "protocolVersion": "0.2.9",
        "preferredTransport": "JSONRPC",
        "name": "Clinical Informaticist Agent",
        "description": "Specialized agent for building, validating, and publishing CQL quality measures from clinical guidelines",
        "url": f"{base_url}/api/clinical-informaticist/a2a",
        "capabilities": {
            "streaming": True,
            "protocols": ["A2A", "MCP"],
            "cql_generation": True,
            "fhir_publishing": True
        },
        "skills": [
            {
                "id": "cql_measure_development",
                "name": "CQL Measure Development",
                "description": "Build CQL quality measures from clinical guidelines",
                "tags": ["cql", "quality-measure", "fhir", "guidelines"],
                "discovery": {
                    "url": f"{base_url}/api/clinical-informaticist/a2a"
                }
            }
        ],
        "methods": [
            "learn_guidelines",
            "build_cql_measure",
            "validate_cql",
            "publish_to_fhir",
            "execute_full_workflow",
            "get_workflow_status"
        ],
        "supported_formats": [
            "application/fhir+json",
            "text/cql",
            "application/json"
        ]
    }
