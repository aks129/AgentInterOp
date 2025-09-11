"""
FastAPI router for experimental v2 autonomous BCS system.
"""
import json
import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .fhir_mapper import fetch_patient_everything, extract_minimal_facts, validate_minimal_facts, create_demo_facts, create_test_cases
from .guidelines import GuidelinesEvaluator, DEFAULT_BCS_GUIDELINES, evaluate_test_cases
from .autonomy import AutonomousDialog, DialogConfig
from .arbiter import DialogArbiter, arbitrate_test_cases


router = APIRouter(prefix="/api/experimental/v2", tags=["experimental-v2"])

# In-memory storage for active dialogs (production would use Redis/DB)
active_dialogs: Dict[str, AutonomousDialog] = {}

# Guidelines storage (production would use proper persistence)
guidelines_storage = {
    "default": DEFAULT_BCS_GUIDELINES.copy()
}


class FHIRRequest(BaseModel):
    patientId: str
    fhir_base_url: Optional[str] = None
    bearer_token: Optional[str] = None
    mammogram_codes: Optional[List[Dict[str, str]]] = None


class AutonomyRequest(BaseModel):
    scenario: str = "bcse"
    facts: Dict[str, Any]
    a2a: Optional[Dict[str, str]] = None
    options: Optional[Dict[str, Any]] = None
    guidelines: Optional[Dict[str, Any]] = None
    api_key: Optional[str] = None


# === FHIR Endpoints ===

@router.post("/fhir/everything")
async def fetch_fhir_everything(request: FHIRRequest = Body(...)):
    """
    Fetch patient $everything bundle and extract minimal facts.
    
    Args:
        request: FHIR request with patient ID and server details
        
    Returns:
        Minimal facts extracted from FHIR bundle
    """
    try:
        # Use default FHIR server if not specified
        fhir_base_url = request.fhir_base_url or "https://hapi.fhir.org/baseR4"
        
        # Fetch $everything bundle
        bundle = await fetch_patient_everything(
            fhir_base_url=fhir_base_url,
            patient_id=request.patientId,
            bearer_token=request.bearer_token
        )
        
        # Extract minimal facts
        facts = extract_minimal_facts(
            fhir_bundle=bundle,
            mammogram_codes=request.mammogram_codes
        )
        
        # Validate facts
        validation = validate_minimal_facts(facts)
        
        return {
            "ok": True,
            "facts": facts,
            "validation": validation,
            "fhir_server": fhir_base_url,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"FHIR processing failed: {str(e)}")


@router.get("/fhir/demo-facts")
async def get_demo_facts():
    """Get demo minimal facts for testing."""
    return {
        "ok": True,
        "facts": create_demo_facts(),
        "test_cases": create_test_cases()
    }


# === Guidelines Endpoints ===

@router.get("/guidelines/bcse")
async def get_bcs_guidelines(version: str = "default"):
    """Get BCS guidelines configuration."""
    if version not in guidelines_storage:
        raise HTTPException(status_code=404, detail=f"Guidelines version '{version}' not found")
    
    return {
        "ok": True,
        "guidelines": guidelines_storage[version],
        "version": version,
        "available_versions": list(guidelines_storage.keys())
    }


@router.post("/guidelines/bcse")
async def update_bcs_guidelines(
    guidelines: Dict[str, Any] = Body(...),
    version: str = "default",
    api_key: Optional[str] = None
):
    """Update BCS guidelines configuration."""
    try:
        # Validate guidelines
        evaluator = GuidelinesEvaluator()
        evaluator.update_guidelines(guidelines)
        
        # Store guidelines
        guidelines_storage[version] = guidelines.copy()
        
        # Test guidelines with sample cases
        test_results = evaluate_test_cases(guidelines)
        
        return {
            "ok": True,
            "message": f"Guidelines updated for version '{version}'",
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid guidelines: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update guidelines: {str(e)}")


@router.get("/guidelines/test")
async def test_guidelines(version: str = "default"):
    """Test guidelines with standard test cases."""
    if version not in guidelines_storage:
        raise HTTPException(status_code=404, detail=f"Guidelines version '{version}' not found")
    
    guidelines = guidelines_storage[version]
    test_results = evaluate_test_cases(guidelines)
    
    return {
        "ok": True,
        "guidelines_version": version,
        "test_results": test_results,
        "passed": sum(1 for r in test_results if r["passed"]),
        "total": len(test_results)
    }


# === Autonomy Endpoints ===

@router.post("/autonomy/run")
async def start_autonomous_run(request: AutonomyRequest = Body(...)):
    """
    Start an autonomous two-agent dialog.
    
    Args:
        request: Autonomy configuration
        
    Returns:
        Run ID and initial status
    """
    try:
        # Use default guidelines if not provided
        guidelines = request.guidelines or guidelines_storage.get("default", DEFAULT_BCS_GUIDELINES)
        
        # Create dialog configuration
        config = DialogConfig(
            scenario=request.scenario,
            facts=request.facts,
            a2a=request.a2a or {},
            options=request.options or {},
            guidelines=guidelines,
            api_key=request.api_key
        )
        
        # Create and store dialog
        dialog = AutonomousDialog(config)
        active_dialogs[dialog.run_id] = dialog
        
        # Start dialog in background if not dry run
        if not config.options.get("dry_run", False):
            # For demo purposes, we'll run synchronously with SSE
            pass
        
        return {
            "ok": True,
            "run_id": dialog.run_id,
            "started": True,
            "config": {
                "scenario": config.scenario,
                "max_turns": dialog.max_turns,
                "dry_run": dialog.dry_run,
                "has_facts": bool(config.facts),
                "has_guidelines": bool(config.guidelines)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start autonomous run: {str(e)}")


@router.get("/autonomy/run/{run_id}/stream")
async def stream_autonomous_run(run_id: str):
    """
    Stream autonomous dialog progress via SSE.
    
    Args:
        run_id: Dialog run ID
        
    Returns:
        Server-sent events stream
    """
    if run_id not in active_dialogs:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found")
    
    dialog = active_dialogs[run_id]
    
    async def event_stream():
        try:
            async for frame in dialog.run():
                yield f"data: {json.dumps(frame)}\n\n"
        except Exception as e:
            error_frame = {
                "type": "error",
                "run_id": run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_frame)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/autonomy/status")
async def get_autonomy_status(run_id: str):
    """Get current status of autonomous dialog."""
    if run_id not in active_dialogs:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found")
    
    dialog = active_dialogs[run_id]
    status = dialog.get_status()
    
    return {
        "ok": True,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/autonomy/cancel")
async def cancel_autonomous_run(run_id: str = Body(..., embed=True)):
    """Cancel autonomous dialog."""
    if run_id not in active_dialogs:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found")
    
    dialog = active_dialogs[run_id]
    dialog.cancel()
    
    return {
        "ok": True,
        "message": f"Run '{run_id}' cancelled",
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/autonomy/cleanup")
async def cleanup_dialogs():
    """Clean up completed/cancelled dialogs."""
    before_count = len(active_dialogs)
    
    # Remove completed, cancelled, or error dialogs older than 1 hour
    current_time = datetime.now()
    to_remove = []
    
    for run_id, dialog in active_dialogs.items():
        dialog_age = (current_time - dialog.start_time).total_seconds()
        if (dialog_age > 3600 or  # 1 hour old
            dialog.state.value in ["completed", "cancelled", "error"]):
            to_remove.append(run_id)
    
    for run_id in to_remove:
        del active_dialogs[run_id]
    
    return {
        "ok": True,
        "message": f"Cleaned up {len(to_remove)} dialogs",
        "before": before_count,
        "after": len(active_dialogs),
        "active_dialogs": list(active_dialogs.keys())
    }


# === Testing Endpoints ===

@router.get("/test/arbiter")
async def test_arbiter():
    """Test arbiter with sample scenarios."""
    try:
        test_results = arbitrate_test_cases()
        return {
            "ok": True,
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arbiter test failed: {str(e)}")


@router.post("/test/quick-run")
async def quick_test_run(
    test_case: str = "eligible",
    dry_run: bool = True,
    api_key: Optional[str] = None
):
    """
    Run a quick test case through the autonomous system.
    
    Args:
        test_case: "eligible", "needs-info", or "ineligible"
        dry_run: Whether to run in dry-run mode
        api_key: Optional API key for Claude calls
        
    Returns:
        Complete test run results
    """
    # Get test case facts
    test_cases = create_test_cases()
    case_map = {case["name"].split("-")[0].lower(): case for case in test_cases}
    
    if test_case not in case_map:
        raise HTTPException(status_code=400, detail=f"Invalid test case: {test_case}")
    
    selected_case = case_map[test_case]
    
    try:
        # Create dialog configuration
        config = DialogConfig(
            scenario="bcse",
            facts=selected_case["facts"],
            a2a={},
            options={"max_turns": 4, "dry_run": dry_run},
            guidelines=guidelines_storage.get("default", DEFAULT_BCS_GUIDELINES),
            api_key=api_key
        )
        
        # Run dialog
        dialog = AutonomousDialog(config)
        frames = []
        
        async for frame in dialog.run():
            frames.append(frame)
        
        # Get final status
        final_status = dialog.get_status()
        
        return {
            "ok": True,
            "test_case": selected_case["name"],
            "expected_outcome": selected_case["expected_outcome"],
            "actual_outcome": final_status.get("final_outcome", {}).get("chosen"),
            "passed": final_status.get("final_outcome", {}).get("chosen") == selected_case["expected_outcome"],
            "frames": frames,
            "final_status": final_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick test run failed: {str(e)}")


# === Health/Status Endpoints ===

@router.get("/health")
async def health_check():
    """Health check for v2 autonomous system."""
    return {
        "ok": True,
        "service": "experimental-v2-autonomous-bcs",
        "version": "1.0.0",
        "active_dialogs": len(active_dialogs),
        "guidelines_versions": list(guidelines_storage.keys()),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/info")
async def system_info():
    """Get system information and capabilities."""
    return {
        "ok": True,
        "capabilities": {
            "fhir_integration": True,
            "autonomous_dialogs": True,
            "guidelines_editor": True,
            "arbiter_decisions": True,
            "a2a_protocol": True,
            "claude_integration": True,
            "dry_run_mode": True
        },
        "endpoints": {
            "fhir": "/api/experimental/v2/fhir/everything",
            "guidelines": "/api/experimental/v2/guidelines/bcse",
            "autonomy": "/api/experimental/v2/autonomy/run",
            "stream": "/api/experimental/v2/autonomy/run/{run_id}/stream",
            "status": "/api/experimental/v2/autonomy/status",
            "test": "/api/experimental/v2/test/quick-run"
        },
        "default_options": {
            "max_turns": 8,
            "sse_timeout_ms": 8000,
            "poll_interval_ms": 1200
        },
        "timestamp": datetime.now().isoformat()
    }