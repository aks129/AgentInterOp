"""
Colonoscopy Scheduling Agent - Automates the complex colonoscopy scheduling workflow.

Problem Being Solved:
- Scheduling a colonoscopy is frustrating even with a PCP referral
- Long phone queue wait times to reach the clinic
- Complex 40+ question intake forms that need to be filled out
- Coordination between multiple parties (patient, PCP, specialist, insurance)

This agent automates:
1. Intake form completion - Gathers and pre-fills patient information
2. Insurance verification - Checks coverage and prior authorization
3. Clinic availability search - Finds available appointments
4. Appointment scheduling - Books the procedure
5. Prep instructions delivery - Provides colonoscopy preparation guidance
"""

import json
import logging
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SchedulingStatus(str, Enum):
    """Status of the scheduling workflow"""
    INITIATED = "initiated"
    INTAKE_IN_PROGRESS = "intake_in_progress"
    INTAKE_COMPLETE = "intake_complete"
    INSURANCE_VERIFIED = "insurance_verified"
    SEARCHING_APPOINTMENTS = "searching_appointments"
    APPOINTMENT_OFFERED = "appointment_offered"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    PREP_INSTRUCTIONS_SENT = "prep_instructions_sent"
    COMPLETED = "completed"
    FAILED = "failed"


# Standard colonoscopy intake questions (40+ questions simplified into categories)
INTAKE_FORM_SECTIONS = {
    "demographics": {
        "section_name": "Patient Demographics",
        "questions": [
            {"id": "full_name", "question": "Full legal name", "type": "text", "required": True},
            {"id": "dob", "question": "Date of birth", "type": "date", "required": True},
            {"id": "sex", "question": "Sex assigned at birth", "type": "choice", "options": ["Male", "Female"], "required": True},
            {"id": "address", "question": "Home address", "type": "text", "required": True},
            {"id": "phone", "question": "Phone number", "type": "phone", "required": True},
            {"id": "email", "question": "Email address", "type": "email", "required": True},
            {"id": "emergency_contact", "question": "Emergency contact name and phone", "type": "text", "required": True},
        ]
    },
    "insurance": {
        "section_name": "Insurance Information",
        "questions": [
            {"id": "insurance_provider", "question": "Insurance company name", "type": "text", "required": True},
            {"id": "member_id", "question": "Member/Subscriber ID", "type": "text", "required": True},
            {"id": "group_number", "question": "Group number", "type": "text", "required": False},
            {"id": "policyholder_name", "question": "Policyholder name (if different)", "type": "text", "required": False},
            {"id": "policyholder_dob", "question": "Policyholder date of birth (if different)", "type": "date", "required": False},
        ]
    },
    "referral": {
        "section_name": "Referral Information",
        "questions": [
            {"id": "referring_physician", "question": "Referring physician name", "type": "text", "required": True},
            {"id": "referring_practice", "question": "Referring practice/clinic name", "type": "text", "required": True},
            {"id": "referring_phone", "question": "Referring physician phone", "type": "phone", "required": True},
            {"id": "referring_fax", "question": "Referring physician fax", "type": "phone", "required": False},
            {"id": "referral_reason", "question": "Reason for referral", "type": "choice", "options": [
                "Routine screening (age 45+)",
                "Follow-up from previous colonoscopy",
                "Positive FIT/stool test",
                "Family history of colon cancer",
                "Symptoms (bleeding, change in bowel habits)",
                "Anemia workup",
                "Other"
            ], "required": True},
            {"id": "referral_date", "question": "Date of referral", "type": "date", "required": True},
        ]
    },
    "medical_history": {
        "section_name": "Medical History",
        "questions": [
            {"id": "previous_colonoscopy", "question": "Have you had a colonoscopy before?", "type": "boolean", "required": True},
            {"id": "previous_colonoscopy_date", "question": "If yes, when was your last colonoscopy?", "type": "date", "required": False},
            {"id": "previous_findings", "question": "Previous colonoscopy findings (polyps, etc.)", "type": "text", "required": False},
            {"id": "colon_cancer_history", "question": "Personal history of colon cancer or polyps?", "type": "boolean", "required": True},
            {"id": "family_colon_cancer", "question": "Family history of colon cancer?", "type": "boolean", "required": True},
            {"id": "family_colon_cancer_details", "question": "If yes, which relatives and at what age?", "type": "text", "required": False},
            {"id": "ibd_history", "question": "History of inflammatory bowel disease (Crohn's, Ulcerative Colitis)?", "type": "boolean", "required": True},
            {"id": "current_symptoms", "question": "Current GI symptoms", "type": "multi_choice", "options": [
                "None",
                "Rectal bleeding",
                "Blood in stool",
                "Change in bowel habits",
                "Abdominal pain",
                "Unexplained weight loss",
                "Anemia"
            ], "required": True},
        ]
    },
    "medications": {
        "section_name": "Current Medications",
        "questions": [
            {"id": "blood_thinners", "question": "Do you take blood thinners?", "type": "boolean", "required": True},
            {"id": "blood_thinner_list", "question": "List blood thinners (Warfarin, Eliquis, Plavix, etc.)", "type": "text", "required": False},
            {"id": "diabetes_meds", "question": "Do you take diabetes medications?", "type": "boolean", "required": True},
            {"id": "diabetes_med_list", "question": "List diabetes medications", "type": "text", "required": False},
            {"id": "other_medications", "question": "List all other current medications", "type": "text", "required": True},
            {"id": "allergies", "question": "Drug allergies", "type": "text", "required": True},
        ]
    },
    "health_conditions": {
        "section_name": "Health Conditions",
        "questions": [
            {"id": "heart_conditions", "question": "Heart conditions (pacemaker, valve replacement, heart failure)?", "type": "text", "required": True},
            {"id": "lung_conditions", "question": "Lung conditions (COPD, sleep apnea, oxygen use)?", "type": "text", "required": True},
            {"id": "kidney_disease", "question": "Kidney disease or dialysis?", "type": "boolean", "required": True},
            {"id": "liver_disease", "question": "Liver disease or cirrhosis?", "type": "boolean", "required": True},
            {"id": "bleeding_disorder", "question": "Bleeding or clotting disorders?", "type": "boolean", "required": True},
            {"id": "previous_surgeries", "question": "Previous abdominal surgeries", "type": "text", "required": True},
            {"id": "anesthesia_problems", "question": "Any problems with anesthesia in the past?", "type": "text", "required": True},
        ]
    },
    "scheduling_preferences": {
        "section_name": "Scheduling Preferences",
        "questions": [
            {"id": "preferred_dates", "question": "Preferred appointment dates/times", "type": "text", "required": True},
            {"id": "dates_to_avoid", "question": "Dates to avoid", "type": "text", "required": False},
            {"id": "preferred_location", "question": "Preferred facility location", "type": "text", "required": False},
            {"id": "transportation", "question": "Will you have a driver to take you home?", "type": "boolean", "required": True},
            {"id": "driver_name", "question": "Name of person driving you home", "type": "text", "required": True},
            {"id": "special_needs", "question": "Any special accommodations needed?", "type": "text", "required": False},
        ]
    }
}

# Colonoscopy prep instructions template
PREP_INSTRUCTIONS = {
    "title": "Colonoscopy Preparation Instructions",
    "overview": "A successful colonoscopy requires a clean colon. Please follow these instructions carefully.",
    "prep_timeline": [
        {
            "timing": "7 days before",
            "instructions": [
                "Stop taking iron supplements",
                "Review your medications with the scheduling nurse",
                "Arrange for someone to drive you home after the procedure",
                "Purchase your bowel prep kit from the pharmacy"
            ]
        },
        {
            "timing": "5 days before",
            "instructions": [
                "Stop eating seeds, nuts, popcorn, and high-fiber foods",
                "Stop taking blood thinners if instructed by your doctor"
            ]
        },
        {
            "timing": "1 day before",
            "instructions": [
                "Clear liquid diet only (no red or purple liquids)",
                "Allowed: water, clear broth, apple juice, white grape juice, Gatorade (not red/purple), black coffee/tea, Jell-O (not red/purple)",
                "NOT allowed: milk, cream, orange juice, alcohol, anything you cannot see through",
                "Begin bowel prep as instructed (usually evening)"
            ]
        },
        {
            "timing": "Day of procedure",
            "instructions": [
                "Continue clear liquids until 4 hours before procedure",
                "Complete second dose of prep if split-dose regimen",
                "Take morning medications with small sip of water (unless told otherwise)",
                "Do NOT take diabetes medications the morning of the procedure",
                "Bring photo ID and insurance card",
                "Wear comfortable, loose clothing",
                "Leave jewelry and valuables at home"
            ]
        }
    ],
    "what_to_expect": [
        "The procedure takes about 30-60 minutes",
        "You will receive sedation and will not feel pain",
        "You will need 1-2 hours in recovery",
        "You MUST have someone drive you home - you cannot drive, take a taxi alone, or use public transportation",
        "Plan to rest for the remainder of the day",
        "You can resume normal diet after the procedure unless told otherwise"
    ],
    "warning_signs": [
        "Call immediately if you experience: severe abdominal pain, fever over 101F, heavy rectal bleeding, or persistent nausea/vomiting"
    ]
}


class ColonoscopySchedulerAgent:
    """
    Colonoscopy Scheduling Agent - Automates the complex colonoscopy scheduling workflow.

    This agent solves real patient problems:
    - Eliminates long phone queue wait times
    - Pre-fills 40+ intake form questions through conversation
    - Verifies insurance and referral information
    - Finds available appointments
    - Provides prep instructions

    The agent demonstrates:
    - Complex multi-step workflow automation
    - Healthcare form processing
    - Insurance/eligibility verification
    - Appointment scheduling integration
    - Patient education delivery
    """

    def __init__(self):
        self.agent_id = "colonoscopy_scheduler"
        self.name = "Colonoscopy Scheduling Agent"
        self.description = "Automates colonoscopy scheduling - intake forms, insurance verification, and appointment booking"
        self.domain = "gi_scheduling"
        self.role = "scheduling_coordinator"

        # Workflow state
        self.workflow_state = {
            "status": SchedulingStatus.INITIATED,
            "intake_data": {},
            "completed_sections": [],
            "insurance_verified": False,
            "referral_verified": False,
            "available_appointments": [],
            "selected_appointment": None,
            "prep_instructions_sent": False
        }

        # Track conversation
        self.conversation_history = []

        logger.info("Colonoscopy Scheduling Agent initialized")

    def get_intake_progress(self) -> Dict[str, Any]:
        """Get progress on intake form completion"""
        total_questions = sum(len(section["questions"]) for section in INTAKE_FORM_SECTIONS.values())
        answered_questions = len(self.workflow_state["intake_data"])

        section_progress = {}
        for section_id, section in INTAKE_FORM_SECTIONS.items():
            section_questions = [q["id"] for q in section["questions"]]
            answered = sum(1 for q in section_questions if q in self.workflow_state["intake_data"])
            section_progress[section_id] = {
                "name": section["section_name"],
                "total": len(section_questions),
                "answered": answered,
                "complete": answered == len(section_questions)
            }

        return {
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "progress_percent": round((answered_questions / total_questions) * 100, 1) if total_questions > 0 else 0,
            "sections": section_progress,
            "completed_sections": self.workflow_state["completed_sections"]
        }

    def get_next_questions(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get the next unanswered questions to ask"""
        questions = []

        for section_id, section in INTAKE_FORM_SECTIONS.items():
            if section_id in self.workflow_state["completed_sections"]:
                continue

            for question in section["questions"]:
                if question["id"] not in self.workflow_state["intake_data"]:
                    questions.append({
                        "section": section["section_name"],
                        "section_id": section_id,
                        **question
                    })
                    if len(questions) >= count:
                        return questions

        return questions

    def process_intake_answer(self, question_id: str, answer: Any) -> Dict[str, Any]:
        """Process an answer to an intake question"""
        # Find the question
        question_info = None
        section_id = None

        for sid, section in INTAKE_FORM_SECTIONS.items():
            for q in section["questions"]:
                if q["id"] == question_id:
                    question_info = q
                    section_id = sid
                    break
            if question_info:
                break

        if not question_info:
            return {"success": False, "error": f"Unknown question: {question_id}"}

        # Validate answer
        if question_info.get("required") and not answer:
            return {"success": False, "error": "This question is required"}

        # Store answer
        self.workflow_state["intake_data"][question_id] = answer

        # Check if section is complete
        section_questions = [q["id"] for q in INTAKE_FORM_SECTIONS[section_id]["questions"]]
        section_complete = all(q in self.workflow_state["intake_data"] for q in section_questions
                               if next((x for x in INTAKE_FORM_SECTIONS[section_id]["questions"] if x["id"] == q), {}).get("required", False))

        if section_complete and section_id not in self.workflow_state["completed_sections"]:
            self.workflow_state["completed_sections"].append(section_id)

        # Check if all intake is complete
        all_complete = len(self.workflow_state["completed_sections"]) == len(INTAKE_FORM_SECTIONS)
        if all_complete:
            self.workflow_state["status"] = SchedulingStatus.INTAKE_COMPLETE
        else:
            self.workflow_state["status"] = SchedulingStatus.INTAKE_IN_PROGRESS

        return {
            "success": True,
            "question_id": question_id,
            "section_complete": section_complete,
            "all_intake_complete": all_complete,
            "progress": self.get_intake_progress()
        }

    def bulk_process_intake(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Process multiple intake answers at once (e.g., from FHIR data)"""
        results = []
        for question_id, answer in answers.items():
            result = self.process_intake_answer(question_id, answer)
            results.append(result)

        return {
            "processed": len(results),
            "success_count": sum(1 for r in results if r.get("success")),
            "progress": self.get_intake_progress()
        }

    def verify_insurance(self) -> Dict[str, Any]:
        """Verify insurance coverage for colonoscopy"""
        insurance_data = {
            "provider": self.workflow_state["intake_data"].get("insurance_provider"),
            "member_id": self.workflow_state["intake_data"].get("member_id"),
            "group_number": self.workflow_state["intake_data"].get("group_number")
        }

        if not insurance_data["provider"] or not insurance_data["member_id"]:
            return {
                "verified": False,
                "error": "Insurance information incomplete",
                "missing_fields": ["insurance_provider", "member_id"]
            }

        # Simulate insurance verification
        # In production, this would call real insurance eligibility APIs
        referral_reason = self.workflow_state["intake_data"].get("referral_reason", "")
        is_screening = "screening" in referral_reason.lower() or "routine" in referral_reason.lower()

        self.workflow_state["insurance_verified"] = True
        self.workflow_state["status"] = SchedulingStatus.INSURANCE_VERIFIED

        return {
            "verified": True,
            "insurance_provider": insurance_data["provider"],
            "member_id": insurance_data["member_id"],
            "coverage_details": {
                "colonoscopy_covered": True,
                "screening_vs_diagnostic": "Screening" if is_screening else "Diagnostic",
                "prior_auth_required": not is_screening,
                "prior_auth_status": "Not Required" if is_screening else "Pending",
                "estimated_patient_cost": "$0" if is_screening else "Subject to deductible",
                "facility_network": "In-Network",
                "anesthesia_covered": True
            },
            "notes": [
                "Preventive screening colonoscopies are typically covered at 100% with no cost-sharing",
                "If polyps are found and removed, the procedure may be reclassified as diagnostic"
            ] if is_screening else [
                "Diagnostic colonoscopies are subject to your deductible and coinsurance",
                "Prior authorization may be required - we will handle this for you"
            ]
        }

    def verify_referral(self) -> Dict[str, Any]:
        """Verify referral from PCP"""
        referral_data = {
            "physician": self.workflow_state["intake_data"].get("referring_physician"),
            "practice": self.workflow_state["intake_data"].get("referring_practice"),
            "phone": self.workflow_state["intake_data"].get("referring_phone"),
            "reason": self.workflow_state["intake_data"].get("referral_reason"),
            "date": self.workflow_state["intake_data"].get("referral_date")
        }

        if not referral_data["physician"]:
            return {
                "verified": False,
                "error": "Referral information incomplete",
                "missing_fields": ["referring_physician"]
            }

        self.workflow_state["referral_verified"] = True

        return {
            "verified": True,
            "referral_details": referral_data,
            "referral_status": "Active",
            "referral_valid_until": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
            "notes": "Referral confirmed. Valid for 90 days."
        }

    def search_appointments(self, preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search for available colonoscopy appointments"""
        self.workflow_state["status"] = SchedulingStatus.SEARCHING_APPOINTMENTS

        prefs = preferences or {}
        preferred_dates = prefs.get("preferred_dates") or self.workflow_state["intake_data"].get("preferred_dates", "")
        preferred_location = prefs.get("preferred_location") or self.workflow_state["intake_data"].get("preferred_location", "")

        # Simulate appointment search
        # In production, this would integrate with clinic scheduling systems
        base_date = datetime.now() + timedelta(days=14)  # Appointments typically 2+ weeks out

        appointments = []
        for i in range(5):
            appt_date = base_date + timedelta(days=i * 2 + (i % 3))
            for hour in [7, 9, 11, 14]:
                appointments.append({
                    "id": f"APT-{appt_date.strftime('%Y%m%d')}-{hour:02d}00",
                    "datetime": appt_date.replace(hour=hour, minute=0).isoformat(),
                    "date_display": appt_date.strftime("%A, %B %d, %Y"),
                    "time_display": f"{hour}:00 AM" if hour < 12 else f"{hour-12 if hour > 12 else 12}:00 PM",
                    "facility": "GI Specialists of Metro",
                    "address": "123 Medical Center Drive, Suite 400",
                    "provider": "Dr. Sarah Chen, MD - Gastroenterology",
                    "procedure_type": "Screening Colonoscopy",
                    "duration_minutes": 60,
                    "arrival_time": f"{hour-1}:30 AM" if hour < 12 else f"{hour-13 if hour > 13 else 11}:30 {'AM' if hour <= 13 else 'PM'}"
                })

        self.workflow_state["available_appointments"] = appointments[:8]  # Return top 8

        return {
            "success": True,
            "appointments_found": len(appointments),
            "appointments": self.workflow_state["available_appointments"],
            "search_criteria": {
                "preferred_dates": preferred_dates,
                "preferred_location": preferred_location or "Any"
            },
            "next_step": "Select an appointment from the list"
        }

    def select_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Select and confirm an appointment"""
        appointment = next(
            (a for a in self.workflow_state["available_appointments"] if a["id"] == appointment_id),
            None
        )

        if not appointment:
            return {
                "success": False,
                "error": f"Appointment {appointment_id} not found"
            }

        # Verify all requirements are met
        if not self.workflow_state["insurance_verified"]:
            return {
                "success": False,
                "error": "Insurance must be verified before scheduling",
                "action_required": "verify_insurance"
            }

        has_driver = self.workflow_state["intake_data"].get("transportation")
        if not has_driver:
            return {
                "success": False,
                "error": "You must have a driver arranged to schedule the procedure",
                "action_required": "confirm_transportation"
            }

        self.workflow_state["selected_appointment"] = appointment
        self.workflow_state["status"] = SchedulingStatus.APPOINTMENT_CONFIRMED

        return {
            "success": True,
            "appointment_confirmed": True,
            "confirmation_number": f"COL-{datetime.now().strftime('%Y%m%d')}-{appointment_id[-4:]}",
            "appointment_details": appointment,
            "patient_name": self.workflow_state["intake_data"].get("full_name"),
            "driver_name": self.workflow_state["intake_data"].get("driver_name"),
            "important_reminders": [
                f"Arrive at {appointment['arrival_time']} (30 minutes before procedure)",
                "Bring photo ID and insurance card",
                "Your driver must stay at the facility during the procedure",
                "Do not eat solid food after midnight the day before",
                "Prep instructions will be provided"
            ],
            "next_step": "get_prep_instructions"
        }

    def get_prep_instructions(self) -> Dict[str, Any]:
        """Get colonoscopy preparation instructions"""
        if not self.workflow_state["selected_appointment"]:
            return {
                "success": False,
                "error": "No appointment scheduled yet"
            }

        appointment = self.workflow_state["selected_appointment"]
        appt_date = datetime.fromisoformat(appointment["datetime"])

        # Customize prep instructions with dates
        customized_prep = PREP_INSTRUCTIONS.copy()
        customized_prep["procedure_date"] = appt_date.strftime("%A, %B %d, %Y")
        customized_prep["procedure_time"] = appointment["time_display"]
        customized_prep["arrival_time"] = appointment["arrival_time"]

        # Calculate prep timeline dates
        prep_dates = {}
        for item in customized_prep["prep_timeline"]:
            if "7 days" in item["timing"]:
                prep_dates[item["timing"]] = (appt_date - timedelta(days=7)).strftime("%A, %B %d")
            elif "5 days" in item["timing"]:
                prep_dates[item["timing"]] = (appt_date - timedelta(days=5)).strftime("%A, %B %d")
            elif "1 day" in item["timing"]:
                prep_dates[item["timing"]] = (appt_date - timedelta(days=1)).strftime("%A, %B %d")
            elif "Day of" in item["timing"]:
                prep_dates[item["timing"]] = appt_date.strftime("%A, %B %d")

        customized_prep["prep_dates"] = prep_dates

        # Add medication-specific instructions
        takes_blood_thinners = self.workflow_state["intake_data"].get("blood_thinners")
        takes_diabetes_meds = self.workflow_state["intake_data"].get("diabetes_meds")

        customized_prep["medication_instructions"] = []
        if takes_blood_thinners:
            customized_prep["medication_instructions"].append({
                "warning": "BLOOD THINNERS",
                "instruction": "Contact your prescribing physician about when to stop blood thinners before the procedure. This is typically 3-7 days before depending on the medication."
            })
        if takes_diabetes_meds:
            customized_prep["medication_instructions"].append({
                "warning": "DIABETES MEDICATIONS",
                "instruction": "Do NOT take diabetes medications the morning of your procedure. Monitor blood sugar closely during prep. If blood sugar drops below 70, drink regular (non-diet) clear soda or juice."
            })

        self.workflow_state["prep_instructions_sent"] = True
        self.workflow_state["status"] = SchedulingStatus.PREP_INSTRUCTIONS_SENT

        return {
            "success": True,
            "prep_instructions": customized_prep,
            "appointment": appointment,
            "patient_name": self.workflow_state["intake_data"].get("full_name")
        }

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get complete workflow status"""
        return {
            "agent": self.agent_id,
            "status": self.workflow_state["status"].value,
            "intake_progress": self.get_intake_progress(),
            "insurance_verified": self.workflow_state["insurance_verified"],
            "referral_verified": self.workflow_state["referral_verified"],
            "appointment_scheduled": self.workflow_state["selected_appointment"] is not None,
            "prep_instructions_sent": self.workflow_state["prep_instructions_sent"],
            "selected_appointment": self.workflow_state["selected_appointment"],
            "timestamp": datetime.now().isoformat()
        }

    def _extract_answers_from_message(self, message: str, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract answers from a natural language message based on pending questions"""
        extracted = {}
        message_lower = message.lower().strip()
        parts = message.split()

        # Try to match answers to questions
        for q in questions:
            qid = q["id"]
            qtype = q.get("type", "text")

            # Date detection (various formats)
            if qtype == "date" or qid in ["dob", "referral_date", "previous_colonoscopy_date"]:
                import re
                # Match patterns like 05/22/1975, 1975-05-22, May 22 1975, etc.
                date_patterns = [
                    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or MM-DD-YYYY
                    r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',    # YYYY-MM-DD
                    r'\b(\w+\s+\d{1,2},?\s+\d{4})\b',        # Month DD, YYYY
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, message)
                    if match:
                        extracted[qid] = match.group(1)
                        break

            # Sex/gender detection
            elif qid == "sex":
                if "male" in message_lower and "female" not in message_lower:
                    extracted[qid] = "Male"
                elif "female" in message_lower:
                    extracted[qid] = "Female"
                elif message_lower in ["m", "f"]:
                    extracted[qid] = "Male" if message_lower == "m" else "Female"

            # Boolean detection
            elif qtype == "boolean":
                if any(word in message_lower for word in ["yes", "yeah", "yep", "true", "correct", "affirmative"]):
                    extracted[qid] = True
                elif any(word in message_lower for word in ["no", "nope", "false", "negative", "none", "n/a"]):
                    extracted[qid] = False

            # Name detection (for full_name question)
            elif qid == "full_name":
                # Look for name patterns - typically 2-4 words at start of message
                import re
                # Remove date and other obvious non-name content
                name_text = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '', message)
                name_text = re.sub(r'\b(male|female|m|f)\b', '', name_text, flags=re.IGNORECASE)
                name_text = name_text.strip()
                # Extract capitalized words or words that look like names
                name_parts = [p for p in name_text.split() if p and not p.isdigit()]
                if name_parts:
                    extracted[qid] = ' '.join(name_parts[:4])  # Max 4 words for name

        return extracted

    def process_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a natural language message and determine appropriate action"""
        message_lower = message.lower()

        # Track conversation
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # If intake is in progress, try to extract answers from the message
        if self.workflow_state["status"] == SchedulingStatus.INTAKE_IN_PROGRESS:
            pending_questions = self.get_next_questions(5)
            if pending_questions:
                extracted = self._extract_answers_from_message(message, pending_questions)
                if extracted:
                    # Store the extracted answers
                    for qid, answer in extracted.items():
                        self.process_intake_answer(qid, answer)

        # Determine intent and respond
        response = None

        if any(word in message_lower for word in ["schedule", "book", "appointment", "colonoscopy"]):
            if self.workflow_state["status"] == SchedulingStatus.INITIATED:
                # Start intake process
                self.workflow_state["status"] = SchedulingStatus.INTAKE_IN_PROGRESS
                next_questions = self.get_next_questions(3)
                response = {
                    "action": "start_intake",
                    "message": "I'll help you schedule your colonoscopy. First, I need to collect some information. Let's start with your basic details.",
                    "next_questions": next_questions,
                    "progress": self.get_intake_progress()
                }
            elif self.workflow_state["status"] in [SchedulingStatus.INTAKE_COMPLETE, SchedulingStatus.INSURANCE_VERIFIED]:
                # Ready to search appointments
                response = self.search_appointments()
                response["message"] = "Here are available appointments. Which one works best for you?"

        elif any(word in message_lower for word in ["insurance", "coverage", "verify"]):
            response = self.verify_insurance()
            response["message"] = "I've verified your insurance coverage. Here are the details."

        elif any(word in message_lower for word in ["referral", "doctor", "pcp"]):
            response = self.verify_referral()
            response["message"] = "I've verified your referral from your primary care physician."

        elif any(word in message_lower for word in ["prep", "preparation", "instructions", "ready"]):
            response = self.get_prep_instructions()
            response["message"] = "Here are your colonoscopy preparation instructions. Please follow them carefully."

        elif any(word in message_lower for word in ["status", "progress", "where"]):
            response = self.get_workflow_status()
            response["message"] = f"Your scheduling status: {self.workflow_state['status'].value}"

        else:
            # Default: check if intake is in progress and provide next questions
            if self.workflow_state["status"] == SchedulingStatus.INTAKE_IN_PROGRESS:
                # Check what was extracted from the message
                pending_questions = self.get_next_questions(5)
                extracted = self._extract_answers_from_message(message, pending_questions) if pending_questions else {}

                # Build acknowledgment of captured data
                captured_items = []
                intake_data = self.workflow_state["intake_data"]
                if intake_data.get("full_name"):
                    captured_items.append(f"Name: {intake_data['full_name']}")
                if intake_data.get("dob"):
                    captured_items.append(f"DOB: {intake_data['dob']}")
                if intake_data.get("sex"):
                    captured_items.append(f"Sex: {intake_data['sex']}")

                next_questions = self.get_next_questions(3)
                if next_questions:
                    progress = self.get_intake_progress()
                    if captured_items:
                        ack_msg = f"Got it! I've recorded: {', '.join(captured_items)}. "
                    else:
                        ack_msg = ""

                    response = {
                        "action": "continue_intake",
                        "message": f"{ack_msg}Now let's continue with the next questions ({progress['answered_questions']}/{progress['total_questions']} complete):",
                        "next_questions": next_questions,
                        "progress": progress,
                        "captured_data": {k: v for k, v in intake_data.items() if v} if captured_items else None
                    }
                else:
                    response = {
                        "action": "intake_complete",
                        "message": "Great! Your intake form is complete. Let me verify your insurance and find available appointments.",
                        "progress": self.get_intake_progress()
                    }
            else:
                response = {
                    "action": "help",
                    "message": "I can help you with: scheduling a colonoscopy, verifying insurance, checking your referral, getting prep instructions, or checking your scheduling status. What would you like to do?",
                    "status": self.get_workflow_status()
                }

        # Track response
        self.conversation_history.append({
            "role": "agent",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    def execute_full_workflow(self, patient_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the complete scheduling workflow"""
        workflow_results = {
            "workflow": "colonoscopy_scheduling",
            "started": datetime.now().isoformat(),
            "steps": []
        }

        # Step 1: Process intake data if provided
        if patient_data:
            intake_result = self.bulk_process_intake(patient_data)
            workflow_results["steps"].append({
                "step": 1,
                "action": "process_intake",
                "status": "complete",
                "details": intake_result
            })

        # Step 2: Verify insurance
        insurance_result = self.verify_insurance()
        workflow_results["steps"].append({
            "step": 2,
            "action": "verify_insurance",
            "status": "verified" if insurance_result.get("verified") else "failed",
            "details": insurance_result
        })

        # Step 3: Verify referral
        referral_result = self.verify_referral()
        workflow_results["steps"].append({
            "step": 3,
            "action": "verify_referral",
            "status": "verified" if referral_result.get("verified") else "failed",
            "details": referral_result
        })

        # Step 4: Search appointments
        appointment_result = self.search_appointments()
        workflow_results["steps"].append({
            "step": 4,
            "action": "search_appointments",
            "status": "found" if appointment_result.get("appointments") else "none_available",
            "details": appointment_result
        })

        workflow_results["status"] = "ready_to_schedule"
        workflow_results["completed"] = datetime.now().isoformat()
        workflow_results["next_step"] = "Select an appointment and confirm"
        workflow_results["agent"] = self.agent_id

        return workflow_results

    # =========================================================================
    # Voice/Telephony Capabilities
    # =========================================================================

    def get_voice_greeting(self, direction: str = "inbound") -> str:
        """
        Get voice-optimized greeting for phone calls.

        Args:
            direction: "inbound" for patient calling in, "outbound" for agent calling out

        Returns:
            Greeting text optimized for text-to-speech
        """
        if direction == "outbound":
            return (
                "Hello, this is the automated scheduling assistant calling from "
                "G I Specialists. I'm calling to help schedule a colonoscopy appointment. "
                "Is this a good time to talk?"
            )
        else:
            return (
                "Hello, thank you for calling G I Specialists scheduling. "
                "I'm an automated assistant and I can help you schedule your "
                "colonoscopy appointment. To get started, may I have your full name please?"
            )

    def process_voice_message(self, text: str, call_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a message from a phone call.

        Optimized for voice interactions with shorter responses and clearer questions.

        Args:
            text: Transcribed speech from the caller
            call_context: Call metadata (call_id, caller, etc.)

        Returns:
            Response dict with voice-optimized message
        """
        # Use standard message processing
        result = self.process_message(text, call_context)

        # Optimize the message for voice
        if result.get("message"):
            result["message"] = self._optimize_for_voice(result["message"])

        # Add voice-specific response formatting
        if result.get("next_questions"):
            # For voice, ask one question at a time
            questions = result["next_questions"]
            if questions:
                first_q = questions[0]
                result["voice_prompt"] = f"Next question: {first_q.get('question', '')}"
                result["pending_questions"] = questions[1:] if len(questions) > 1 else []

        # Check if we should trigger an outbound call (e.g., to clinic)
        if result.get("action") == "intake_complete" and self.workflow_state["insurance_verified"]:
            # Patient intake is done, could trigger call to clinic
            result["trigger_outbound_call"] = {
                "purpose": "schedule_with_clinic",
                "patient_data": self.workflow_state["intake_data"],
                "target": "clinic"  # Would be actual clinic phone in production
            }

        return result

    def _optimize_for_voice(self, text: str) -> str:
        """
        Make text more suitable for text-to-speech playback.

        - Shorten long responses
        - Expand abbreviations
        - Remove markdown formatting
        - Improve pronunciation hints
        """
        if not text:
            return text

        # Limit length for voice (shorter is better for phone)
        if len(text) > 250:
            sentences = text.split('. ')
            text = '. '.join(sentences[:3])
            if not text.endswith('.'):
                text += '.'

        # Replace abbreviations for better TTS pronunciation
        replacements = {
            "DOB": "date of birth",
            "PCP": "primary care provider",
            "GI": "G I",
            "ID": "I D",
            "Dr.": "Doctor",
            "Appt": "Appointment",
            "appt": "appointment",
            "w/": "with",
            "vs": "versus",
            "&": "and",
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "and so on",
            "approx.": "approximately",
            "info": "information",
            "amt": "amount",
        }
        for abbr, full in replacements.items():
            text = text.replace(abbr, full)

        # Remove markdown formatting
        text = text.replace("**", "")
        text = text.replace("*", "")
        text = text.replace("`", "")
        text = text.replace("#", "")

        # Remove bullet points and list markers
        import re
        text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)

        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def get_voice_prompt_for_question(self, question_id: str) -> str:
        """
        Get a voice-optimized prompt for a specific question.

        Args:
            question_id: ID of the intake question

        Returns:
            Voice-friendly prompt text
        """
        # Find the question
        for section in INTAKE_FORM_SECTIONS.values():
            for q in section["questions"]:
                if q["id"] == question_id:
                    base_question = q["question"]

                    # Add context for certain question types
                    if q.get("type") == "date":
                        return f"{base_question}? You can say it like month day year."
                    elif q.get("type") == "boolean":
                        return f"{base_question}? Please answer yes or no."
                    elif q.get("type") == "choice" and q.get("options"):
                        options = ", or ".join(q["options"][:3])
                        return f"{base_question}? Options include {options}."
                    else:
                        return f"{base_question}?"

        return "Could you please provide that information?"

    def get_voice_summary(self) -> str:
        """
        Get a voice-friendly summary of collected information.

        Useful for confirmation before scheduling.
        """
        data = self.workflow_state["intake_data"]
        progress = self.get_intake_progress()

        if progress["answered_questions"] == 0:
            return "I don't have any information recorded yet."

        summary_parts = []

        if data.get("full_name"):
            summary_parts.append(f"Your name is {data['full_name']}")

        if data.get("dob"):
            summary_parts.append(f"date of birth {data['dob']}")

        if data.get("insurance_provider"):
            summary_parts.append(f"insured by {data['insurance_provider']}")

        if data.get("referring_physician"):
            summary_parts.append(f"referred by Doctor {data['referring_physician']}")

        if self.workflow_state.get("selected_appointment"):
            appt = self.workflow_state["selected_appointment"]
            summary_parts.append(
                f"scheduled for {appt.get('date_display', 'the selected date')} "
                f"at {appt.get('time_display', 'the selected time')}"
            )

        if summary_parts:
            return "Here's what I have: " + ", ".join(summary_parts) + "."
        else:
            return "I have some information recorded but need a few more details."

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "problem_solved": "Eliminates long phone queues and complex 40+ question intake forms for colonoscopy scheduling",
            "capabilities": [
                "intake_form_processing",
                "insurance_verification",
                "referral_verification",
                "appointment_search",
                "appointment_booking",
                "prep_instructions_delivery",
                "voice_phone_calls"
            ],
            "protocols_supported": ["a2a", "mcp", "voice"],
            "methods": [
                "process_message",
                "process_voice_message",
                "bulk_process_intake",
                "verify_insurance",
                "verify_referral",
                "search_appointments",
                "select_appointment",
                "get_prep_instructions",
                "execute_full_workflow",
                "get_workflow_status",
                "get_voice_greeting",
                "get_voice_summary"
            ],
            "intake_sections": list(INTAKE_FORM_SECTIONS.keys()),
            "total_intake_questions": sum(len(s["questions"]) for s in INTAKE_FORM_SECTIONS.values()),
            "voice_enabled": True
        }


# Factory function
def create_colonoscopy_scheduler_agent() -> ColonoscopySchedulerAgent:
    """Create a Colonoscopy Scheduling Agent instance"""
    return ColonoscopySchedulerAgent()
