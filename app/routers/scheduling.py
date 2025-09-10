from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.scheduling.config import (
    SchedulingConfig,
    get_scheduling_config,
    save_scheduling_config,
    update_scheduling_config
)
from app.scheduling.publisher import test_publishers, get_cache_stats
from app.scheduling.discovery import SlotQuery, discover_slots, choose_slot


router = APIRouter(prefix="/api/scheduling", tags=["scheduling"])


class SchedulingConfigUpdate(BaseModel):
    """Model for scheduling config updates."""
    publishers: Optional[List[str]] = None
    cache_ttl_seconds: Optional[int] = None
    default_specialty: Optional[str] = None
    default_radius_km: Optional[int] = None
    default_timezone: Optional[str] = None


class SlotChoiceRequest(BaseModel):
    """Model for slot selection."""
    slot_id: str
    publisher_url: str
    note: Optional[str] = None


@router.get("/config")
async def get_config() -> SchedulingConfig:
    """Get current scheduling configuration."""
    return get_scheduling_config()


@router.post("/config")
async def update_config(config_update: SchedulingConfigUpdate) -> SchedulingConfig:
    """Update scheduling configuration."""
    try:
        # Convert to dict, filtering out None values
        update_data = {
            k: v for k, v in config_update.model_dump().items() 
            if v is not None
        }
        
        updated_config = update_scheduling_config(update_data)
        return updated_config
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuration update failed: {str(e)}")


@router.post("/publishers/test")
async def test_publishers_endpoint() -> Dict[str, Any]:
    """Test all configured publishers and return their status."""
    try:
        results = await test_publishers()
        return {
            "success": True,
            "publishers": results,
            "tested_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publisher test failed: {str(e)}")


@router.get("/index/stats")
async def get_index_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    return get_cache_stats()


@router.post("/search")
async def search_slots(query: SlotQuery) -> Dict[str, Any]:
    """Search for available slots across configured publishers."""
    try:
        results = await discover_slots(query)
        return {
            "success": True,
            "searched_at": datetime.utcnow().isoformat(),
            **results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Slot search failed: {str(e)}")


@router.post("/choose")
async def choose_slot_endpoint(choice: SlotChoiceRequest) -> Dict[str, Any]:
    """Choose a specific slot and get booking information."""
    try:
        result = await choose_slot(
            slot_id=choice.slot_id,
            publisher_url=choice.publisher_url,
            note=choice.note
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Slot choice failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Slot choice failed: {str(e)}")


# Simulated booking endpoint for demo purposes
@router.get("/simulate")
async def simulate_booking(slotId: str, publisher: str) -> Dict[str, Any]:
    """Simulated booking page for slots without real booking links."""
    return {
        "message": "Simulated Booking Portal",
        "slot_id": slotId,
        "publisher": publisher,
        "instructions": "This is a demo simulation. In a real implementation, this would redirect to the provider's actual booking portal.",
        "next_steps": [
            "Verify patient information",
            "Select appointment type",
            "Confirm appointment details",
            "Complete scheduling"
        ]
    }