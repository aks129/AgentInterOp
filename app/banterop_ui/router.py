"""FastAPI router for Banterop-style scenario UI"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

from .scenario_models import RunConfig
from .scenario_loader import fetch_scenario, get_cached_scenarios, create_sample_bcs_scenario, create_clinical_informaticist_scenario
from .agentcard_loader import fetch_agent_card, get_cached_agent_cards, get_preset_agent_cards
from .mcp_fhir_bridge import fetch_patient_everything, extract_minimal_facts, get_configurable_codes
from .bcs_guidelines import (
    get_bcs_rules, update_bcs_rules, reset_bcs_rules, 
    evaluate_bcs_eligibility, generate_bcs_summary
)
from .a2a_proxy import proxy_a2a_message, create_message_send_payload, create_tasks_get_payload, create_tasks_resubscribe_payload
from .scenario_runner import (
    start_scenario_run, send_message_in_run, get_run_status,
    cancel_run, list_active_runs, cleanup_old_runs
)
from .claude_integration import (
    is_claude_available, synthesize_narrative, evaluate_guideline_rationale, complete_conversation
)
import asyncio

router = APIRouter(prefix="/api/experimental/banterop", tags=["banterop-ui"])


# Request/Response models

class ScenarioLoadRequest(BaseModel):
    url: str


class AgentCardLoadRequest(BaseModel):
    url: str


class FhirEverythingRequest(BaseModel):
    base: str
    patientId: str
    token: Optional[str] = None


class A2AProxyRequest(BaseModel):
    url: str
    rpc: Dict[str, Any]
    stream: bool = False


class RunSendRequest(BaseModel):
    runId: str
    parts: List[Dict[str, Any]]
    taskId: Optional[str] = None
    stream: bool = False


class RunCancelRequest(BaseModel):
    runId: str


class SmokeTestRequest(BaseModel):
    remoteA2aUrl: str
    scriptLength: int = 2


class BcsEvaluationRequest(BaseModel):
    patientFacts: Dict[str, Any]


class LlmCompleteRequest(BaseModel):
    messages: List[Dict[str, Any]]
    system_prompt: Optional[str] = None
    max_tokens: int = 500


class LlmNarrativeRequest(BaseModel):
    role: str  # "applicant" or "administrator"
    transcript: List[Dict[str, Any]]
    patient_facts: Optional[Dict[str, Any]] = None
    guidelines: Optional[Dict[str, Any]] = None


class LlmRationaleRequest(BaseModel):
    patient_facts: Dict[str, Any]
    evaluation: Dict[str, Any]
    guidelines: Dict[str, Any]


# Scenario endpoints

@router.post("/scenario/load")
async def load_scenario(request: ScenarioLoadRequest):
    """Load and parse scenario from URL"""
    try:
        scenario = await fetch_scenario(request.url)
        return {
            "success": True,
            "data": {
                "metadata": scenario.metadata,
                "agent_ids": scenario.get_agent_ids(),
                "agents": [{"agentId": agent.agentId, "name": agent.name, "role": agent.role} for agent in scenario.agents],
                "tools": len(scenario.tools) if scenario.tools else 0,
                "knowledgeBase": len(scenario.knowledgeBase) if scenario.knowledgeBase else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scenario/sample/bcs")
async def get_sample_bcs_scenario():
    """Get sample BCS scenario"""
    scenario = create_sample_bcs_scenario()
    return {
        "success": True,
        "data": scenario.dict()
    }


@router.get("/scenario/sample/clinical-informaticist")
async def get_clinical_informaticist_scenario():
    """Get Clinical Informaticist CQL Measure Development scenario"""
    scenario = create_clinical_informaticist_scenario()
    return {
        "success": True,
        "data": scenario.dict()
    }


@router.get("/scenario/presets")
async def get_scenario_presets():
    """Get all available scenario presets"""
    bcs_scenario = create_sample_bcs_scenario()
    cql_scenario = create_clinical_informaticist_scenario()

    return {
        "success": True,
        "data": {
            "presets": [
                {
                    "id": "sample-bcs",
                    "name": bcs_scenario.metadata.name,
                    "description": bcs_scenario.metadata.description,
                    "tags": bcs_scenario.metadata.tags,
                    "endpoint": "/scenario/sample/bcs"
                },
                {
                    "id": "clinical-informaticist",
                    "name": cql_scenario.metadata.name,
                    "description": cql_scenario.metadata.description,
                    "tags": cql_scenario.metadata.tags,
                    "endpoint": "/scenario/sample/clinical-informaticist",
                    "a2a_endpoint": "/api/bridge/cql-measure/a2a"
                }
            ]
        }
    }


@router.get("/scenario/cached")
async def get_cached_scenarios_list():
    """Get list of cached scenarios"""
    cached = get_cached_scenarios()
    return {
        "success": True,
        "data": {
            "count": len(cached),
            "scenarios": [
                {
                    "url": url,
                    "metadata": scenario.metadata.dict(),
                    "agent_count": len(scenario.agents)
                }
                for url, scenario in cached.items()
            ]
        }
    }


# Agent Card endpoints

@router.post("/agentcard/load")
async def load_agent_card(request: AgentCardLoadRequest):
    """Load and parse agent card from URL"""
    try:
        result = await fetch_agent_card(request.url)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agentcard/presets")
async def get_agent_card_presets():
    """Get preset agent card URLs"""
    return {
        "success": True,
        "data": get_preset_agent_cards()
    }


@router.get("/agentcard/cached")
async def get_cached_agent_cards_list():
    """Get list of cached agent cards"""
    cached = get_cached_agent_cards()
    return {
        "success": True,
        "data": {
            "count": len(cached),
            "cards": [
                {
                    "url": url,
                    "name": info["details"]["name"],
                    "a2a_url": info["url"],
                    "transport": info["details"]["preferredTransport"]
                }
                for url, info in cached.items()
            ]
        }
    }


# FHIR endpoints

@router.post("/fhir/everything")
async def fetch_fhir_everything(request: FhirEverythingRequest):
    """Fetch patient $everything bundle and extract minimal facts"""
    try:
        bundle = await fetch_patient_everything(request.base, request.patientId, request.token)
        facts = extract_minimal_facts(bundle)
        
        return {
            "success": True,
            "data": {
                "bundle": bundle,
                "facts": facts
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/fhir/codes")
async def get_fhir_codes():
    """Get configurable FHIR codes"""
    return {
        "success": True,
        "data": get_configurable_codes()
    }


# BCS endpoints

@router.get("/bcs/rules")
async def get_bcs_rules_endpoint():
    """Get current BCS evaluation rules"""
    return {
        "success": True,
        "data": get_bcs_rules()
    }


@router.post("/bcs/rules")
async def update_bcs_rules_endpoint(rules: Dict[str, Any]):
    """Update BCS evaluation rules"""
    try:
        updated_rules = update_bcs_rules(rules)
        return {
            "success": True,
            "data": updated_rules
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bcs/rules/reset")
async def reset_bcs_rules_endpoint():
    """Reset BCS rules to defaults"""
    reset_bcs_rules()
    return {
        "success": True,
        "data": get_bcs_rules()
    }


@router.post("/bcs/evaluate")
async def evaluate_bcs(request: BcsEvaluationRequest):
    """Evaluate BCS eligibility"""
    try:
        evaluation = evaluate_bcs_eligibility(request.patientFacts)
        summary = generate_bcs_summary(evaluation, request.patientFacts)
        
        return {
            "success": True,
            "data": {
                "evaluation": evaluation,
                "summary": summary
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# A2A Proxy endpoints

@router.post("/a2a/proxy")
async def proxy_a2a_endpoint(request: A2AProxyRequest):
    """Proxy A2A message to remote endpoint"""
    try:
        if request.stream:
            # Return streaming response
            return await proxy_a2a_message(request.url, request.rpc, stream=True)
        else:
            # Return regular response
            result = await proxy_a2a_message(request.url, request.rpc, stream=False)
            return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Scenario Run endpoints

@router.post("/run/start")
async def start_run(config: RunConfig):
    """Start a new scenario run"""
    try:
        run_id = await start_scenario_run(config)
        return {
            "success": True,
            "data": {
                "runId": run_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/run/send")
async def send_run_message(request: RunSendRequest):
    """Send message in scenario run"""
    try:
        if request.stream:
            # For streaming, we'd need to modify the implementation
            # For now, fall back to regular send
            pass
        
        result = await send_message_in_run(
            request.runId, 
            request.parts, 
            request.taskId, 
            request.stream
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run/status")
async def get_run_status_endpoint(runId: str):
    """Get run status and transcript"""
    context = get_run_status(runId)
    if not context:
        raise HTTPException(status_code=404, detail=f"Run {runId} not found")
    
    return {
        "success": True,
        "data": context.dict()
    }


@router.post("/run/cancel")
async def cancel_run_endpoint(request: RunCancelRequest):
    """Cancel a scenario run"""
    success = cancel_run(request.runId)
    if not success:
        raise HTTPException(status_code=404, detail=f"Run {request.runId} not found")
    
    return {
        "success": True,
        "data": {
            "runId": request.runId,
            "status": "cancelled"
        }
    }


@router.get("/run/list")
async def list_runs():
    """List active runs"""
    runs = list_active_runs()
    return {
        "success": True,
        "data": {
            "count": len(runs),
            "runs": runs
        }
    }


# Test endpoints

@router.post("/test/smoke")
async def run_smoke_test(request: SmokeTestRequest):
    """Run smoke test against remote A2A endpoint"""
    try:
        test_messages = [
            [{"kind": "text", "text": "Hello, can you help me with eligibility screening?"}],
            [{"kind": "text", "text": "I am a 55-year-old female."}],
        ]
        
        if request.scriptLength > 2:
            test_messages.append([{"kind": "text", "text": "When was my last mammogram?"}])
        
        results = []
        task_id = None
        
        for i, message_parts in enumerate(test_messages[:request.scriptLength]):
            try:
                payload = create_message_send_payload(message_parts, task_id)
                result = await proxy_a2a_message(request.remoteA2aUrl, payload)
                
                # Extract task ID for follow-up messages
                if result.get("success") and result.get("data", {}).get("result", {}).get("taskId"):
                    task_id = result["data"]["result"]["taskId"]
                
                results.append({
                    "step": i + 1,
                    "message": message_parts,
                    "success": result.get("success", False),
                    "response": result.get("data"),
                    "timestamp": result.get("timestamp")
                })
                
                # Small delay between messages
                if i < len(test_messages) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                results.append({
                    "step": i + 1,
                    "message": message_parts,
                    "success": False,
                    "error": str(e)
                })
                break
        
        # Determine overall pass/fail
        all_successful = all(result.get("success", False) for result in results)
        
        return {
            "success": True,
            "data": {
                "passed": all_successful,
                "remote_url": request.remoteA2aUrl,
                "script_length": request.scriptLength,
                "results": results,
                "summary": f"{'PASS' if all_successful else 'FAIL'} - {len([r for r in results if r.get('success')])}/{len(results)} messages successful"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# LLM/Claude endpoints

@router.get("/llm/status")
async def get_llm_status():
    """Check if Claude integration is available"""
    return {
        "success": True,
        "data": {
            "enabled": is_claude_available(),
            "model": "claude-3-haiku-20240307" if is_claude_available() else None
        }
    }


@router.post("/llm/complete")
async def llm_complete(request: LlmCompleteRequest):
    """General Claude completion endpoint"""
    result = complete_conversation(
        request.messages,
        request.system_prompt,
        request.max_tokens
    )

    if result.get("disabled"):
        return {
            "success": False,
            "disabled": True,
            "message": result.get("message")
        }

    return {
        "success": result.get("success", False),
        "data": result
    }


@router.post("/llm/narrative")
async def llm_narrative(request: LlmNarrativeRequest):
    """Generate narrative summary from transcript"""
    if request.role not in ["applicant", "administrator"]:
        raise HTTPException(status_code=400, detail="Role must be 'applicant' or 'administrator'")

    result = synthesize_narrative(
        request.role,
        request.transcript,
        request.patient_facts,
        request.guidelines
    )

    if result.get("disabled"):
        return {
            "success": False,
            "disabled": True,
            "message": result.get("message")
        }

    return {
        "success": result.get("success", False),
        "data": result
    }


@router.post("/llm/rationale")
async def llm_rationale(request: LlmRationaleRequest):
    """Generate guideline evaluation rationale"""
    result = evaluate_guideline_rationale(
        request.patient_facts,
        request.evaluation,
        request.guidelines
    )

    if result.get("disabled"):
        return {
            "success": False,
            "disabled": True,
            "message": result.get("message")
        }

    return {
        "success": result.get("success", False),
        "data": result
    }


# Utility endpoints

@router.post("/cleanup")
async def cleanup_runs(maxAgeHours: int = 24):
    """Clean up old run contexts"""
    cleanup_old_runs(maxAgeHours)
    return {
        "success": True,
        "data": {
            "message": f"Cleaned up runs older than {maxAgeHours} hours"
        }
    }