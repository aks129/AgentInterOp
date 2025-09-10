import math
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.scheduling.config import get_scheduling_config
from app.scheduling.publisher import get_cached_index, fetch_and_cache_index


class SlotQuery(BaseModel):
    """Query parameters for slot discovery."""
    specialty: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_km: Optional[int] = None
    org: Optional[str] = None
    location_text: Optional[str] = None
    tz: Optional[str] = None
    limit: int = 50
    publishers: Optional[List[str]] = None


class SlotResult(BaseModel):
    """Result DTO for a discovered slot."""
    slot_id: str
    start: str
    end: str
    org: str
    service: str
    location: Dict[str, Any]
    booking_link: Optional[str] = None
    distance_km: Optional[float] = None
    source_publisher: str


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points using haversine formula."""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def matches_specialty(slot: Dict[str, Any], specialty: str) -> bool:
    """Check if slot matches specialty criteria."""
    if not specialty:
        return True
    
    specialty_lower = specialty.lower()
    
    # Check service types from resolved schedule
    service_types = slot.get("_service_types", [])
    for service_type in service_types:
        if specialty_lower in service_type.lower():
            return True
    
    # Check slot serviceCategory and serviceType
    categories = slot.get("serviceCategory", [])
    for category in categories:
        if "text" in category and specialty_lower in category["text"].lower():
            return True
        if "coding" in category:
            for coding in category["coding"]:
                if "display" in coding and specialty_lower in coding["display"].lower():
                    return True
    
    service_types_direct = slot.get("serviceType", [])
    for service_type in service_types_direct:
        if "text" in service_type and specialty_lower in service_type["text"].lower():
            return True
        if "coding" in service_type:
            for coding in service_type["coding"]:
                if "display" in coding and specialty_lower in coding["display"].lower():
                    return True
    
    return False


def matches_time_window(slot: Dict[str, Any], start: Optional[datetime], end: Optional[datetime]) -> bool:
    """Check if slot falls within time window."""
    slot_start = slot.get("_start_dt")
    slot_end = slot.get("_end_dt")
    
    if not slot_start:
        return True  # Can't filter without start time
    
    if start and slot_start < start:
        return False
    
    if end and slot_start > end:
        return False
    
    return True


def matches_location(slot: Dict[str, Any], lat: Optional[float], lng: Optional[float], 
                    radius_km: Optional[int], location_text: Optional[str]) -> tuple[bool, Optional[float]]:
    """Check if slot location matches criteria. Returns (matches, distance_km)."""
    location = slot.get("_location", {})
    
    # Text-based location filter
    if location_text:
        location_text_lower = location_text.lower()
        address = location.get("address", "").lower()
        name = location.get("name", "").lower()
        
        if location_text_lower not in address and location_text_lower not in name:
            return False, None
    
    # Geo-based filter
    distance_km = None
    if lat is not None and lng is not None:
        slot_lat = location.get("lat")
        slot_lng = location.get("lng")
        
        if slot_lat is not None and slot_lng is not None:
            distance_km = haversine_distance(lat, lng, slot_lat, slot_lng)
            
            if radius_km is not None and distance_km > radius_km:
                return False, distance_km
    
    return True, distance_km


def matches_org(slot: Dict[str, Any], org_filter: Optional[str]) -> bool:
    """Check if slot organization matches filter."""
    if not org_filter:
        return True
    
    org_name = slot.get("_org", "")
    return org_filter.lower() in org_name.lower()


async def discover_slots(query: SlotQuery) -> Dict[str, Any]:
    """
    Discover available slots across publishers based on query criteria.
    
    Returns:
        Dict with "slots" array and "source_counts" dict
    """
    config = get_scheduling_config()
    
    # Determine which publishers to search
    publishers_to_search = query.publishers or config.publishers
    if not publishers_to_search:
        return {"slots": [], "source_counts": {}}
    
    # Collect matching slots from all publishers
    all_slots = []
    source_counts = {}
    
    for publisher_url in publishers_to_search:
        try:
            # Get cached or fetch fresh index
            index = await get_cached_index(publisher_url)
            if not index:
                index = await fetch_and_cache_index(publisher_url)
            
            publisher_slots = []
            
            for slot in index.slots:
                # Apply filters
                if not matches_specialty(slot, query.specialty):
                    continue
                
                if not matches_time_window(slot, query.start, query.end):
                    continue
                
                location_matches, distance_km = matches_location(
                    slot, query.lat, query.lng, query.radius_km, query.location_text
                )
                if not location_matches:
                    continue
                
                if not matches_org(slot, query.org):
                    continue
                
                # Build result DTO
                slot_result = SlotResult(
                    slot_id=slot["id"],
                    start=slot.get("start", ""),
                    end=slot.get("end", ""),
                    org=slot.get("_org", ""),
                    service=", ".join(slot.get("_service_types", [])[:2]),  # First 2 service types
                    location={
                        "name": slot.get("_location", {}).get("name", ""),
                        "address": slot.get("_location", {}).get("address", ""),
                        "lat": slot.get("_location", {}).get("lat"),
                        "lng": slot.get("_location", {}).get("lng")
                    },
                    booking_link=slot.get("_booking_link"),
                    distance_km=distance_km,
                    source_publisher=publisher_url
                )
                
                publisher_slots.append(slot_result)
            
            all_slots.extend(publisher_slots)
            source_counts[publisher_url] = len(publisher_slots)
            
        except Exception as e:
            print(f"[WARN] Error searching publisher {publisher_url}: {e}")
            source_counts[publisher_url] = f"error: {str(e)}"
    
    # Sort results by ranking criteria
    # 1. Soonest start time
    # 2. Distance (if geo provided)  
    # 3. Organization name
    def sort_key(slot_result: SlotResult):
        start_time = datetime.fromisoformat(slot_result.start.replace("Z", "+00:00")) if slot_result.start else datetime.max
        distance = slot_result.distance_km if slot_result.distance_km is not None else float('inf')
        org_name = slot_result.org.lower()
        
        return (start_time, distance, org_name)
    
    all_slots.sort(key=sort_key)
    
    # Apply limit
    limited_slots = all_slots[:query.limit]
    
    # Convert to dict format for JSON response
    slots_data = [slot.model_dump() for slot in limited_slots]
    
    return {
        "slots": slots_data,
        "source_counts": source_counts
    }


async def choose_slot(slot_id: str, publisher_url: str, note: Optional[str] = None) -> Dict[str, Any]:
    """
    Record a slot choice and return booking information.
    
    Args:
        slot_id: ID of the chosen slot
        publisher_url: Publisher URL where slot was found
        note: Optional note for the choice
        
    Returns:
        Dict with booking_link, confirmation info, and trace data
    """
    try:
        # Find the slot in cached data
        index = await get_cached_index(publisher_url)
        if not index:
            index = await fetch_and_cache_index(publisher_url)
        
        chosen_slot = None
        for slot in index.slots:
            if slot["id"] == slot_id:
                chosen_slot = slot
                break
        
        if not chosen_slot:
            raise ValueError(f"Slot {slot_id} not found in publisher {publisher_url}")
        
        # Get booking link or generate simulated one
        booking_link = chosen_slot.get("_booking_link")
        is_simulation = False
        
        if not booking_link:
            # Generate simulated booking URL
            booking_link = f"/schedule/simulate?slotId={slot_id}&publisher={publisher_url}"
            is_simulation = True
        
        # Prepare trace data
        trace_data = {
            "slot_id": slot_id,
            "publisher_url": publisher_url,
            "slot_start": chosen_slot.get("start"),
            "slot_end": chosen_slot.get("end"),
            "org": chosen_slot.get("_org"),
            "location": chosen_slot.get("_location"),
            "booking_link": booking_link,
            "is_simulation": is_simulation,
            "note": note,
            "chosen_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "booking_link": booking_link,
            "is_simulation": is_simulation,
            "confirmation": f"Selected slot on {chosen_slot.get('start', 'unknown time')} at {chosen_slot.get('_org', 'unknown provider')}",
            "guidance": "Open the provider's portal to complete booking." if not is_simulation else "This is a simulated booking link for demo purposes.",
            "trace_data": trace_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "trace_data": {
                "slot_id": slot_id,
                "publisher_url": publisher_url,
                "error": str(e),
                "chosen_at": datetime.utcnow().isoformat()
            }
        }