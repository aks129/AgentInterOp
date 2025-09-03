import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class BCSDEligibilityChecker:
    """BCSE (Benefits Coverage Support Eligibility) Checker"""
    
    def __init__(self):
        self.eligibility_rules = self._initialize_rules()
        logger.info("BCSE Eligibility Checker initialized")
    
    def _initialize_rules(self) -> Dict[str, Any]:
        """Initialize BCSE eligibility rules"""
        return {
            "age_requirements": {
                "minimum_age": 18,
                "maximum_age": 65
            },
            "income_thresholds": {
                "individual": 35000,
                "family_of_2": 47000,
                "family_of_3": 59000,
                "family_of_4": 71000
            },
            "residency_requirements": {
                "required": True,
                "valid_states": ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
            },
            "employment_status": {
                "eligible_statuses": ["unemployed", "part_time", "seasonal", "student"]
            },
            "medical_conditions": {
                "chronic_conditions_eligible": True,
                "disability_eligible": True
            }
        }
    
    def check_eligibility(self, patient_data: Dict[str, Any], benefit_type: str = "bcse") -> Dict[str, Any]:
        """Check patient eligibility for BCSE benefits"""
        logger.info(f"Checking eligibility for patient: {patient_data.get('id', 'unknown')}")
        
        criteria_checks = {}
        
        # Age eligibility
        criteria_checks["age"] = self._check_age_eligibility(patient_data)
        
        # Income eligibility
        criteria_checks["income"] = self._check_income_eligibility(patient_data)
        
        # Residency eligibility
        criteria_checks["residency"] = self._check_residency_eligibility(patient_data)
        
        # Employment status
        criteria_checks["employment"] = self._check_employment_eligibility(patient_data)
        
        # Medical conditions
        criteria_checks["medical"] = self._check_medical_eligibility(patient_data)
        
        # Overall eligibility determination
        eligible = self._determine_overall_eligibility(criteria_checks)
        
        result = {
            "patient_id": patient_data.get("id", "unknown"),
            "benefit_type": benefit_type,
            "eligible": eligible,
            "criteria_met": criteria_checks,
            "eligibility_score": self._calculate_eligibility_score(criteria_checks),
            "checked_at": datetime.now().isoformat(),
            "checker": "BCSDEligibilityChecker"
        }
        
        if eligible:
            result["next_steps"] = self._get_approval_next_steps()
        else:
            result["rejection_reasons"] = self._get_rejection_reasons(criteria_checks)
        
        return result
    
    def _check_age_eligibility(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check age eligibility criteria"""
        birth_date_str = patient_data.get("birth_date", "")
        
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            min_age = self.eligibility_rules["age_requirements"]["minimum_age"]
            max_age = self.eligibility_rules["age_requirements"]["maximum_age"]
            
            eligible = min_age <= age <= max_age
            
            return {
                "eligible": eligible,
                "current_age": age,
                "required_range": f"{min_age}-{max_age}",
                "details": f"Patient is {age} years old"
            }
        
        except Exception as e:
            logger.error(f"Error checking age eligibility: {str(e)}")
            return {
                "eligible": False,
                "error": f"Could not determine age: {str(e)}",
                "details": "Invalid or missing birth date"
            }
    
    def _check_income_eligibility(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check income eligibility criteria"""
        annual_income = patient_data.get("annual_income", 0)
        family_size = patient_data.get("family_size", 1)
        
        # Determine income threshold based on family size
        thresholds = self.eligibility_rules["income_thresholds"]
        
        if family_size == 1:
            threshold = thresholds["individual"]
        elif family_size == 2:
            threshold = thresholds["family_of_2"]
        elif family_size == 3:
            threshold = thresholds["family_of_3"]
        elif family_size >= 4:
            threshold = thresholds["family_of_4"]
        else:
            threshold = thresholds["individual"]
        
        eligible = annual_income <= threshold
        
        return {
            "eligible": eligible,
            "annual_income": annual_income,
            "family_size": family_size,
            "income_threshold": threshold,
            "details": f"Income ${annual_income} vs threshold ${threshold}"
        }
    
    def _check_residency_eligibility(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check residency eligibility criteria"""
        state = patient_data.get("address", {}).get("state", "")
        valid_states = self.eligibility_rules["residency_requirements"]["valid_states"]
        
        eligible = state in valid_states
        
        return {
            "eligible": eligible,
            "patient_state": state,
            "valid_states": valid_states,
            "details": f"Patient resides in {state}"
        }
    
    def _check_employment_eligibility(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check employment status eligibility"""
        employment_status = patient_data.get("employment_status", "").lower()
        eligible_statuses = self.eligibility_rules["employment_status"]["eligible_statuses"]
        
        eligible = employment_status in eligible_statuses
        
        return {
            "eligible": eligible,
            "current_status": employment_status,
            "eligible_statuses": eligible_statuses,
            "details": f"Employment status: {employment_status}"
        }
    
    def _check_medical_eligibility(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check medical condition eligibility"""
        medical_conditions = patient_data.get("medical_conditions", [])
        has_chronic_conditions = patient_data.get("chronic_conditions", False)
        has_disability = patient_data.get("disability", False)
        
        rules = self.eligibility_rules["medical_conditions"]
        
        # Check for qualifying conditions
        eligible = False
        qualifying_factors = []
        
        if has_chronic_conditions and rules["chronic_conditions_eligible"]:
            eligible = True
            qualifying_factors.append("chronic conditions")
        
        if has_disability and rules["disability_eligible"]:
            eligible = True
            qualifying_factors.append("disability")
        
        # If no specific medical conditions, still eligible for basic coverage
        if not qualifying_factors:
            eligible = True
            qualifying_factors.append("standard eligibility")
        
        return {
            "eligible": eligible,
            "has_chronic_conditions": has_chronic_conditions,
            "has_disability": has_disability,
            "qualifying_factors": qualifying_factors,
            "details": f"Medical eligibility based on: {', '.join(qualifying_factors)}"
        }
    
    def _determine_overall_eligibility(self, criteria_checks: Dict[str, Dict[str, Any]]) -> bool:
        """Determine overall eligibility based on all criteria"""
        # All criteria must be met for eligibility
        required_criteria = ["age", "income", "residency"]
        
        for criterion in required_criteria:
            if not criteria_checks.get(criterion, {}).get("eligible", False):
                return False
        
        return True
    
    def _calculate_eligibility_score(self, criteria_checks: Dict[str, Dict[str, Any]]) -> float:
        """Calculate eligibility score (0-100)"""
        total_criteria = len(criteria_checks)
        met_criteria = sum(1 for check in criteria_checks.values() if check.get("eligible", False))
        
        return round((met_criteria / total_criteria) * 100, 2) if total_criteria > 0 else 0
    
    def _get_approval_next_steps(self) -> List[str]:
        """Get next steps for approved applications"""
        return [
            "Application will be forwarded to benefits administration",
            "Expect confirmation within 5-7 business days",
            "Benefits coverage will begin within 30 days",
            "You will receive a benefits card by mail"
        ]
    
    def _get_rejection_reasons(self, criteria_checks: Dict[str, Dict[str, Any]]) -> List[str]:
        """Get rejection reasons for failed criteria"""
        reasons = []
        
        for criterion, check in criteria_checks.items():
            if not check.get("eligible", False):
                if criterion == "age":
                    reasons.append(f"Age requirement not met: {check.get('details', '')}")
                elif criterion == "income":
                    reasons.append(f"Income exceeds threshold: {check.get('details', '')}")
                elif criterion == "residency":
                    reasons.append(f"Residency requirement not met: {check.get('details', '')}")
                elif criterion == "employment":
                    reasons.append(f"Employment status not eligible: {check.get('details', '')}")
        
        return reasons
    
    def get_eligibility_rules(self) -> Dict[str, Any]:
        """Get current eligibility rules"""
        return self.eligibility_rules.copy()
    
    def update_eligibility_rules(self, new_rules: Dict[str, Any]) -> bool:
        """Update eligibility rules"""
        try:
            self.eligibility_rules.update(new_rules)
            logger.info("Eligibility rules updated")
            return True
        except Exception as e:
            logger.error(f"Error updating eligibility rules: {str(e)}")
            return False
