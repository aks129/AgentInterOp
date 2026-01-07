"""
Clinic Scheduling Workflow - Agent calls clinic on behalf of patient.

This workflow manages the conversation when the agent calls a clinic
to schedule a colonoscopy appointment for a patient.

The agent:
1. Identifies itself as an automated scheduling assistant
2. Provides patient information
3. Requests an appointment
4. Confirms details
5. Gets confirmation number
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class ClinicCallState(str, Enum):
    """States in the clinic call workflow."""
    INITIATING = "initiating"
    GREETING = "greeting"
    IDENTIFYING = "identifying"
    PROVIDING_PATIENT_INFO = "providing_patient_info"
    REQUESTING_APPOINTMENT = "requesting_appointment"
    CONFIRMING_DETAILS = "confirming_details"
    GETTING_CONFIRMATION = "getting_confirmation"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ClinicSchedulingContext:
    """Context for the clinic scheduling workflow."""
    call_id: str
    patient_data: Dict[str, Any]
    current_state: ClinicCallState = ClinicCallState.INITIATING
    clinic_responses: List[Dict[str, str]] = field(default_factory=list)
    offered_appointments: List[Dict[str, Any]] = field(default_factory=list)
    selected_appointment: Optional[Dict[str, Any]] = None
    confirmation_number: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    max_attempts: int = 3


class ClinicSchedulingWorkflow:
    """
    Manages the agent-to-clinic conversation for scheduling.

    This workflow handles outbound calls to GI clinics to schedule
    colonoscopies on behalf of patients.
    """

    # Scripts and prompts for the agent
    SCRIPTS = {
        ClinicCallState.GREETING: (
            "Hello, this is an automated scheduling assistant calling from "
            "{referring_practice}. I'm calling to schedule a colonoscopy "
            "appointment for a patient. Is this a good time?"
        ),
        ClinicCallState.IDENTIFYING: (
            "I'm the automated scheduling system. I have a referral from "
            "Doctor {referring_physician} for a patient who needs a colonoscopy."
        ),
        ClinicCallState.PROVIDING_PATIENT_INFO: (
            "The patient's name is {full_name}. "
            "Date of birth: {dob}. "
            "Insurance: {insurance_provider}, member ID {member_id}. "
            "The referral is for {referral_reason}."
        ),
        ClinicCallState.REQUESTING_APPOINTMENT: (
            "The patient is available {preferred_dates}. "
            "What appointment times do you have available?"
        ),
        ClinicCallState.CONFIRMING_DETAILS: (
            "To confirm: {full_name} is scheduled for {date} at {time}. "
            "Is that correct?"
        ),
        ClinicCallState.GETTING_CONFIRMATION: (
            "What is the confirmation number for this appointment?"
        ),
        ClinicCallState.COMPLETE: (
            "Thank you very much. The patient will receive prep instructions. "
            "Have a great day!"
        ),
    }

    def __init__(self, patient_data: Dict[str, Any], call_id: str):
        """
        Initialize the clinic scheduling workflow.

        Args:
            patient_data: Patient information collected during intake
            call_id: Unique identifier for this call
        """
        self.context = ClinicSchedulingContext(
            call_id=call_id,
            patient_data=patient_data
        )
        self._llm_client = None

    def get_opening_script(self) -> str:
        """Get the initial script when the clinic answers."""
        self.context.current_state = ClinicCallState.GREETING
        return self.SCRIPTS[ClinicCallState.GREETING].format(
            referring_practice=self.context.patient_data.get(
                "referring_practice", "the patient's doctor"
            )
        )

    async def process_clinic_response(self, response: str) -> str:
        """
        Process what the clinic staff says and generate appropriate response.

        Args:
            response: What the clinic staff said

        Returns:
            Agent's response
        """
        # Record the clinic response
        self.context.clinic_responses.append({
            "role": "clinic",
            "content": response,
            "timestamp": datetime.now().isoformat(),
        })

        current_state = self.context.current_state
        response_lower = response.lower()

        try:
            # Handle based on current state
            if current_state == ClinicCallState.GREETING:
                return await self._handle_greeting_response(response_lower)

            elif current_state == ClinicCallState.IDENTIFYING:
                return await self._handle_identification_response(response_lower)

            elif current_state == ClinicCallState.PROVIDING_PATIENT_INFO:
                return await self._handle_patient_info_response(response_lower)

            elif current_state == ClinicCallState.REQUESTING_APPOINTMENT:
                return await self._handle_appointment_response(response)

            elif current_state == ClinicCallState.CONFIRMING_DETAILS:
                return await self._handle_confirmation_response(response_lower)

            elif current_state == ClinicCallState.GETTING_CONFIRMATION:
                return await self._handle_confirmation_number(response)

            else:
                return await self._handle_unexpected_response(response)

        except Exception as e:
            logger.exception(f"Error processing clinic response: {e}")
            return "I apologize, could you please repeat that?"

    async def _handle_greeting_response(self, response: str) -> str:
        """Handle response to initial greeting."""
        # Check for positive acknowledgment
        if any(word in response for word in ["yes", "sure", "okay", "go ahead", "how can i help"]):
            self.context.current_state = ClinicCallState.IDENTIFYING
            return self.SCRIPTS[ClinicCallState.IDENTIFYING].format(
                referring_physician=self.context.patient_data.get(
                    "referring_physician", "the primary care physician"
                )
            )
        elif any(word in response for word in ["hold", "wait", "moment", "transfer"]):
            # Being transferred or asked to hold
            return "Of course, I'll hold. Thank you."
        elif any(word in response for word in ["busy", "call back", "not a good time"]):
            # Bad time, offer to call back
            return "I understand. When would be a better time for me to call back?"
        else:
            # Not sure, proceed anyway
            self.context.current_state = ClinicCallState.IDENTIFYING
            return self.SCRIPTS[ClinicCallState.IDENTIFYING].format(
                referring_physician=self.context.patient_data.get(
                    "referring_physician", "the primary care physician"
                )
            )

    async def _handle_identification_response(self, response: str) -> str:
        """Handle response after identification."""
        # They might ask for more info or be ready for patient details
        if any(word in response for word in ["patient", "name", "information", "details"]):
            self.context.current_state = ClinicCallState.PROVIDING_PATIENT_INFO
            return self.SCRIPTS[ClinicCallState.PROVIDING_PATIENT_INFO].format(
                **self.context.patient_data
            )
        elif any(word in response for word in ["referral", "fax", "send"]):
            return (
                "The referral has been sent from Doctor "
                f"{self.context.patient_data.get('referring_physician')}'s office. "
                "Would you like me to provide the patient information?"
            )
        else:
            # Proceed to patient info
            self.context.current_state = ClinicCallState.PROVIDING_PATIENT_INFO
            return self.SCRIPTS[ClinicCallState.PROVIDING_PATIENT_INFO].format(
                **self.context.patient_data
            )

    async def _handle_patient_info_response(self, response: str) -> str:
        """Handle response after providing patient info."""
        # They might ask for specific details or be ready to schedule
        if "insurance" in response:
            return (
                f"The insurance is {self.context.patient_data.get('insurance_provider')}, "
                f"member ID {self.context.patient_data.get('member_id')}."
            )
        elif "date of birth" in response or "dob" in response:
            return f"The date of birth is {self.context.patient_data.get('dob')}."
        elif any(word in response for word in ["schedule", "appointment", "available", "when"]):
            self.context.current_state = ClinicCallState.REQUESTING_APPOINTMENT
            return self.SCRIPTS[ClinicCallState.REQUESTING_APPOINTMENT].format(
                preferred_dates=self.context.patient_data.get(
                    "preferred_dates", "any time in the next two weeks"
                )
            )
        else:
            # Ask about scheduling
            self.context.current_state = ClinicCallState.REQUESTING_APPOINTMENT
            return (
                "Thank you. What appointment times do you have available for a colonoscopy?"
            )

    async def _handle_appointment_response(self, response: str) -> str:
        """Handle response with appointment offerings."""
        # Use LLM to extract appointment details from natural language
        appointments = await self._extract_appointments_from_response(response)

        if appointments:
            self.context.offered_appointments = appointments
            # Select the first offered appointment
            selected = appointments[0]
            self.context.selected_appointment = selected
            self.context.current_state = ClinicCallState.CONFIRMING_DETAILS

            return self.SCRIPTS[ClinicCallState.CONFIRMING_DETAILS].format(
                full_name=self.context.patient_data.get("full_name"),
                date=selected.get("date", "the offered date"),
                time=selected.get("time", "the offered time")
            )

        elif any(word in response.lower() for word in ["no appointments", "full", "booked", "waitlist"]):
            self.context.notes.append("No appointments available, offered waitlist")
            return (
                "I understand. Is there a waitlist the patient can be added to? "
                "Or when is the next available appointment?"
            )
        else:
            # Ask for clarification
            return "Could you please tell me what dates and times are available?"

    async def _handle_confirmation_response(self, response: str) -> str:
        """Handle response to appointment confirmation."""
        if any(word in response for word in ["yes", "correct", "confirmed", "right"]):
            self.context.current_state = ClinicCallState.GETTING_CONFIRMATION
            return self.SCRIPTS[ClinicCallState.GETTING_CONFIRMATION]
        elif any(word in response for word in ["no", "incorrect", "wrong"]):
            # Ask what's wrong
            return "I apologize, what needs to be corrected?"
        else:
            self.context.current_state = ClinicCallState.GETTING_CONFIRMATION
            return "Is the appointment confirmed? What is the confirmation number?"

    async def _handle_confirmation_number(self, response: str) -> str:
        """Handle confirmation number from clinic."""
        # Extract confirmation number from response
        confirmation = await self._extract_confirmation_number(response)

        if confirmation:
            self.context.confirmation_number = confirmation
            self.context.current_state = ClinicCallState.COMPLETE
            return self.SCRIPTS[ClinicCallState.COMPLETE]
        else:
            # Ask again
            return "I didn't catch the confirmation number. Could you repeat that please?"

    async def _handle_unexpected_response(self, response: str) -> str:
        """Handle unexpected responses using LLM."""
        # Use Claude to generate appropriate response
        try:
            from app.llm.anthropic import get_completion

            prompt = f"""You are a scheduling assistant on a phone call with a medical clinic.
You are scheduling a colonoscopy for a patient.

Patient information:
- Name: {self.context.patient_data.get('full_name')}
- DOB: {self.context.patient_data.get('dob')}
- Insurance: {self.context.patient_data.get('insurance_provider')}
- Referral from: {self.context.patient_data.get('referring_physician')}

The clinic staff just said: "{response}"

Generate a brief, professional response to continue the scheduling process.
Keep it under 2 sentences. Be polite and focused on scheduling."""

            result = await get_completion(prompt)
            return result.strip()

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "Could you please repeat that? I want to make sure I have the correct information."

    async def _extract_appointments_from_response(self, response: str) -> List[Dict[str, Any]]:
        """Extract appointment offerings from clinic's natural language response."""
        # Simple pattern matching first
        import re

        appointments = []

        # Look for date/time patterns
        # e.g., "January 15th at 9 AM", "next Monday at 2:30"
        date_time_pattern = r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)?)'
        matches = re.findall(date_time_pattern, response, re.IGNORECASE)

        for match in matches:
            appointments.append({
                "raw": match,
                "date": match.split(" at ")[0] if " at " in match else match,
                "time": match.split(" at ")[1] if " at " in match else "TBD",
            })

        # If pattern matching fails, try LLM
        if not appointments and len(response) > 20:
            try:
                from app.llm.anthropic import get_completion

                prompt = f"""Extract appointment date and time from this clinic response:
"{response}"

Return in format: DATE, TIME
If no appointment is mentioned, return: NONE

Examples:
- "We have January 15th at 9 AM" -> January 15th, 9 AM
- "Nothing available this month" -> NONE
"""
                result = await get_completion(prompt)
                if result.strip() != "NONE":
                    parts = result.split(",")
                    if len(parts) >= 2:
                        appointments.append({
                            "date": parts[0].strip(),
                            "time": parts[1].strip(),
                        })

            except Exception as e:
                logger.error(f"LLM extraction error: {e}")

        return appointments

    async def _extract_confirmation_number(self, response: str) -> Optional[str]:
        """Extract confirmation number from response."""
        import re

        # Common confirmation number patterns
        patterns = [
            r'confirmation\s*(?:number|#)?\s*[:\s]*([A-Z0-9-]+)',
            r'reference\s*(?:number|#)?\s*[:\s]*([A-Z0-9-]+)',
            r'([A-Z]{2,3}[-]?\d{6,10})',  # COL-123456
            r'(\d{8,12})',  # 12345678
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return None

    def get_result(self) -> Dict[str, Any]:
        """Get the workflow result."""
        return {
            "call_id": self.context.call_id,
            "success": self.context.current_state == ClinicCallState.COMPLETE,
            "state": self.context.current_state.value,
            "patient_name": self.context.patient_data.get("full_name"),
            "selected_appointment": self.context.selected_appointment,
            "confirmation_number": self.context.confirmation_number,
            "notes": self.context.notes,
            "conversation_length": len(self.context.clinic_responses),
            "started_at": self.context.started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
        }

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.context.current_state in (
            ClinicCallState.COMPLETE,
            ClinicCallState.FAILED
        )

    def is_successful(self) -> bool:
        """Check if workflow completed successfully."""
        return (
            self.context.current_state == ClinicCallState.COMPLETE
            and self.context.confirmation_number is not None
        )
