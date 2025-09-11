"""
BCS Guidelines engine for autonomous evaluation.
"""
from typing import Dict, Any, List
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


# Default BCS guidelines - sites should customize these
DEFAULT_BCS_GUIDELINES = {
    "ageRangeYears": [50, 74],
    "screeningIntervalMonths": 24,
    "sexRequired": "female",
    "noHistoryMeans": "needs-more-info",
    "rationales": {
        "eligible": "Within screening age and interval exceeded; recommend screening.",
        "needs-more-info": "Insufficient history; confirm last mammogram date or documentation.",
        "ineligible": "Outside configured age range or criteria not met."
    },
    "codingHints": {
        "mammogramProcedures": [
            {"system": "http://www.ama-assn.org/go/cpt", "code": "77067"},
            {"system": "http://loinc.org", "code": "24606-6"}
        ]
    },
    "meta": {
        "name": "Default BCS Guidelines",
        "version": "1.0",
        "description": "Example breast cancer screening eligibility guidelines. Sites should customize these based on their clinical policies.",
        "disclaimer": "These are example defaults for demonstration purposes. Clinical sites must implement their own evidence-based guidelines."
    }
}


class GuidelinesEvaluator:
    """Evaluates patient facts against BCS guidelines."""
    
    def __init__(self, guidelines: Dict[str, Any] = None):
        self.guidelines = guidelines or DEFAULT_BCS_GUIDELINES.copy()
    
    def evaluate(self, facts: Dict[str, Any], measurement_date: str = None) -> Dict[str, Any]:
        """
        Evaluate patient facts against guidelines.
        
        Args:
            facts: Minimal facts dict with sex, birthDate, last_mammogram
            measurement_date: Date of evaluation (default: today)
            
        Returns:
            Evaluation result with decision, rationale, confidence, details
        """
        if measurement_date is None:
            measurement_date = date.today().isoformat()
        
        # Convert measurement_date to date object
        eval_date = datetime.fromisoformat(measurement_date).date()
        
        result = {
            "decision": "needs-more-info",
            "rationale": "Evaluation incomplete",
            "confidence": 0.5,
            "details": {
                "age_check": None,
                "sex_check": None,
                "interval_check": None,
                "evaluation_date": measurement_date
            },
            "guidelines_version": self.guidelines.get("meta", {}).get("version", "unknown")
        }
        
        # Check sex requirement
        patient_sex = facts.get("sex")
        required_sex = self.guidelines.get("sexRequired")
        
        if not patient_sex:
            result["decision"] = "needs-more-info"
            result["rationale"] = "Patient sex not available"
            result["details"]["sex_check"] = "missing"
            return result
        
        if patient_sex != required_sex:
            result["decision"] = "ineligible"
            result["rationale"] = f"Patient sex ({patient_sex}) does not meet requirement ({required_sex})"
            result["details"]["sex_check"] = "failed"
            result["confidence"] = 0.9
            return result
        
        result["details"]["sex_check"] = "passed"
        
        # Check age requirement
        birth_date = facts.get("birthDate")
        if not birth_date:
            result["decision"] = "needs-more-info"
            result["rationale"] = "Patient birth date not available"
            result["details"]["age_check"] = "missing"
            return result
        
        try:
            birth_date_obj = datetime.fromisoformat(birth_date).date()
            age = eval_date.year - birth_date_obj.year - ((eval_date.month, eval_date.day) < (birth_date_obj.month, birth_date_obj.day))
            
            age_range = self.guidelines.get("ageRangeYears", [50, 74])
            min_age, max_age = age_range[0], age_range[1]
            
            result["details"]["age_check"] = {
                "patient_age": age,
                "required_range": age_range,
                "status": "passed" if min_age <= age <= max_age else "failed"
            }
            
            if not (min_age <= age <= max_age):
                result["decision"] = "ineligible"
                result["rationale"] = f"Patient age ({age}) outside screening range ({min_age}-{max_age})"
                result["confidence"] = 0.9
                return result
                
        except ValueError:
            result["decision"] = "needs-more-info"
            result["rationale"] = f"Invalid birth date format: {birth_date}"
            result["details"]["age_check"] = "invalid"
            return result
        
        # Check mammogram interval
        last_mammogram = facts.get("last_mammogram")
        if not last_mammogram:
            no_history_action = self.guidelines.get("noHistoryMeans", "needs-more-info")
            result["decision"] = no_history_action
            result["rationale"] = self.guidelines["rationales"].get(no_history_action, "No mammogram history available")
            result["details"]["interval_check"] = "no_history"
            result["confidence"] = 0.7
            return result
        
        try:
            last_mammo_date = datetime.fromisoformat(last_mammogram).date()
            interval_months = self.guidelines.get("screeningIntervalMonths", 24)
            
            # Calculate cutoff date (evaluation date minus interval)
            cutoff_date = eval_date - relativedelta(months=interval_months)
            
            result["details"]["interval_check"] = {
                "last_mammogram": last_mammogram,
                "cutoff_date": cutoff_date.isoformat(),
                "months_since": self._months_between(last_mammo_date, eval_date),
                "interval_required": interval_months,
                "status": "passed" if last_mammo_date <= cutoff_date else "failed"
            }
            
            if last_mammo_date > cutoff_date:
                result["decision"] = "ineligible"
                result["rationale"] = f"Recent mammogram ({last_mammogram}) within {interval_months} month interval"
                result["confidence"] = 0.8
                return result
                
        except ValueError:
            result["decision"] = "needs-more-info"
            result["rationale"] = f"Invalid mammogram date format: {last_mammogram}"
            result["details"]["interval_check"] = "invalid"
            return result
        
        # All checks passed
        result["decision"] = "eligible"
        result["rationale"] = self.guidelines["rationales"].get("eligible", "Patient meets all screening criteria")
        result["confidence"] = 0.95
        
        return result
    
    def _months_between(self, start_date: date, end_date: date) -> int:
        """Calculate months between two dates."""
        return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    
    def get_guidelines(self) -> Dict[str, Any]:
        """Get current guidelines configuration."""
        return self.guidelines.copy()
    
    def update_guidelines(self, new_guidelines: Dict[str, Any]) -> None:
        """Update guidelines configuration with validation."""
        # Basic validation
        required_fields = ["ageRangeYears", "screeningIntervalMonths", "sexRequired", "rationales"]
        for field in required_fields:
            if field not in new_guidelines:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate age range
        age_range = new_guidelines["ageRangeYears"]
        if not isinstance(age_range, list) or len(age_range) != 2:
            raise ValueError("ageRangeYears must be a list of two integers")
        
        if not all(isinstance(x, int) and 0 <= x <= 120 for x in age_range):
            raise ValueError("Age range values must be integers between 0 and 120")
        
        if age_range[0] >= age_range[1]:
            raise ValueError("Minimum age must be less than maximum age")
        
        # Validate interval
        interval = new_guidelines["screeningIntervalMonths"]
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("screeningIntervalMonths must be a positive integer")
        
        # Validate sex requirement
        sex_required = new_guidelines["sexRequired"]
        if sex_required not in ["male", "female"]:
            raise ValueError("sexRequired must be 'male' or 'female'")
        
        # Validate rationales
        rationales = new_guidelines["rationales"]
        required_rationales = ["eligible", "needs-more-info", "ineligible"]
        for rationale in required_rationales:
            if rationale not in rationales:
                raise ValueError(f"Missing required rationale: {rationale}")
        
        self.guidelines = new_guidelines


def create_custom_guidelines(
    age_range: List[int] = [50, 74],
    interval_months: int = 24,
    sex_required: str = "female"
) -> Dict[str, Any]:
    """Create custom guidelines with specified parameters."""
    guidelines = DEFAULT_BCS_GUIDELINES.copy()
    guidelines["ageRangeYears"] = age_range
    guidelines["screeningIntervalMonths"] = interval_months
    guidelines["sexRequired"] = sex_required
    
    # Update meta information
    guidelines["meta"] = {
        "name": "Custom BCS Guidelines",
        "version": "1.0-custom",
        "description": f"Custom guidelines: age {age_range[0]}-{age_range[1]}, {interval_months} month interval, {sex_required} only",
        "created": datetime.now().isoformat()
    }
    
    return guidelines


def evaluate_test_cases(guidelines: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Evaluate test cases against guidelines."""
    evaluator = GuidelinesEvaluator(guidelines)
    
    test_cases = [
        {
            "name": "Eligible-55F-OldMammo",
            "facts": {"sex": "female", "birthDate": "1969-08-10", "last_mammogram": "2022-01-15"},
            "expected": "eligible"
        },
        {
            "name": "Needs-Info-NoHistory", 
            "facts": {"sex": "female", "birthDate": "1964-03-15", "last_mammogram": None},
            "expected": "needs-more-info"
        },
        {
            "name": "Ineligible-TooYoung",
            "facts": {"sex": "female", "birthDate": "1984-06-20", "last_mammogram": "2022-06-01"},
            "expected": "ineligible"
        },
        {
            "name": "Ineligible-RecentMammo",
            "facts": {"sex": "female", "birthDate": "1969-08-10", "last_mammogram": "2024-01-01"},
            "expected": "ineligible"
        }
    ]
    
    results = []
    for case in test_cases:
        evaluation = evaluator.evaluate(case["facts"])
        result = {
            "test_name": case["name"],
            "expected": case["expected"],
            "actual": evaluation["decision"],
            "passed": evaluation["decision"] == case["expected"],
            "confidence": evaluation["confidence"],
            "rationale": evaluation["rationale"],
            "details": evaluation["details"]
        }
        results.append(result)
    
    return results