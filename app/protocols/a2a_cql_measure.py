"""
A2A Bridge for Clinical Informaticist Agent - CQL Measure Development

This bridge endpoint enables agent-to-agent communication for the Clinical
Informaticist Agent, allowing external agents to:
1. Request CQL measure development from clinical guidelines
2. Validate CQL measures
3. Publish measures to FHIR servers (Medplum)

The workflow demonstrates multi-step agent interactions and tool usage.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime, timezone
import json
import time
import uuid
import asyncio
import base64
import logging

from app.agents.clinical_informaticist import (
    ClinicalInformaticistAgent,
    create_clinical_informaticist_agent,
    BREAST_CANCER_SCREENING_GUIDELINES
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge/cql-measure/a2a", tags=["A2A-CQL-Measure"])

# In-memory task storage for demo
_TASKS = {}

# Default Medplum credentials
DEFAULT_MEDPLUM_CLIENT_ID = "0a0fe17a-6013-4c65-a2ab-e8eecf328bbb"
DEFAULT_MEDPLUM_CLIENT_SECRET = "0f9286290fd9d27c07eeb2bb4e84c624ebf08b5be8a0dbdfda6c42f775e167cd"


def _task_snapshot(tid, state, history=None, artifacts=None, context=None):
    """Create an A2A task snapshot"""
    return {
        "id": tid,
        "contextId": tid,
        "status": {"state": state},
        "history": history or [],
        "artifacts": artifacts or [],
        "kind": "task",
        "metadata": context or {}
    }


def _ok(result, id_="1"):
    """Create JSON-RPC success response"""
    return JSONResponse({"jsonrpc": "2.0", "id": id_, "result": result})


def _err(id_, code, message, data=None):
    """Create JSON-RPC error response"""
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": id_,
        "error": {"code": code, "message": message, "data": data or {}}
    }, status_code=200)


def _create_file_artifact(name: str, content: str, mime_type: str = "application/json"):
    """Create A2A file artifact"""
    if isinstance(content, dict):
        content = json.dumps(content, indent=2)
    return {
        "kind": "file",
        "file": {
            "name": name,
            "mimeType": mime_type,
            "bytes": base64.b64encode(content.encode('utf-8')).decode('utf-8')
        }
    }


def _parse_request(text: str) -> dict:
    """Parse incoming request text to extract action and parameters"""
    # Try to parse as JSON first
    try:
        if "{" in text:
            return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Parse natural language request
    text_lower = text.lower()

    if "build" in text_lower or "create" in text_lower or "generate" in text_lower:
        return {"action": "build_measure", "guideline_type": "breast_cancer_screening"}
    elif "validate" in text_lower:
        return {"action": "validate"}
    elif "publish" in text_lower:
        return {"action": "publish"}
    elif "learn" in text_lower or "guidelines" in text_lower:
        return {"action": "learn_guidelines", "guideline_type": "breast_cancer_screening"}
    elif "workflow" in text_lower or "full" in text_lower or "execute" in text_lower:
        return {"action": "execute_full_workflow", "guideline_type": "breast_cancer_screening"}
    elif "status" in text_lower:
        return {"action": "get_status"}
    else:
        # Default: execute full workflow
        return {"action": "execute_full_workflow", "guideline_type": "breast_cancer_screening"}


async def _process_cql_request(request_params: dict, tid: str) -> tuple:
    """
    Process a CQL measure development request.
    Returns: (history_messages, artifacts, final_state)
    """
    action = request_params.get("action", "execute_full_workflow")
    guideline_type = request_params.get("guideline_type", "breast_cancer_screening")

    # Get credentials if provided
    medplum_client_id = request_params.get("medplum_client_id", DEFAULT_MEDPLUM_CLIENT_ID)
    medplum_client_secret = request_params.get("medplum_client_secret", DEFAULT_MEDPLUM_CLIENT_SECRET)

    # Create agent
    agent = create_clinical_informaticist_agent(medplum_client_id, medplum_client_secret)

    history = []
    artifacts = []
    final_state = "working"

    try:
        if action == "learn_guidelines":
            result = agent.learn_guidelines({"type": guideline_type})

            history.append({
                "role": "agent",
                "parts": [{
                    "kind": "text",
                    "text": f"Learned {result['guideline_name']} guidelines from {result['source']}. "
                           f"Found {result['recommendations_count']} recommendations. "
                           f"Quality measure: {result['quality_measure']['cms_id']} (NQF {result['quality_measure']['nqf_id']})"
                }],
                "kind": "message"
            })
            final_state = "input-required"  # Awaiting next action

        elif action == "build_measure":
            # Learn first
            learn_result = agent.learn_guidelines({"type": guideline_type})
            history.append({
                "role": "agent",
                "parts": [{"kind": "text", "text": f"Loaded {learn_result['guideline_name']} guidelines..."}],
                "kind": "message"
            })

            # Build measure
            build_result = agent.build_cql_measure({})

            history.append({
                "role": "agent",
                "parts": [{
                    "kind": "text",
                    "text": f"Built CQL measure: {build_result['library']['title']}. "
                           f"CQL length: {build_result['cql_length']} characters. "
                           f"CMS ID: {build_result['measure']['cms_id']}"
                }],
                "kind": "message"
            })

            # Add CQL as artifact
            if hasattr(agent, '_current_cql'):
                artifacts.append(_create_file_artifact(
                    "BreastCancerScreening.cql",
                    agent._current_cql,
                    "text/cql"
                ))

            final_state = "input-required"

        elif action == "validate":
            # Need full build first
            agent.learn_guidelines({"type": guideline_type})
            agent.build_cql_measure({})
            validate_result = agent.validate_cql({})

            if validate_result["valid"]:
                history.append({
                    "role": "agent",
                    "parts": [{
                        "kind": "text",
                        "text": f"CQL validation PASSED. No errors. "
                               f"{len(validate_result.get('info', []))} informational notes."
                    }],
                    "kind": "message"
                })
                final_state = "input-required"
            else:
                history.append({
                    "role": "agent",
                    "parts": [{
                        "kind": "text",
                        "text": f"CQL validation FAILED. Errors: {'; '.join(validate_result['errors'])}"
                    }],
                    "kind": "message"
                })
                final_state = "failed"

        elif action == "publish":
            # Full workflow with publish
            agent.learn_guidelines({"type": guideline_type})
            agent.build_cql_measure({})
            validate_result = agent.validate_cql({})

            if not validate_result["valid"]:
                history.append({
                    "role": "agent",
                    "parts": [{"kind": "text", "text": f"Cannot publish: CQL validation failed"}],
                    "kind": "message"
                })
                final_state = "failed"
            else:
                # Publish to Medplum
                publish_result = await agent.publish_to_fhir({})

                if publish_result["status"] == "published":
                    history.append({
                        "role": "agent",
                        "parts": [{
                            "kind": "text",
                            "text": f"Successfully published to {publish_result['fhir_server']}!\n"
                                   f"Library ID: {publish_result['library']['id']}\n"
                                   f"Measure ID: {publish_result['measure']['id']}"
                        }],
                        "kind": "message"
                    })

                    # Add artifacts
                    if hasattr(agent, '_current_library'):
                        artifacts.append(_create_file_artifact(
                            "Library-BreastCancerScreening.json",
                            agent._current_library,
                            "application/fhir+json"
                        ))
                    if hasattr(agent, '_current_measure'):
                        artifacts.append(_create_file_artifact(
                            "Measure-BreastCancerScreening.json",
                            agent._current_measure,
                            "application/fhir+json"
                        ))

                    final_state = "completed"
                else:
                    history.append({
                        "role": "agent",
                        "parts": [{"kind": "text", "text": f"Publish failed: {publish_result.get('message', 'Unknown error')}"}],
                        "kind": "message"
                    })
                    final_state = "failed"

        elif action == "execute_full_workflow":
            # Execute complete workflow
            workflow_result = agent.execute_full_workflow({"guideline_type": guideline_type})

            # Add step-by-step messages
            for step in workflow_result.get("steps", []):
                step_text = f"Step {step['step']}: {step['action']} - {step['status']}"
                history.append({
                    "role": "agent",
                    "parts": [{"kind": "text", "text": step_text}],
                    "kind": "message"
                })

            if workflow_result["status"] == "ready_to_publish":
                history.append({
                    "role": "agent",
                    "parts": [{
                        "kind": "text",
                        "text": "Workflow completed successfully! CQL measure is validated and ready to publish. "
                               "Send 'publish' to publish to Medplum FHIR server."
                    }],
                    "kind": "message"
                })

                # Add all artifacts
                artifacts_data = workflow_result.get("artifacts", {})
                if artifacts_data.get("cql"):
                    artifacts.append(_create_file_artifact(
                        "BreastCancerScreening.cql",
                        artifacts_data["cql"],
                        "text/cql"
                    ))
                if artifacts_data.get("library"):
                    artifacts.append(_create_file_artifact(
                        "Library-BreastCancerScreening.json",
                        artifacts_data["library"],
                        "application/fhir+json"
                    ))
                if artifacts_data.get("measure"):
                    artifacts.append(_create_file_artifact(
                        "Measure-BreastCancerScreening.json",
                        artifacts_data["measure"],
                        "application/fhir+json"
                    ))

                final_state = "input-required"  # Waiting for publish confirmation
            else:
                history.append({
                    "role": "agent",
                    "parts": [{
                        "kind": "text",
                        "text": f"Workflow failed at step {workflow_result.get('failed_at_step', 'unknown')}"
                    }],
                    "kind": "message"
                })
                final_state = "failed"

        elif action == "get_status":
            status = agent.get_workflow_status()
            history.append({
                "role": "agent",
                "parts": [{
                    "kind": "text",
                    "text": f"Agent: {status['agent']}\n"
                           f"Guidelines loaded: {status['guidelines_loaded']}\n"
                           f"Guideline: {status.get('guideline_name', 'None')}\n"
                           f"Medplum configured: {status['medplum_configured']}\n"
                           f"Workflow state: {json.dumps(status['workflow_state'], indent=2)}"
                }],
                "kind": "message"
            })
            final_state = "input-required"

        else:
            history.append({
                "role": "agent",
                "parts": [{
                    "kind": "text",
                    "text": f"Unknown action: {action}. Available actions: learn_guidelines, build_measure, "
                           f"validate, publish, execute_full_workflow, get_status"
                }],
                "kind": "message"
            })
            final_state = "input-required"

    except Exception as e:
        logger.error(f"CQL processing error: {e}")
        history.append({
            "role": "agent",
            "parts": [{"kind": "text", "text": f"Error processing request: {str(e)}"}],
            "kind": "message"
        })
        final_state = "failed"

    return history, artifacts, final_state


@router.post("")
async def rpc(req: Request):
    """Handle A2A JSON-RPC requests for CQL measure development"""
    body = await req.json()
    method = body.get("method")
    id_ = body.get("id", "1")
    params = body.get("params") or {}

    logger.info(f"CQL Measure A2A request: method={method}, id={id_}")

    if method == "message/send":
        # Extract message text from parts
        parts = (params.get("message") or {}).get("parts") or []
        text = next((p.get("text") for p in parts if p.get("kind") == "text"), "")

        # Create task ID
        tid = str(uuid.uuid4())[:8]

        # Parse request
        request_params = _parse_request(text)
        logger.info(f"Parsed request: {request_params}")

        # Add user message to history
        user_history = [{"role": "user", "parts": parts, "kind": "message"}]

        # Process request
        agent_history, artifacts, final_state = await _process_cql_request(request_params, tid)

        # Combine history
        full_history = user_history + agent_history

        # Create task snapshot
        snap = _task_snapshot(
            tid,
            final_state,
            history=full_history,
            artifacts=artifacts,
            context={
                "scenario": "cql_measure",
                "agent": "clinical_informaticist",
                "action": request_params.get("action"),
                "guideline_type": request_params.get("guideline_type")
            }
        )

        _TASKS[tid] = snap
        return _ok(snap, id_)

    elif method == "message/stream":
        # SSE streaming for CQL workflow
        def gen():
            tid = str(uuid.uuid4())[:8]

            # Initial working state
            snap = _task_snapshot(
                tid,
                "working",
                history=[{"role": "user", "parts": [], "kind": "message"}],
                context={"scenario": "cql_measure", "agent": "clinical_informaticist"}
            )
            _TASKS[tid] = snap

            yield f"data: {json.dumps({'jsonrpc': '2.0', 'id': 'sse', 'result': {'id': tid, 'status': {'state': 'working'}, 'kind': 'task'}})}\n\n"
            time.sleep(0.3)

            # Introduction message
            intro_msg = {
                "role": "agent",
                "parts": [{
                    "kind": "text",
                    "text": "Clinical Informaticist Agent ready for CQL measure development.\n\n"
                           "Available actions:\n"
                           "- 'learn guidelines' - Load breast cancer screening guidelines\n"
                           "- 'build measure' - Generate CQL and FHIR resources\n"
                           "- 'validate' - Validate CQL syntax\n"
                           "- 'publish' - Publish to Medplum FHIR server\n"
                           "- 'execute workflow' - Run full workflow\n\n"
                           "Send your request or just say 'build' to start."
                }],
                "kind": "message"
            }
            yield f"data: {json.dumps({'jsonrpc': '2.0', 'id': 'sse', 'result': intro_msg})}\n\n"
            time.sleep(0.3)

            # Set input-required state
            yield f"data: {json.dumps({'jsonrpc': '2.0', 'id': 'sse', 'result': {'kind': 'status-update', 'status': {'state': 'input-required'}, 'final': True}})}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    elif method == "tasks/get":
        tid = (params or {}).get("id")
        if not tid or tid not in _TASKS:
            return _err(id_, -32001, "Task not found")
        return _ok(_TASKS[tid], id_)

    elif method == "tasks/cancel":
        tid = (params or {}).get("id")
        if not tid or tid not in _TASKS:
            return _err(id_, -32001, "Task not found")
        snap = _TASKS[tid]
        snap["status"] = {"state": "canceled"}
        return _ok(snap, id_)

    elif method == "tasks/resubscribe":
        tid = (params or {}).get("id")
        if not tid or tid not in _TASKS:
            return _err(id_, -32001, "Task not found")
        return _ok(_TASKS[tid], id_)

    else:
        return _err(id_, -32601, "Method not found")


@router.get("/info")
async def get_bridge_info():
    """Get information about this A2A bridge"""
    return {
        "bridge": "cql-measure",
        "agent": "clinical_informaticist",
        "description": "A2A bridge for Clinical Informaticist Agent - CQL measure development",
        "supported_actions": [
            "learn_guidelines",
            "build_measure",
            "validate",
            "publish",
            "execute_full_workflow",
            "get_status"
        ],
        "guidelines": ["breast_cancer_screening"],
        "fhir_server": "Medplum (https://api.medplum.com)",
        "methods": ["message/send", "message/stream", "tasks/get", "tasks/cancel", "tasks/resubscribe"]
    }
