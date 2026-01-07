"""
Patient Scheduling Workflow - Handles inbound patient calls for scheduling.

This workflow manages the conversation flow when a patient calls
to schedule a colonoscopy appointment.

States:
1. greeting - Initial greeting and name collection
2. demographics - Collect basic patient info
3. insurance - Insurance verification
4. referral - Referral information
5. medical_history - Medical history questions
6. scheduling - Find and book appointment
7. confirmation - Confirm appointment details
8. prep_instructions - Provide prep instructions
9. complete - Call completed
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """States in the patient scheduling workflow."""
    GREETING = "greeting"
    DEMOGRAPHICS = "demographics"
    INSURANCE = "insurance"
    REFERRAL = "referral"
    MEDICAL_HISTORY = "medical_history"
    SCHEDULING = "scheduling"
    CONFIRMATION = "confirmation"
    PREP_INSTRUCTIONS = "prep_instructions"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class PatientSchedulingContext:
    """Context for the patient scheduling workflow."""
    call_id: str
    current_state: WorkflowState = WorkflowState.GREETING
    collected_data: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    selected_appointment: Optional[Dict[str, Any]] = None
    confirmation_number: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)


class PatientSchedulingWorkflow:
    """
    Manages the patient scheduling conversation flow.

    This workflow wraps the Colonoscopy Scheduler Agent with
    voice-optimized prompts and state management.
    """

    # Voice prompts for each state
    PROMPTS = {
        WorkflowState.GREETING: (
            "Thank you for calling to schedule your colonoscopy. "
            "My name is the automated scheduling assistant. "
            "To get started, may I have your full legal name please?"
        ),
        WorkflowState.DEMOGRAPHICS: {
            "dob": "Thank you, {name}. What is your date of birth?",
            "address": "And what is your home address?",
            "phone": "What is the best phone number to reach you?",
            "email": "And your email address?",
            "emergency_contact": "Finally, who is your emergency contact and their phone number?",
        },
        WorkflowState.INSURANCE: {
            "provider": "Now let's verify your insurance. What is your insurance company?",
            "member_id": "What is your member or subscriber I D number?",
            "group": "And your group number if you have one?",
        },
        WorkflowState.REFERRAL: {
            "physician": "Who is the doctor that referred you for this colonoscopy?",
            "practice": "What is the name of their practice or clinic?",
            "reason": (
                "What is the reason for your colonoscopy? "
                "For example, routine screening, follow-up, or symptoms?"
            ),
        },
        WorkflowState.MEDICAL_HISTORY: {
            "previous": "Have you had a colonoscopy before?",
            "medications": "Are you taking any blood thinners like Warfarin or Eliquis?",
            "conditions": "Do you have any heart or lung conditions we should know about?",
        },
        WorkflowState.SCHEDULING: {
            "preferences": "When would you prefer to schedule your procedure?",
            "driver": "Will you have someone to drive you home after the procedure?",
            "offer": (
                "I found an appointment available on {date} at {time}. "
                "Would that work for you?"
            ),
        },
        WorkflowState.CONFIRMATION: (
            "Your appointment is confirmed for {date} at {time} "
            "at G I Specialists. Your confirmation number is {confirmation}. "
            "Would you like me to explain the preparation instructions?"
        ),
        WorkflowState.PREP_INSTRUCTIONS: (
            "Here are your preparation instructions. "
            "Starting 7 days before, stop taking iron supplements. "
            "5 days before, avoid seeds, nuts, and high-fiber foods. "
            "The day before, you'll be on clear liquids only, no red or purple drinks. "
            "You'll need to take your bowel prep as directed. "
            "On the day of the procedure, arrive 30 minutes early "
            "and bring your I D and insurance card. "
            "Do you have any questions?"
        ),
        WorkflowState.COMPLETE: (
            "Your appointment is all set. We'll send you a confirmation email "
            "with all the details and prep instructions. "
            "If you have any questions, please call us back. "
            "Thank you and have a great day!"
        ),
    }

    def __init__(self, agent, call_id: str):
        """
        Initialize the workflow.

        Args:
            agent: The Colonoscopy Scheduler Agent instance
            call_id: Unique identifier for this call
        """
        self.agent = agent
        self.context = PatientSchedulingContext(call_id=call_id)

    def get_initial_greeting(self) -> str:
        """Get the initial greeting for the call."""
        return self.PROMPTS[WorkflowState.GREETING]

    async def process_input(self, user_input: str) -> str:
        """
        Process user input and return the next response.

        Args:
            user_input: What the patient said

        Returns:
            Agent's voice response
        """
        # Add to conversation history
        self.context.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        })

        # Process based on current state
        current_state = self.context.current_state
        response = ""

        try:
            if current_state == WorkflowState.GREETING:
                response = await self._handle_greeting(user_input)

            elif current_state == WorkflowState.DEMOGRAPHICS:
                response = await self._handle_demographics(user_input)

            elif current_state == WorkflowState.INSURANCE:
                response = await self._handle_insurance(user_input)

            elif current_state == WorkflowState.REFERRAL:
                response = await self._handle_referral(user_input)

            elif current_state == WorkflowState.MEDICAL_HISTORY:
                response = await self._handle_medical_history(user_input)

            elif current_state == WorkflowState.SCHEDULING:
                response = await self._handle_scheduling(user_input)

            elif current_state == WorkflowState.CONFIRMATION:
                response = await self._handle_confirmation(user_input)

            elif current_state == WorkflowState.PREP_INSTRUCTIONS:
                response = await self._handle_prep_instructions(user_input)

            elif current_state == WorkflowState.COMPLETE:
                response = self.PROMPTS[WorkflowState.COMPLETE]

        except Exception as e:
            logger.exception(f"Error processing input: {e}")
            self.context.errors.append(str(e))
            response = "I'm sorry, I had trouble processing that. Could you please repeat?"

        # Add response to conversation history
        self.context.conversation_history.append({
            "role": "agent",
            "content": response,
            "timestamp": datetime.now().isoformat(),
        })

        return response

    async def _handle_greeting(self, user_input: str) -> str:
        """Handle greeting state - collect name."""
        # Let the agent extract the name
        result = self.agent.process_message(user_input)

        if self.agent.workflow_state["intake_data"].get("full_name"):
            name = self.agent.workflow_state["intake_data"]["full_name"]
            self.context.collected_data["full_name"] = name
            self.context.current_state = WorkflowState.DEMOGRAPHICS

            return self.PROMPTS[WorkflowState.DEMOGRAPHICS]["dob"].format(name=name)
        else:
            return "I didn't catch your name. Could you please tell me your full legal name?"

    async def _handle_demographics(self, user_input: str) -> str:
        """Handle demographics collection."""
        # Process with agent
        result = self.agent.process_message(user_input)
        intake_data = self.agent.workflow_state["intake_data"]

        # Check what we still need
        if not intake_data.get("dob"):
            return self.PROMPTS[WorkflowState.DEMOGRAPHICS]["dob"].format(
                name=intake_data.get("full_name", "")
            )
        elif not intake_data.get("address"):
            return self.PROMPTS[WorkflowState.DEMOGRAPHICS]["address"]
        elif not intake_data.get("phone"):
            return self.PROMPTS[WorkflowState.DEMOGRAPHICS]["phone"]
        elif not intake_data.get("email"):
            return self.PROMPTS[WorkflowState.DEMOGRAPHICS]["email"]
        elif not intake_data.get("emergency_contact"):
            return self.PROMPTS[WorkflowState.DEMOGRAPHICS]["emergency_contact"]
        else:
            # Demographics complete, move to insurance
            self.context.current_state = WorkflowState.INSURANCE
            self.context.collected_data.update(intake_data)
            return self.PROMPTS[WorkflowState.INSURANCE]["provider"]

    async def _handle_insurance(self, user_input: str) -> str:
        """Handle insurance information collection."""
        result = self.agent.process_message(user_input)
        intake_data = self.agent.workflow_state["intake_data"]

        if not intake_data.get("insurance_provider"):
            return self.PROMPTS[WorkflowState.INSURANCE]["provider"]
        elif not intake_data.get("member_id"):
            return self.PROMPTS[WorkflowState.INSURANCE]["member_id"]
        elif not intake_data.get("group_number"):
            # Group number is optional, allow skip
            if "no" in user_input.lower() or "none" in user_input.lower():
                intake_data["group_number"] = "N/A"
            else:
                return self.PROMPTS[WorkflowState.INSURANCE]["group"]

        # Insurance complete, verify and move to referral
        verification = self.agent.verify_insurance()
        if verification.get("verified"):
            self.context.current_state = WorkflowState.REFERRAL
            return (
                "Great, I've verified your insurance coverage. "
                f"{self.PROMPTS[WorkflowState.REFERRAL]['physician']}"
            )
        else:
            return (
                "I had trouble verifying your insurance. Let me try again. "
                "What is your insurance company name?"
            )

    async def _handle_referral(self, user_input: str) -> str:
        """Handle referral information collection."""
        result = self.agent.process_message(user_input)
        intake_data = self.agent.workflow_state["intake_data"]

        if not intake_data.get("referring_physician"):
            return self.PROMPTS[WorkflowState.REFERRAL]["physician"]
        elif not intake_data.get("referring_practice"):
            return self.PROMPTS[WorkflowState.REFERRAL]["practice"]
        elif not intake_data.get("referral_reason"):
            return self.PROMPTS[WorkflowState.REFERRAL]["reason"]
        else:
            # Referral complete, move to medical history
            self.context.current_state = WorkflowState.MEDICAL_HISTORY
            return (
                "Thank you for that information. "
                f"{self.PROMPTS[WorkflowState.MEDICAL_HISTORY]['previous']}"
            )

    async def _handle_medical_history(self, user_input: str) -> str:
        """Handle medical history collection."""
        result = self.agent.process_message(user_input)
        intake_data = self.agent.workflow_state["intake_data"]

        # Simple yes/no questions
        if "previous_colonoscopy" not in intake_data:
            if "yes" in user_input.lower():
                intake_data["previous_colonoscopy"] = True
            elif "no" in user_input.lower():
                intake_data["previous_colonoscopy"] = False
            else:
                return self.PROMPTS[WorkflowState.MEDICAL_HISTORY]["previous"]

            return self.PROMPTS[WorkflowState.MEDICAL_HISTORY]["medications"]

        if "blood_thinners" not in intake_data:
            if "yes" in user_input.lower():
                intake_data["blood_thinners"] = True
            elif "no" in user_input.lower():
                intake_data["blood_thinners"] = False
            else:
                return self.PROMPTS[WorkflowState.MEDICAL_HISTORY]["medications"]

            return self.PROMPTS[WorkflowState.MEDICAL_HISTORY]["conditions"]

        if "heart_conditions" not in intake_data:
            intake_data["heart_conditions"] = user_input

        # Medical history complete, move to scheduling
        self.context.current_state = WorkflowState.SCHEDULING
        return (
            "Thank you for sharing that information. "
            f"{self.PROMPTS[WorkflowState.SCHEDULING]['preferences']}"
        )

    async def _handle_scheduling(self, user_input: str) -> str:
        """Handle appointment scheduling."""
        intake_data = self.agent.workflow_state["intake_data"]

        # Check for driver confirmation
        if "transportation" not in intake_data:
            if "yes" in user_input.lower():
                intake_data["transportation"] = True
            elif "no" in user_input.lower():
                return (
                    "You must have someone to drive you home after the procedure "
                    "due to the sedation. Can you arrange for a driver?"
                )
            else:
                # First time - collect preferences, then ask about driver
                intake_data["preferred_dates"] = user_input
                return self.PROMPTS[WorkflowState.SCHEDULING]["driver"]

        # Search for appointments
        if not self.context.selected_appointment:
            appointments = self.agent.search_appointments()
            if appointments.get("appointments"):
                appt = appointments["appointments"][0]
                self.context.selected_appointment = appt
                return self.PROMPTS[WorkflowState.SCHEDULING]["offer"].format(
                    date=appt["date_display"],
                    time=appt["time_display"]
                )
            else:
                return (
                    "I'm sorry, I couldn't find any available appointments. "
                    "Would you like me to check different dates?"
                )

        # Confirm or reject offered appointment
        if "yes" in user_input.lower():
            # Book the appointment
            result = self.agent.select_appointment(
                self.context.selected_appointment["id"]
            )
            if result.get("success"):
                self.context.confirmation_number = result.get("confirmation_number")
                self.context.current_state = WorkflowState.CONFIRMATION

                appt = self.context.selected_appointment
                return self.PROMPTS[WorkflowState.CONFIRMATION].format(
                    date=appt["date_display"],
                    time=appt["time_display"],
                    confirmation=self.context.confirmation_number
                )
            else:
                return f"I had trouble booking that appointment: {result.get('error')}. Let me find another time."
        else:
            # Try another appointment
            appointments = self.agent.workflow_state.get("available_appointments", [])
            if len(appointments) > 1:
                # Skip to next appointment
                self.context.selected_appointment = appointments[1]
                appt = self.context.selected_appointment
                return f"How about {appt['date_display']} at {appt['time_display']}?"
            else:
                return "Would you like me to search for different dates?"

    async def _handle_confirmation(self, user_input: str) -> str:
        """Handle appointment confirmation."""
        if "yes" in user_input.lower():
            self.context.current_state = WorkflowState.PREP_INSTRUCTIONS
            return self.PROMPTS[WorkflowState.PREP_INSTRUCTIONS]
        else:
            self.context.current_state = WorkflowState.COMPLETE
            return self.PROMPTS[WorkflowState.COMPLETE]

    async def _handle_prep_instructions(self, user_input: str) -> str:
        """Handle prep instructions delivery."""
        # Check for questions
        if "?" in user_input or "question" in user_input.lower():
            # Let agent handle questions
            result = self.agent.process_message(user_input)
            return result.get("message", "Is there anything else you'd like to know?")
        else:
            self.context.current_state = WorkflowState.COMPLETE
            return self.PROMPTS[WorkflowState.COMPLETE]

    def get_state(self) -> Dict[str, Any]:
        """Get current workflow state."""
        return {
            "call_id": self.context.call_id,
            "current_state": self.context.current_state.value,
            "collected_data": self.context.collected_data,
            "selected_appointment": self.context.selected_appointment,
            "confirmation_number": self.context.confirmation_number,
            "conversation_length": len(self.context.conversation_history),
            "errors": self.context.errors,
            "started_at": self.context.started_at.isoformat(),
        }

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.context.current_state == WorkflowState.COMPLETE
