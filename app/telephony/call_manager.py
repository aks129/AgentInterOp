"""
Call Manager - Manages call lifecycle including origination and termination.

Handles:
- Outbound call origination via shim server
- Call tracking and status updates
- Agent instance management
- Call history and logging
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

import httpx

from .config import get_telephony_config, TelephonyConfig

logger = logging.getLogger(__name__)


@dataclass
class CallRecord:
    """Record of a completed or active call."""
    call_id: str
    direction: str  # "inbound" or "outbound"
    caller: str
    callee: str
    agent_id: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: List[Dict[str, Any]] = field(default_factory=list)
    intake_data: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[str] = None  # e.g., "scheduled", "callback_requested", "failed"
    notes: Optional[str] = None


class CallManager:
    """
    Manages call lifecycle and agent instance creation.

    Responsibilities:
    - Originate outbound calls via shim server
    - Track call status and metadata
    - Create agent instances for calls
    - Store call history
    """

    def __init__(self, config: Optional[TelephonyConfig] = None):
        """
        Initialize call manager.

        Args:
            config: Telephony configuration (loads from env if not provided)
        """
        self.config = config or get_telephony_config()
        self.call_history: Dict[str, CallRecord] = {}
        self._agent_factories: Dict[str, Callable] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    def register_agent(self, agent_id: str, factory: Callable):
        """
        Register an agent factory for creating agent instances.

        Args:
            agent_id: Identifier for the agent type
            factory: Callable that creates agent instances
        """
        self._agent_factories[agent_id] = factory
        logger.info(f"Registered agent factory: {agent_id}")

    def get_agent(self, agent_id: str):
        """
        Get or create an agent instance.

        Args:
            agent_id: Identifier for the agent type

        Returns:
            Agent instance
        """
        if agent_id not in self._agent_factories:
            # Try to dynamically import the agent
            if agent_id == "colonoscopy_scheduler":
                from app.agents.colonoscopy_scheduler import create_colonoscopy_scheduler_agent
                self._agent_factories[agent_id] = create_colonoscopy_scheduler_agent
            else:
                raise ValueError(f"Unknown agent: {agent_id}")

        return self._agent_factories[agent_id]()

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for shim server communication."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.shim_server_timeout)
            )
        return self._http_client

    async def originate(
        self,
        phone_number: str,
        agent_id: str,
        context: Optional[Dict[str, Any]] = None,
        caller_id: Optional[str] = None,
    ) -> str:
        """
        Originate an outbound call.

        Args:
            phone_number: Destination phone number (E.164 format)
            agent_id: Agent to handle the call
            context: Additional context for the agent
            caller_id: Override caller ID (defaults to config)

        Returns:
            Call ID for tracking

        Raises:
            ValueError: If phone number is invalid
            ConnectionError: If shim server is unreachable
        """
        if not self.config.is_ready:
            raise RuntimeError("Telephony not configured properly")

        # Validate phone number
        if not self._validate_phone(phone_number):
            raise ValueError(f"Invalid phone number format: {phone_number}")

        # Validate agent
        if agent_id not in self.config.voice_enabled_agents:
            raise ValueError(f"Agent {agent_id} not enabled for voice")

        # Generate call ID
        call_id = f"call-{uuid.uuid4().hex[:12]}"

        # Build request to shim server
        request_data = {
            "destination": phone_number,
            "callerId": caller_id or self.config.caller_id,
            "callId": call_id,
            "customParameters": {
                "agent": agent_id,
                "direction": "outbound",
                **(context or {}),
            }
        }

        logger.info(f"Originating call {call_id} to {phone_number} with agent {agent_id}")

        try:
            client = await self._get_http_client()
            response = await client.post(
                f"{self.config.shim_server_url}/calls/originate",
                json=request_data,
            )

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Failed to originate call: {error_msg}")
                raise ConnectionError(f"Shim server error: {error_msg}")

            result = response.json()

            # Record the call
            self.call_history[call_id] = CallRecord(
                call_id=call_id,
                direction="outbound",
                caller=caller_id or self.config.caller_id,
                callee=phone_number,
                agent_id=agent_id,
                status="initiating",
                started_at=datetime.now(),
            )

            logger.info(f"Call {call_id} initiated successfully")
            return call_id

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to shim server: {e}")
            raise ConnectionError(f"Cannot reach shim server at {self.config.shim_server_url}")

    async def hangup(self, call_id: str) -> bool:
        """
        Hang up an active call.

        Args:
            call_id: Call to terminate

        Returns:
            True if successful
        """
        logger.info(f"Hanging up call {call_id}")

        try:
            client = await self._get_http_client()
            response = await client.post(
                f"{self.config.shim_server_url}/calls/{call_id}/hangup"
            )

            if response.status_code == 200:
                if call_id in self.call_history:
                    self.call_history[call_id].status = "ended"
                    self.call_history[call_id].ended_at = datetime.now()
                return True
            else:
                logger.warning(f"Failed to hangup call {call_id}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error hanging up call {call_id}: {e}")
            return False

    async def transfer(self, call_id: str, destination: str) -> bool:
        """
        Transfer a call to another number.

        Args:
            call_id: Call to transfer
            destination: Destination number or extension

        Returns:
            True if successful
        """
        logger.info(f"Transferring call {call_id} to {destination}")

        try:
            client = await self._get_http_client()
            response = await client.post(
                f"{self.config.shim_server_url}/calls/{call_id}/transfer",
                json={"destination": destination}
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error transferring call {call_id}: {e}")
            return False

    def update_call_status(
        self,
        call_id: str,
        status: str,
        transcript: Optional[List[Dict]] = None,
        intake_data: Optional[Dict] = None,
        outcome: Optional[str] = None,
    ):
        """
        Update call record with latest status.

        Args:
            call_id: Call to update
            status: New status
            transcript: Call transcript
            intake_data: Data collected during call
            outcome: Call outcome (for completed calls)
        """
        if call_id not in self.call_history:
            logger.warning(f"Call {call_id} not found in history")
            return

        record = self.call_history[call_id]
        record.status = status

        if transcript:
            record.transcript = transcript
        if intake_data:
            record.intake_data = intake_data
        if outcome:
            record.outcome = outcome

        if status in ("ended", "completed", "failed"):
            record.ended_at = datetime.now()
            if record.started_at:
                record.duration_seconds = int(
                    (record.ended_at - record.started_at).total_seconds()
                )

    def get_call_history(
        self,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get call history with optional filters.

        Args:
            agent_id: Filter by agent
            since: Filter calls after this time
            limit: Maximum records to return

        Returns:
            List of call records
        """
        records = list(self.call_history.values())

        if agent_id:
            records = [r for r in records if r.agent_id == agent_id]

        if since:
            records = [r for r in records if r.started_at >= since]

        # Sort by start time, newest first
        records.sort(key=lambda r: r.started_at, reverse=True)

        # Convert to dicts
        return [
            {
                "call_id": r.call_id,
                "direction": r.direction,
                "caller": r.caller,
                "callee": r.callee,
                "agent_id": r.agent_id,
                "status": r.status,
                "started_at": r.started_at.isoformat(),
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "duration_seconds": r.duration_seconds,
                "outcome": r.outcome,
            }
            for r in records[:limit]
        ]

    def get_call_details(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details for a specific call.

        Args:
            call_id: Call to retrieve

        Returns:
            Call details including transcript
        """
        if call_id not in self.call_history:
            return None

        r = self.call_history[call_id]
        return {
            "call_id": r.call_id,
            "direction": r.direction,
            "caller": r.caller,
            "callee": r.callee,
            "agent_id": r.agent_id,
            "status": r.status,
            "started_at": r.started_at.isoformat(),
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            "duration_seconds": r.duration_seconds,
            "transcript": r.transcript,
            "intake_data": r.intake_data,
            "outcome": r.outcome,
            "notes": r.notes,
        }

    async def get_shim_server_status(self) -> Dict[str, Any]:
        """
        Get status of the shim server.

        Returns:
            Shim server health status
        """
        try:
            client = await self._get_http_client()
            response = await client.get(f"{self.config.shim_server_url}/health")

            if response.status_code == 200:
                return {
                    "connected": True,
                    "url": self.config.shim_server_url,
                    **response.json()
                }
            else:
                return {
                    "connected": False,
                    "url": self.config.shim_server_url,
                    "error": f"HTTP {response.status_code}",
                }

        except Exception as e:
            return {
                "connected": False,
                "url": self.config.shim_server_url,
                "error": str(e),
            }

    def _validate_phone(self, number: str) -> bool:
        """
        Validate phone number format.

        Args:
            number: Phone number to validate

        Returns:
            True if valid E.164 format
        """
        import re
        # E.164 format: + followed by 1-15 digits
        return bool(re.match(r'^\+[1-9]\d{1,14}$', number))

    async def close(self):
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_call_manager: Optional[CallManager] = None


def get_call_manager() -> CallManager:
    """Get or create the global call manager instance."""
    global _call_manager
    if _call_manager is None:
        _call_manager = CallManager()
    return _call_manager
