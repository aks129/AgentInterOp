"""Breast Cancer Screening guidelines evaluator"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


# Default BCS guidelines (configurable)
DEFAULT_BCS_RULES = {
    "ageRangeYears": [50, 74],
    "screeningIntervalMonths": 24,
    "sexRequired": "female",
    "rationales": {
        "eligible": "Based on AMA guidelines, you are eligible for breast cancer screening. Regular mammography is recommended for women aged 50-74 every 2 years.",
        "too_young": "You are currently below the recommended age for routine breast cancer screening (50 years). Please consult with your healthcare provider about your individual risk factors.",
        "too_old": "You are above the typical age range for routine screening (50-74 years). Please discuss with your healthcare provider about continued screening based on your health status and life expectancy.",
        "wrong_sex": "Current breast cancer screening guidelines primarily apply to biological females. Please consult with your healthcare provider for personalized recommendations.",
        "recent_screening": "You have had a recent mammogram within the recommended screening interval. Your next screening should be scheduled based on your previous results and provider recommendations.",
        "missing_info": "Additional information is needed to determine your screening eligibility. Please provide your age, sex, and date of last mammogram if applicable."
    },
    "riskFactors": {
        "family_history": {
            "description": "First-degree relative with breast/ovarian cancer",
            "adjustment": "Consider screening at age 40 or 10 years before youngest affected relative"
        },
        "genetic_mutation": {
            "description": "BRCA1/BRCA2 or other high-risk genetic mutations",
            "adjustment": "Consider annual MRI screening starting at age 25-30"
        },
        "prior_biopsy": {
            "description": "Previous breast biopsy with high-risk lesions",
            "adjustment": "May require more frequent screening"
        },
        "chest_radiation": {
            "description": "Prior chest radiation therapy",
            "adjustment": "Consider screening 8-10 years after radiation or at age 25, whichever is later"
        }
    }
}

# Global rules storage (in production, this would be in a database)
_bcs_rules = DEFAULT_BCS_RULES.copy()


def get_bcs_rules() -> Dict[str, Any]:
    """Get current BCS rules"""
    return _bcs_rules.copy()


def update_bcs_rules(rules: Dict[str, Any]) -> Dict[str, Any]:
    """Update BCS rules"""
    global _bcs_rules
    
    # Merge with existing rules
    _bcs_rules.update(rules)
    
    # Ensure required fields exist
    if "ageRangeYears" not in _bcs_rules:
        _bcs_rules["ageRangeYears"] = [50, 74]
    if "screeningIntervalMonths" not in _bcs_rules:
        _bcs_rules["screeningIntervalMonths"] = 24
    if "sexRequired" not in _bcs_rules:
        _bcs_rules["sexRequired"] = "female"
    
    return _bcs_rules.copy()


def reset_bcs_rules():
    """Reset BCS rules to defaults"""
    global _bcs_rules
    _bcs_rules = DEFAULT_BCS_RULES.copy()


def evaluate_bcs_eligibility(patient_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate BCS eligibility based on patient facts and current rules.
    
    Args:
        patient_facts: Dictionary with patient information
            - age: int
            - sex: str 
            - last_mammogram_date: str (YYYY-MM-DD)
            - risk_factors: List[str] (optional)
    
    Returns:
        {
            "decision": "eligible|needs-more-info|ineligible",
            "rationale": "Human readable explanation",
            "details": {
                "age_check": "pass|fail",
                "sex_check": "pass|fail", 
                "interval_check": "pass|fail|na",
                "risk_factors": [...],
                "next_screening_date": "YYYY-MM-DD",
                "recommendations": [...]
            },
            "confidence": 0.95
        }
    """
    rules = get_bcs_rules()
    
    result = {
        "decision": "needs-more-info",
        "rationale": rules["rationales"]["missing_info"],
        "details": {
            "age_check": "unknown",
            "sex_check": "unknown",
            "interval_check": "unknown",
            "risk_factors": [],
            "next_screening_date": None,
            "recommendations": []
        },
        "confidence": 0.5
    }
    
    # Check required information
    age = patient_facts.get("age")
    sex = patient_facts.get("sex")
    last_mammogram_date = patient_facts.get("last_mammogram_date")
    risk_factors = patient_facts.get("risk_factors", [])
    
    # Age check
    if age is not None:
        min_age, max_age = rules["ageRangeYears"]
        if age < min_age:
            result.update({
                "decision": "ineligible",
                "rationale": rules["rationales"]["too_young"],
                "confidence": 0.9
            })
            result["details"]["age_check"] = "fail"
            result["details"]["recommendations"].append(f"Routine screening typically begins at age {min_age}")
            return result
        elif age > max_age:
            result.update({
                "decision": "ineligible", 
                "rationale": rules["rationales"]["too_old"],
                "confidence": 0.7
            })
            result["details"]["age_check"] = "fail"
            result["details"]["recommendations"].append("Discuss continued screening with healthcare provider")
            return result
        else:
            result["details"]["age_check"] = "pass"
    
    # Sex check
    if sex is not None:
        if sex.lower() != rules["sexRequired"].lower():
            result.update({
                "decision": "ineligible",
                "rationale": rules["rationales"]["wrong_sex"], 
                "confidence": 0.8
            })
            result["details"]["sex_check"] = "fail"
            return result
        else:
            result["details"]["sex_check"] = "pass"
    
    # If we have age and sex, we can make a preliminary decision
    if age is not None and sex is not None:
        # Check screening interval
        if last_mammogram_date:
            days_since_last = calculate_days_since(last_mammogram_date)
            interval_months = rules["screeningIntervalMonths"]
            interval_days = interval_months * 30  # Approximate
            
            if days_since_last < interval_days:
                result.update({
                    "decision": "ineligible",
                    "rationale": rules["rationales"]["recent_screening"],
                    "confidence": 0.9
                })
                result["details"]["interval_check"] = "fail"
                
                # Calculate next screening date
                next_date = datetime.strptime(last_mammogram_date, "%Y-%m-%d") + timedelta(days=interval_days)
                result["details"]["next_screening_date"] = next_date.strftime("%Y-%m-%d")
                result["details"]["recommendations"].append(f"Next screening due: {next_date.strftime('%B %Y')}")
                return result
            else:
                result["details"]["interval_check"] = "pass"
        else:
            result["details"]["interval_check"] = "na"
        
        # If all checks pass, patient is eligible
        result.update({
            "decision": "eligible",
            "rationale": rules["rationales"]["eligible"],
            "confidence": 0.95
        })
        
        # Add risk factor considerations
        if risk_factors:
            result["details"]["risk_factors"] = risk_factors
            recommendations = []
            
            for factor in risk_factors:
                if factor in rules.get("riskFactors", {}):
                    risk_info = rules["riskFactors"][factor]
                    recommendations.append(f"{risk_info['description']}: {risk_info['adjustment']}")
            
            if recommendations:
                result["details"]["recommendations"].extend(recommendations)
                result["rationale"] += f" Note: Due to your risk factors ({', '.join(risk_factors)}), discuss modified screening recommendations with your provider."
        
        # Calculate next screening recommendation
        if not result["details"]["next_screening_date"]:
            interval_months = rules["screeningIntervalMonths"]
            if last_mammogram_date:
                last_date = datetime.strptime(last_mammogram_date, "%Y-%m-%d")
                next_date = last_date + timedelta(days=interval_months * 30)
            else:
                next_date = datetime.now() + timedelta(days=interval_months * 30)
            
            result["details"]["next_screening_date"] = next_date.strftime("%Y-%m-%d")
            result["details"]["recommendations"].append(f"Schedule next screening by {next_date.strftime('%B %Y')}")
    
    return result


def calculate_days_since(date_string: str) -> int:
    """Calculate days since a given date"""
    try:
        given_date = datetime.strptime(date_string, "%Y-%m-%d")
        today = datetime.now()
        return (today - given_date).days
    except:
        return 0


def generate_bcs_summary(evaluation: Dict[str, Any], patient_facts: Dict[str, Any]) -> str:
    """Generate a human-readable summary of BCS evaluation"""
    decision = evaluation.get("decision", "unknown")
    rationale = evaluation.get("rationale", "No evaluation available")
    details = evaluation.get("details", {})
    
    summary_parts = []
    
    # Basic info
    age = patient_facts.get("age")
    sex = patient_facts.get("sex")
    if age and sex:
        summary_parts.append(f"Patient: {age}-year-old {sex}")
    
    # Decision
    decision_emoji = {
        "eligible": "✅",
        "ineligible": "❌", 
        "needs-more-info": "ℹ️"
    }.get(decision, "❓")
    
    summary_parts.append(f"{decision_emoji} Decision: {decision.upper()}")
    summary_parts.append(f"Rationale: {rationale}")
    
    # Additional details
    if details.get("next_screening_date"):
        summary_parts.append(f"Next screening: {details['next_screening_date']}")
    
    recommendations = details.get("recommendations", [])
    if recommendations:
        summary_parts.append("Recommendations:")
        for rec in recommendations:
            summary_parts.append(f"  • {rec}")
    
    return "\n".join(summary_parts)