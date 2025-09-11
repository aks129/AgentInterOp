"""
Autonomous two-agent dialog system for BCS evaluation.
"""
import asyncio
import httpx
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum

from app.experimental.claude_client import claude_call


class AgentRole(Enum):
    APPLICANT = "applicant"
    ADMINISTRATOR = "administrator"


class DialogState(Enum):
    STARTING = "starting"
    APPLICANT_TURN = "applicant_turn"
    ADMINISTRATOR_TURN = "administrator_turn"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class DialogTurn:
    """Represents a single turn in the dialog."""
    turn_number: int
    agent_role: AgentRole
    timestamp: str
    source: str  # "claude", "external", "system"
    message: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    state: str = "working"
    error: Optional[str] = None


@dataclass
class DialogConfig:
    """Configuration for autonomous dialog."""
    scenario: str = "bcse"
    facts: Dict[str, Any] = None
    a2a: Dict[str, str] = None  # applicant_endpoint, administrator_endpoint
    options: Dict[str, Any] = None
    guidelines: Dict[str, Any] = None
    api_key: Optional[str] = None


class AutonomousDialog:
    """Manages autonomous two-agent dialog for BCS evaluation."""
    
    def __init__(self, config: DialogConfig):
        self.config = config
        self.run_id = str(uuid.uuid4())
        self.state = DialogState.STARTING
        self.turns: List[DialogTurn] = []
        self.current_turn = 0
        self.final_outcome: Optional[Dict[str, Any]] = None
        self.start_time = datetime.now()
        
        # Options with defaults
        options = config.options or {}
        self.max_turns = options.get("max_turns", 8)
        self.sse_timeout_ms = options.get("sse_timeout_ms", 8000)
        self.poll_interval_ms = options.get("poll_interval_ms", 1200)
        self.dry_run = options.get("dry_run", False)
        
        # Agent personas
        self.applicant_persona = self._get_applicant_persona()
        self.administrator_persona = self._get_administrator_persona()
    
    def _get_applicant_persona(self) -> str:
        """Get applicant agent persona prompt."""
        return """You are an Applicant Agent helping a patient navigate breast cancer screening eligibility.

Your role:
- Present the patient's case clearly and concisely
- Provide requested information when available
- Ask clarifying questions when information is missing
- Stay within the facts provided - do not fabricate data

Return JSON in this format:
{
  "role": "applicant",
  "state": "working|input-required|completed",
  "message": "Brief message describing your action",
  "actions": [
    {"kind": "provide_info", "data": {...}} |
    {"kind": "request_clarification", "question": "..."} |
    {"kind": "accept_decision", "decision": "eligible|needs-more-info|ineligible"}
  ],
  "confidence": 0.8
}

Be concise and professional. Focus on the patient's needs."""

    def _get_administrator_persona(self) -> str:
        """Get administrator agent persona prompt."""
        return """You are an Administrator Agent evaluating breast cancer screening eligibility.

Your role:
- Review patient information against clinical guidelines
- Request additional information when needed
- Make evidence-based eligibility decisions
- Provide clear rationale for decisions

Return JSON in this format:
{
  "role": "administrator", 
  "state": "working|input-required|completed",
  "message": "Brief message describing your evaluation",
  "actions": [
    {"kind": "request_info", "fields": ["field1", "field2"]} |
    {"kind": "request_docs", "items": ["doc1", "doc2"]} |
    {"kind": "propose_decision", "decision": "eligible|needs-more-info|ineligible", "rationale": "..."}
  ],
  "confidence": 0.9
}

Base decisions on clinical guidelines and available evidence."""

    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the autonomous dialog and yield progress frames.
        """
        try:
            self.state = DialogState.APPLICANT_TURN
            
            # Initial frame
            yield {
                "type": "start",
                "run_id": self.run_id,
                "state": self.state.value,
                "timestamp": datetime.now().isoformat()
            }
            
            # Main dialog loop
            while (self.current_turn < self.max_turns and 
                   self.state not in [DialogState.COMPLETED, DialogState.CANCELLED, DialogState.ERROR]):
                
                if self.state == DialogState.APPLICANT_TURN:
                    async for frame in self._process_applicant_turn():
                        yield frame
                elif self.state == DialogState.ADMINISTRATOR_TURN:
                    async for frame in self._process_administrator_turn():
                        yield frame
                
                # Check for completion
                if self._should_complete():
                    self.state = DialogState.COMPLETED
                    break
            
            # Final outcome
            if self.state != DialogState.ERROR:
                self.final_outcome = self._determine_final_outcome()
                yield {
                    "type": "completion",
                    "run_id": self.run_id,
                    "state": "completed",
                    "outcome": self.final_outcome,
                    "total_turns": len(self.turns),
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            self.state = DialogState.ERROR
            yield {
                "type": "error",
                "run_id": self.run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_applicant_turn(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Process applicant agent turn."""
        turn = DialogTurn(
            turn_number=self.current_turn,
            agent_role=AgentRole.APPLICANT,
            timestamp=datetime.now().isoformat(),
            source="claude" if not self.config.a2a.get("applicant_endpoint") else "external",
            message={}
        )
        
        yield {
            "type": "turn_start",
            "run_id": self.run_id,
            "turn": self.current_turn,
            "agent": "applicant",
            "source": turn.source,
            "timestamp": turn.timestamp
        }
        
        try:
            if self.dry_run or not self.config.a2a.get("applicant_endpoint"):
                # Use Claude for applicant
                response = await self._call_claude_agent(AgentRole.APPLICANT)
            else:
                # Use external A2A endpoint
                response = await self._call_a2a_endpoint(
                    self.config.a2a["applicant_endpoint"], 
                    self._build_context_message()
                )
            
            turn.response = response
            turn.state = response.get("state", "completed")
            self.turns.append(turn)
            
            yield {
                "type": "turn_complete",
                "run_id": self.run_id,
                "turn": self.current_turn,
                "agent": "applicant",
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            self.current_turn += 1
            self.state = DialogState.ADMINISTRATOR_TURN
            
        except Exception as e:
            turn.error = str(e)
            turn.state = "error"
            self.turns.append(turn)
            
            yield {
                "type": "turn_error",
                "run_id": self.run_id,
                "turn": self.current_turn,
                "agent": "applicant",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            self.state = DialogState.ERROR
    
    async def _process_administrator_turn(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Process administrator agent turn."""
        turn = DialogTurn(
            turn_number=self.current_turn,
            agent_role=AgentRole.ADMINISTRATOR,
            timestamp=datetime.now().isoformat(),
            source="claude" if not self.config.a2a.get("administrator_endpoint") else "external",
            message={}
        )
        
        yield {
            "type": "turn_start",
            "run_id": self.run_id,
            "turn": self.current_turn,
            "agent": "administrator",
            "source": turn.source,
            "timestamp": turn.timestamp
        }
        
        try:
            if self.dry_run or not self.config.a2a.get("administrator_endpoint"):
                # Use Claude for administrator
                response = await self._call_claude_agent(AgentRole.ADMINISTRATOR)
            else:
                # Use external A2A endpoint
                response = await self._call_a2a_endpoint(
                    self.config.a2a["administrator_endpoint"],
                    self._build_context_message()
                )
            
            turn.response = response
            turn.state = response.get("state", "completed")
            self.turns.append(turn)
            
            yield {
                "type": "turn_complete",
                "run_id": self.run_id,
                "turn": self.current_turn,
                "agent": "administrator", 
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            self.current_turn += 1
            self.state = DialogState.APPLICANT_TURN
            
        except Exception as e:
            turn.error = str(e)
            turn.state = "error"
            self.turns.append(turn)
            
            yield {
                "type": "turn_error",
                "run_id": self.run_id,
                "turn": self.current_turn,
                "agent": "administrator",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            self.state = DialogState.ERROR
    
    async def _call_claude_agent(self, role: AgentRole) -> Dict[str, Any]:
        """Call Claude to generate agent response."""
        persona = self.applicant_persona if role == AgentRole.APPLICANT else self.administrator_persona
        
        # Build context from previous turns
        context = []
        for turn in self.turns[-3:]:  # Last 3 turns for context
            if turn.response:
                context.append({
                    "role": "assistant" if turn.agent_role == role else "user",
                    "content": turn.response.get("message", "")
                })
        
        # Add current facts
        facts_str = json.dumps(self.config.facts, indent=2) if self.config.facts else "No facts available"
        guidelines_str = json.dumps(self.config.guidelines, indent=2) if self.config.guidelines else "No guidelines available"
        
        prompt = f"""{persona}

CURRENT FACTS:
{facts_str}

GUIDELINES:
{guidelines_str}

CONVERSATION CONTEXT:
{json.dumps(context, indent=2) if context else "Starting conversation"}

Please provide your response as JSON following the specified schema."""

        messages = [{"role": "user", "content": prompt}]
        
        result = await claude_call(messages, api_key=self.config.api_key)
        
        if "error" in result:
            raise Exception(f"Claude error: {result['error']}")
        
        return result
    
    async def _call_a2a_endpoint(self, endpoint: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Call external A2A endpoint."""
        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "parts": [{"kind": "text", "text": json.dumps(message)}]
                }
            },
            "id": f"auto_{self.current_turn}"
        }
        
        async with httpx.AsyncClient(timeout=self.sse_timeout_ms / 1000) as client:
            response = await client.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                raise Exception(f"A2A error: {result['error']}")
            
            # Extract message from A2A response
            history = result.get("result", {}).get("history", [])
            if history:
                last_message = history[-1]
                if last_message.get("role") == "agent":
                    parts = last_message.get("parts", [])
                    if parts and parts[0].get("kind") == "text":
                        return json.loads(parts[0]["text"])
            
            raise Exception("No valid response from A2A endpoint")
    
    def _build_context_message(self) -> Dict[str, Any]:
        """Build context message for external agents."""
        return {
            "scenario": self.config.scenario,
            "facts": self.config.facts,
            "guidelines": self.config.guidelines,
            "turn": self.current_turn,
            "previous_turns": [asdict(turn) for turn in self.turns[-2:]]
        }
    
    def _should_complete(self) -> bool:
        """Check if dialog should complete."""
        if not self.turns:
            return False
        
        last_turn = self.turns[-1]
        if last_turn.response:
            actions = last_turn.response.get("actions", [])
            for action in actions:
                if action.get("kind") == "propose_decision":
                    return True
                if action.get("kind") == "accept_decision":
                    return True
        
        return False
    
    def _determine_final_outcome(self) -> Dict[str, Any]:
        """Determine final outcome from dialog turns."""
        from .arbiter import DialogArbiter
        
        arbiter = DialogArbiter(self.config.guidelines)
        return arbiter.determine_outcome(self.turns)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current dialog status."""
        return {
            "run_id": self.run_id,
            "state": self.state.value,
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "total_turns": len(self.turns),
            "start_time": self.start_time.isoformat(),
            "turns": [asdict(turn) for turn in self.turns],
            "final_outcome": self.final_outcome,
            "dry_run": self.dry_run
        }
    
    def cancel(self) -> None:
        """Cancel the dialog."""
        self.state = DialogState.CANCELLED