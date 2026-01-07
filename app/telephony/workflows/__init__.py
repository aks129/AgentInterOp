"""
Telephony Workflows - Pre-built voice call workflows.

Workflows:
- PatientSchedulingWorkflow: Handles inbound patient calls for scheduling
- ClinicSchedulingWorkflow: Agent calls clinic to schedule on behalf of patient
"""

from .patient_scheduling import PatientSchedulingWorkflow
from .clinic_scheduling import ClinicSchedulingWorkflow

__all__ = [
    "PatientSchedulingWorkflow",
    "ClinicSchedulingWorkflow",
]
