"""
Smart Scheduling Agent - Provider search and appointment booking using SMART Scheduling Links.

This agent integrates with the Smart Scheduling API to:
1. Search for healthcare providers by specialty, location, and availability
2. Find available appointment slots for providers
3. Retrieve booking links and phone numbers for appointment scheduling

Designed to work as an A2A skill callable by external agents (e.g., Claude agents via MCP).

API Reference: https://github.com/aks129/smartscheduling
"""

import httpx
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SearchStatus(str, Enum):
    """Status of the search/booking workflow"""
    IDLE = "idle"
    SEARCHING_PROVIDERS = "searching_providers"
    PROVIDERS_FOUND = "providers_found"
    CHECKING_AVAILABILITY = "checking_availability"
    SLOTS_FOUND = "slots_found"
    BOOKING_RETRIEVED = "booking_retrieved"
    ERROR = "error"


# Default Smart Scheduling API base URL
DEFAULT_API_BASE = os.getenv(
    "SMART_SCHEDULING_API_BASE",
    "https://smart-scheduling-links.vercel.app"
)


class SmartSchedulerAgent:
    """
    Smart Scheduling Agent for provider search and appointment booking.

    Uses the SMART Scheduling Links API aggregator to:
    - Search providers by specialty, location, insurance, languages
    - Find available appointment slots
    - Retrieve booking deep-links and phone numbers
    """

    def __init__(
        self,
        agent_id: str = "smart-scheduler",
        api_base: str = DEFAULT_API_BASE
    ):
        self.agent_id = agent_id
        self.name = "Smart Scheduling Agent"
        self.description = "Search healthcare providers and find available appointments"
        self.domain = "healthcare-scheduling"
        self.api_base = api_base.rstrip("/")

        # Current state
        self.state = {
            "status": SearchStatus.IDLE,
            "last_search": None,
            "providers": [],
            "selected_provider": None,
            "slots": [],
            "selected_slot": None,
            "booking_info": None,
            "error": None
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "api_base": self.api_base,
            "features": [
                "provider_search",
                "availability_lookup",
                "booking_retrieval",
                "multi_publisher_aggregation"
            ],
            "supported_filters": [
                "specialty",
                "location",
                "date_range",
                "languages",
                "insurance",
                "available_only"
            ]
        }

    async def search_providers(
        self,
        specialty: Optional[str] = None,
        location: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        languages: Optional[List[str]] = None,
        insurance: Optional[List[str]] = None,
        available_only: bool = True
    ) -> Dict[str, Any]:
        """
        Search for healthcare providers.

        Args:
            specialty: Medical specialty (e.g., "dermatology", "cardiology")
            location: Geographic location (e.g., "Boston", "New York")
            date_from: Start date for availability (YYYY-MM-DD)
            date_to: End date for availability (YYYY-MM-DD)
            languages: List of languages spoken
            insurance: List of accepted insurance plans
            available_only: Only return providers with available slots

        Returns:
            Dictionary with providers and search metadata
        """
        self.state["status"] = SearchStatus.SEARCHING_PROVIDERS
        self.state["error"] = None

        # Build search request
        search_params = {}
        if specialty:
            search_params["specialty"] = specialty
        if location:
            search_params["location"] = location
        if date_from:
            search_params["dateFrom"] = date_from
        if date_to:
            search_params["dateTo"] = date_to
        if languages:
            search_params["languages"] = languages
        if insurance:
            search_params["insurance"] = insurance
        if available_only:
            search_params["availableOnly"] = True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/api/search",
                    json=search_params,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    data = response.json()
                    providers = data if isinstance(data, list) else data.get("results", [])

                    self.state["providers"] = providers
                    self.state["last_search"] = search_params
                    self.state["status"] = SearchStatus.PROVIDERS_FOUND

                    return {
                        "success": True,
                        "count": len(providers),
                        "providers": providers,
                        "search_criteria": search_params,
                        "message": f"Found {len(providers)} provider(s) matching your criteria"
                    }
                else:
                    self.state["status"] = SearchStatus.ERROR
                    self.state["error"] = f"API error: {response.status_code}"
                    return {
                        "success": False,
                        "error": f"Search failed with status {response.status_code}",
                        "details": response.text
                    }

        except httpx.TimeoutException:
            self.state["status"] = SearchStatus.ERROR
            self.state["error"] = "Request timeout"
            return {
                "success": False,
                "error": "Search request timed out. Please try again."
            }
        except Exception as e:
            self.state["status"] = SearchStatus.ERROR
            self.state["error"] = str(e)
            return {
                "success": False,
                "error": f"Search failed: {str(e)}"
            }

    async def get_provider_availability(
        self,
        provider_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get available appointment slots for a specific provider.

        Args:
            provider_id: The provider's unique identifier
            date_from: Start date for availability (YYYY-MM-DD)
            date_to: End date for availability (YYYY-MM-DD)

        Returns:
            Dictionary with available slots
        """
        self.state["status"] = SearchStatus.CHECKING_AVAILABILITY
        self.state["error"] = None
        self.state["selected_provider"] = provider_id

        try:
            # Build URL with query params
            url = f"{self.api_base}/api/availability/{provider_id}"
            params = {}
            if date_from:
                params["dateFrom"] = date_from
            if date_to:
                params["dateTo"] = date_to

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    slots = data if isinstance(data, list) else data.get("slots", [])

                    # Filter to only available slots
                    available_slots = [
                        s for s in slots
                        if s.get("status") == "free" or s.get("available", True)
                    ]

                    self.state["slots"] = available_slots
                    self.state["status"] = SearchStatus.SLOTS_FOUND

                    # Format slots for display
                    formatted_slots = []
                    for slot in available_slots[:10]:  # Limit to 10
                        formatted_slots.append({
                            "id": slot.get("id"),
                            "start": slot.get("start"),
                            "end": slot.get("end"),
                            "status": slot.get("status", "free"),
                            "appointment_type": slot.get("appointmentType"),
                            "virtual": slot.get("virtual", False),
                            "display": self._format_slot_display(slot)
                        })

                    return {
                        "success": True,
                        "provider_id": provider_id,
                        "count": len(available_slots),
                        "slots": formatted_slots,
                        "message": f"Found {len(available_slots)} available slot(s)"
                    }
                else:
                    self.state["status"] = SearchStatus.ERROR
                    return {
                        "success": False,
                        "error": f"Failed to get availability: {response.status_code}"
                    }

        except Exception as e:
            self.state["status"] = SearchStatus.ERROR
            self.state["error"] = str(e)
            return {
                "success": False,
                "error": f"Availability check failed: {str(e)}"
            }

    async def get_booking_info(self, slot_id: str) -> Dict[str, Any]:
        """
        Get booking information for a specific slot.

        Returns the booking deep-link URL and/or phone number for scheduling.

        Args:
            slot_id: The slot's unique identifier

        Returns:
            Dictionary with booking URL and phone number
        """
        self.state["selected_slot"] = slot_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_base}/api/booking/{slot_id}"
                )

                if response.status_code == 200:
                    data = response.json()

                    self.state["booking_info"] = data
                    self.state["status"] = SearchStatus.BOOKING_RETRIEVED

                    return {
                        "success": True,
                        "slot_id": slot_id,
                        "booking_url": data.get("bookingUrl") or data.get("deepLink"),
                        "booking_phone": data.get("bookingPhone") or data.get("phone"),
                        "provider_name": data.get("providerName"),
                        "location": data.get("location"),
                        "appointment_details": data.get("appointmentDetails"),
                        "message": "Booking information retrieved. Use the URL or phone to complete scheduling."
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get booking info: {response.status_code}"
                    }

        except Exception as e:
            self.state["error"] = str(e)
            return {
                "success": False,
                "error": f"Booking retrieval failed: {str(e)}"
            }

    async def get_all_providers(self) -> Dict[str, Any]:
        """Get list of all available providers (practitioners)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_base}/api/practitioners")

                if response.status_code == 200:
                    data = response.json()
                    providers = data if isinstance(data, list) else data.get("practitioners", [])

                    return {
                        "success": True,
                        "count": len(providers),
                        "providers": providers
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get providers: {response.status_code}"
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_all_locations(self) -> Dict[str, Any]:
        """Get list of all available locations"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_base}/api/locations")

                if response.status_code == 200:
                    data = response.json()
                    locations = data if isinstance(data, list) else data.get("locations", [])

                    return {
                        "success": True,
                        "count": len(locations),
                        "locations": locations
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get locations: {response.status_code}"
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_all_slots(
        self,
        available_only: bool = True,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all available slots across all providers"""
        try:
            params = {}
            if available_only:
                params["status"] = "free"
            if date_from:
                params["dateFrom"] = date_from
            if date_to:
                params["dateTo"] = date_to

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_base}/api/slots",
                    params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    slots = data if isinstance(data, list) else data.get("slots", [])

                    return {
                        "success": True,
                        "count": len(slots),
                        "slots": slots
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get slots: {response.status_code}"
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_slot_display(self, slot: Dict[str, Any]) -> str:
        """Format a slot for human-readable display"""
        try:
            start = slot.get("start", "")
            if start:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                date_str = dt.strftime("%A, %B %d, %Y")
                time_str = dt.strftime("%I:%M %p")
                return f"{date_str} at {time_str}"
        except:
            pass
        return slot.get("start", "Unknown time")

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "status": self.state["status"].value,
            "providers_found": len(self.state["providers"]),
            "slots_found": len(self.state["slots"]),
            "selected_provider": self.state["selected_provider"],
            "selected_slot": self.state["selected_slot"],
            "has_booking_info": self.state["booking_info"] is not None,
            "error": self.state["error"]
        }

    def reset(self):
        """Reset agent state"""
        self.state = {
            "status": SearchStatus.IDLE,
            "last_search": None,
            "providers": [],
            "selected_provider": None,
            "slots": [],
            "selected_slot": None,
            "booking_info": None,
            "error": None
        }

    async def process_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a natural language message and route to appropriate action.

        Args:
            message: User's message
            context: Optional context with search parameters

        Returns:
            Response dictionary
        """
        message_lower = message.lower()

        # Extract context parameters
        ctx = context or {}

        # Route based on message intent
        if any(kw in message_lower for kw in ["search", "find", "look for", "provider", "doctor"]):
            # Extract specialty and location from message or context
            specialty = ctx.get("specialty")
            location = ctx.get("location")

            # Try to extract from message
            if "dermatolog" in message_lower:
                specialty = "dermatology"
            elif "cardio" in message_lower:
                specialty = "cardiology"
            elif "primary" in message_lower or "general" in message_lower:
                specialty = "primary care"

            # Extract location hints
            location_keywords = ["in", "near", "around"]
            for kw in location_keywords:
                if kw in message_lower:
                    parts = message_lower.split(kw)
                    if len(parts) > 1:
                        location = parts[1].strip().split()[0] if parts[1].strip() else None

            result = await self.search_providers(
                specialty=specialty or ctx.get("specialty"),
                location=location or ctx.get("location"),
                date_from=ctx.get("date_from"),
                date_to=ctx.get("date_to"),
                available_only=True
            )

            return {
                "action": "search_providers",
                "result": result,
                "message": result.get("message", "Search completed"),
                "providers": result.get("providers", [])[:5]  # Return top 5
            }

        elif any(kw in message_lower for kw in ["availability", "available", "slots", "appointment"]):
            provider_id = ctx.get("provider_id")

            if provider_id:
                result = await self.get_provider_availability(provider_id)
                return {
                    "action": "get_availability",
                    "result": result,
                    "message": result.get("message", "Availability check completed"),
                    "slots": result.get("slots", [])
                }
            else:
                return {
                    "action": "get_availability",
                    "error": "Please specify a provider ID to check availability",
                    "hint": "First search for providers, then select one to check availability"
                }

        elif any(kw in message_lower for kw in ["book", "schedule", "reserve"]):
            slot_id = ctx.get("slot_id")

            if slot_id:
                result = await self.get_booking_info(slot_id)
                return {
                    "action": "get_booking",
                    "result": result,
                    "message": result.get("message", "Booking info retrieved"),
                    "booking_url": result.get("booking_url"),
                    "booking_phone": result.get("booking_phone")
                }
            else:
                return {
                    "action": "get_booking",
                    "error": "Please specify a slot ID to get booking information",
                    "hint": "First check availability, then select a slot to book"
                }

        else:
            # Default: return capabilities and guidance
            return {
                "action": "help",
                "message": "I can help you find healthcare providers and schedule appointments.",
                "capabilities": self.get_capabilities(),
                "examples": [
                    "Search for dermatologists in Boston",
                    "Find available appointments for provider X",
                    "Get booking link for slot Y"
                ]
            }


def create_smart_scheduler_agent(api_base: Optional[str] = None) -> SmartSchedulerAgent:
    """Factory function to create a Smart Scheduler Agent"""
    return SmartSchedulerAgent(
        agent_id="smart-scheduler",
        api_base=api_base or DEFAULT_API_BASE
    )
