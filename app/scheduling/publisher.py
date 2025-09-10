import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
from pydantic import BaseModel

from app.scheduling.config import get_scheduling_config


class SchedulingIndex(BaseModel):
    """Indexed scheduling data for fast lookup."""
    locations: Dict[str, Dict[str, Any]] = {}
    organizations: Dict[str, Dict[str, Any]] = {}
    healthcare_services: Dict[str, Dict[str, Any]] = {}
    schedules: Dict[str, Dict[str, Any]] = {}
    slots: List[Dict[str, Any]] = []
    indexed_at: float
    source_url: str


# In-memory cache with TTL
_cache: Dict[str, SchedulingIndex] = {}


async def fetch_bulk_publish(base_url: str, timeout: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch bulk publish data from a SMART Scheduling Links publisher.
    
    Args:
        base_url: Base URL of the publisher
        timeout: Request timeout in seconds
        
    Returns:
        Dict with normalized resource arrays by resourceType
    """
    url = f"{base_url.rstrip('/')}/$bulk-publish"
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            url,
            headers={
                "Accept": "application/json, application/x-ndjson"
            }
        )
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "").lower()
        
        if "application/x-ndjson" in content_type or "application/ndjson" in content_type:
            # Parse NDJSON format
            resources_by_type = {}
            for line in response.text.strip().split('\n'):
                if line.strip():
                    resource = json.loads(line)
                    resource_type = resource.get("resourceType")
                    if resource_type:
                        if resource_type not in resources_by_type:
                            resources_by_type[resource_type] = []
                        resources_by_type[resource_type].append(resource)
            return resources_by_type
            
        elif "application/json" in content_type:
            # Parse JSON Bundle format
            data = response.json()
            resources_by_type = {}
            
            # Handle Bundle format
            if data.get("resourceType") == "Bundle" and "entry" in data:
                for entry in data["entry"]:
                    resource = entry.get("resource", {})
                    resource_type = resource.get("resourceType")
                    if resource_type:
                        if resource_type not in resources_by_type:
                            resources_by_type[resource_type] = []
                        resources_by_type[resource_type].append(resource)
            else:
                # Direct resource array format
                for resource_type in ["Location", "Organization", "HealthcareService", "Schedule", "Slot"]:
                    if resource_type in data:
                        resources_by_type[resource_type] = data[resource_type]
            
            return resources_by_type
        
        else:
            raise ValueError(f"Unsupported content type: {content_type}")


def build_index(bulk_data: Dict[str, List[Dict[str, Any]]], source_url: str) -> SchedulingIndex:
    """
    Build an indexed view of the bulk data for efficient searching.
    
    Args:
        bulk_data: Raw bulk publish data by resourceType
        source_url: Source URL for tracking
        
    Returns:
        SchedulingIndex with resolved references and derived fields
    """
    index = SchedulingIndex(
        indexed_at=time.time(),
        source_url=source_url
    )
    
    # Index base resources by ID
    for location in bulk_data.get("Location", []):
        if "id" in location:
            index.locations[location["id"]] = location
            
    for org in bulk_data.get("Organization", []):
        if "id" in org:
            index.organizations[org["id"]] = org
            
    for service in bulk_data.get("HealthcareService", []):
        if "id" in service:
            index.healthcare_services[service["id"]] = service
            
    for schedule in bulk_data.get("Schedule", []):
        if "id" in schedule:
            # Resolve actor references
            actor_refs = schedule.get("actor", [])
            resolved_actors = []
            for actor_ref in actor_refs:
                ref = actor_ref.get("reference", "")
                if ref.startswith("Location/"):
                    loc_id = ref.replace("Location/", "")
                    if loc_id in index.locations:
                        resolved_actors.append({
                            "type": "Location",
                            "resource": index.locations[loc_id]
                        })
                elif ref.startswith("HealthcareService/"):
                    svc_id = ref.replace("HealthcareService/", "")
                    if svc_id in index.healthcare_services:
                        resolved_actors.append({
                            "type": "HealthcareService", 
                            "resource": index.healthcare_services[svc_id]
                        })
            
            schedule["_resolved_actors"] = resolved_actors
            index.schedules[schedule["id"]] = schedule
    
    # Process slots with derived fields
    for slot in bulk_data.get("Slot", []):
        if "id" not in slot:
            continue
            
        # Resolve schedule reference
        schedule_ref = slot.get("schedule", {}).get("reference", "")
        resolved_schedule = None
        if schedule_ref.startswith("Schedule/"):
            schedule_id = schedule_ref.replace("Schedule/", "")
            resolved_schedule = index.schedules.get(schedule_id)
        
        # Build derived fields for search
        derived_slot = {
            **slot,
            "_resolved_schedule": resolved_schedule,
            "_service_types": [],
            "_org": None,
            "_location": None,
            "_booking_link": None
        }
        
        # Extract service types from schedule
        if resolved_schedule:
            service_types = resolved_schedule.get("serviceType", [])
            for st in service_types:
                if "coding" in st:
                    for coding in st["coding"]:
                        if "code" in coding:
                            derived_slot["_service_types"].append(coding["code"])
                        if "display" in coding:
                            derived_slot["_service_types"].append(coding["display"])
                if "text" in st:
                    derived_slot["_service_types"].append(st["text"])
            
            # Extract org and location from resolved actors
            for actor in resolved_schedule.get("_resolved_actors", []):
                if actor["type"] == "Location":
                    loc = actor["resource"]
                    derived_slot["_location"] = {
                        "name": loc.get("name", ""),
                        "address": _format_address(loc.get("address")),
                        "lat": _extract_lat(loc),
                        "lng": _extract_lng(loc)
                    }
                    # Try to get org from location
                    managing_org = loc.get("managingOrganization", {}).get("reference", "")
                    if managing_org.startswith("Organization/"):
                        org_id = managing_org.replace("Organization/", "")
                        if org_id in index.organizations:
                            derived_slot["_org"] = index.organizations[org_id].get("name", "")
                elif actor["type"] == "HealthcareService":
                    svc = actor["resource"]
                    # Get org from healthcare service
                    org_ref = svc.get("providedBy", {}).get("reference", "")
                    if org_ref.startswith("Organization/"):
                        org_id = org_ref.replace("Organization/", "")
                        if org_id in index.organizations:
                            derived_slot["_org"] = index.organizations[org_id].get("name", "")
        
        # Check for booking extension (SMART Scheduling Links deep-link)
        extensions = slot.get("extension", [])
        for ext in extensions:
            if ext.get("url") == "http://fhir-registry.smarthealthit.org/StructureDefinition/booking-deep-link":
                derived_slot["_booking_link"] = ext.get("valueUrl")
                break
        
        # Parse slot times
        start_str = slot.get("start")
        end_str = slot.get("end")
        if start_str:
            try:
                derived_slot["_start_dt"] = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except:
                pass
        if end_str:
            try:
                derived_slot["_end_dt"] = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except:
                pass
        
        index.slots.append(derived_slot)
    
    return index


def _format_address(address: Optional[Dict[str, Any]]) -> str:
    """Format a FHIR address into a display string."""
    if not address:
        return ""
    
    parts = []
    if "line" in address:
        parts.extend(address["line"])
    if "city" in address:
        parts.append(address["city"])
    if "state" in address:
        parts.append(address["state"])
    if "postalCode" in address:
        parts.append(address["postalCode"])
    
    return ", ".join(str(p) for p in parts if p)


def _extract_lat(location: Dict[str, Any]) -> Optional[float]:
    """Extract latitude from FHIR Location position."""
    position = location.get("position", {})
    return position.get("latitude")


def _extract_lng(location: Dict[str, Any]) -> Optional[float]:
    """Extract longitude from FHIR Location position."""
    position = location.get("position", {})
    return position.get("longitude")


async def get_cached_index(base_url: str) -> Optional[SchedulingIndex]:
    """Get cached index for a publisher URL, respecting TTL."""
    config = get_scheduling_config()
    
    if base_url in _cache:
        index = _cache[base_url]
        age = time.time() - index.indexed_at
        if age < config.cache_ttl_seconds:
            return index
        else:
            # Expired, remove from cache
            del _cache[base_url]
    
    return None


async def fetch_and_cache_index(base_url: str) -> SchedulingIndex:
    """Fetch publisher data and cache the built index."""
    # Check cache first
    cached = await get_cached_index(base_url)
    if cached:
        return cached
    
    # Fetch fresh data
    bulk_data = await fetch_bulk_publish(base_url)
    
    # Validate required resource types
    required_types = ["Location", "Organization", "HealthcareService", "Schedule", "Slot"]
    missing_types = [rt for rt in required_types if rt not in bulk_data or not bulk_data[rt]]
    if missing_types:
        raise ValueError(f"Publisher missing required resource types: {missing_types}")
    
    # Build and cache index
    index = build_index(bulk_data, base_url)
    _cache[base_url] = index
    
    return index


async def test_publishers() -> Dict[str, Any]:
    """Test all configured publishers and return status."""
    config = get_scheduling_config()
    results = {}
    
    for publisher_url in config.publishers:
        try:
            start_time = time.time()
            index = await fetch_and_cache_index(publisher_url)
            elapsed = time.time() - start_time
            
            results[publisher_url] = {
                "status": "success",
                "elapsed_ms": int(elapsed * 1000),
                "counts": {
                    "locations": len(index.locations),
                    "organizations": len(index.organizations),
                    "healthcare_services": len(index.healthcare_services),
                    "schedules": len(index.schedules),
                    "slots": len(index.slots)
                },
                "cache_age_seconds": int(time.time() - index.indexed_at)
            }
        except Exception as e:
            results[publisher_url] = {
                "status": "error",
                "error": str(e)
            }
    
    return results


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    config = get_scheduling_config()
    stats = {
        "cache_entries": len(_cache),
        "ttl_seconds": config.cache_ttl_seconds,
        "entries": {}
    }
    
    current_time = time.time()
    for url, index in _cache.items():
        age = current_time - index.indexed_at
        stats["entries"][url] = {
            "age_seconds": int(age),
            "expired": age >= config.cache_ttl_seconds,
            "slot_count": len(index.slots)
        }
    
    return stats