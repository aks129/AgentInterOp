"""
BCS-E Evaluator Unit Tests

Tests the breast cancer screening eligibility logic with comprehensive edge cases.
"""
import pytest
from datetime import date, timedelta
from app.scenarios.bcse import evaluate, map_fhir_bundle


class TestBCSEEvaluator:
    """Test BCS-E eligibility evaluator logic"""

    def test_eligible_case_exact_age_bounds(self):
        """Test eligibility at exact age boundaries (50 and 74)"""
        today = date.today()
        birth_50 = date(today.year - 50, today.month, today.day)
        birth_74 = date(today.year - 74, today.month, today.day)
        recent_mammo = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Test age 50 (lower bound)
        payload_50 = {
            "sex": "female",
            "birthDate": birth_50.strftime("%Y-%m-%d"),
            "last_mammogram": recent_mammo
        }
        result_50 = evaluate(payload_50)
        assert result_50["status"] == "eligible"
        
        # Test age 74 (upper bound)
        payload_74 = {
            "sex": "female", 
            "birthDate": birth_74.strftime("%Y-%m-%d"),
            "last_mammogram": recent_mammo
        }
        result_74 = evaluate(payload_74)
        assert result_74["status"] == "eligible"

    def test_ineligible_age_boundaries(self):
        """Test ineligibility just outside age boundaries"""
        today = date.today()
        birth_49 = date(today.year - 49, today.month, today.day)
        birth_75 = date(today.year - 75, today.month, today.day)
        recent_mammo = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Test age 49 (too young)
        payload_49 = {
            "sex": "female",
            "birthDate": birth_49.strftime("%Y-%m-%d"),
            "last_mammogram": recent_mammo
        }
        result_49 = evaluate(payload_49)
        assert result_49["status"] == "ineligible"
        assert "Age 49 outside 50-74" in result_49["rationale"][0]
        
        # Test age 75 (too old)
        payload_75 = {
            "sex": "female",
            "birthDate": birth_75.strftime("%Y-%m-%d"),
            "last_mammogram": recent_mammo
        }
        result_75 = evaluate(payload_75)
        assert result_75["status"] == "ineligible"
        assert "Age 75 outside 50-74" in result_75["rationale"][0]

    def test_mammogram_time_boundaries(self):
        """Test mammogram timing at 27-month boundary"""
        today = date.today()
        birth_date = date(today.year - 55, today.month, today.day)
        
        # Exactly 27 months ago (should be eligible)
        mammo_27_months = today - timedelta(days=int(27 * 30.44))
        payload_27 = {
            "sex": "female",
            "birthDate": birth_date.strftime("%Y-%m-%d"),
            "last_mammogram": mammo_27_months.strftime("%Y-%m-%d")
        }
        result_27 = evaluate(payload_27)
        assert result_27["status"] == "eligible"
        
        # Over 27 months ago (should need more info/new screening)
        mammo_28_months = today - timedelta(days=int(28 * 30.44))
        payload_28 = {
            "sex": "female",
            "birthDate": birth_date.strftime("%Y-%m-%d"),
            "last_mammogram": mammo_28_months.strftime("%Y-%m-%d")
        }
        result_28 = evaluate(payload_28)
        assert result_28["status"] == "needs-more-info"
        assert "Last mammogram older than 27 months" in result_28["rationale"][0]

    def test_sex_validation(self):
        """Test sex field validation"""
        today = date.today()
        birth_date = date(today.year - 55, today.month, today.day)
        recent_mammo = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Test male (ineligible)
        payload_male = {
            "sex": "male",
            "birthDate": birth_date.strftime("%Y-%m-%d"),
            "last_mammogram": recent_mammo
        }
        result_male = evaluate(payload_male)
        assert result_male["status"] == "ineligible"
        assert "Requires female sex" in result_male["rationale"][0]
        
        # Test other/unknown sex values
        for sex_value in ["other", "unknown", "", None]:
            payload = {
                "sex": sex_value,
                "birthDate": birth_date.strftime("%Y-%m-%d"),
                "last_mammogram": recent_mammo
            }
            result = evaluate(payload)
            assert result["status"] == "ineligible"

    def test_missing_data_needs_more_info(self):
        """Test handling of missing required data"""
        today = date.today()
        
        # Missing mammogram only should ask for more info
        payload_no_mammo = {
            "sex": "female",
            "birthDate": date(today.year - 55, today.month, today.day).strftime("%Y-%m-%d")
        }
        result = evaluate(payload_no_mammo)
        assert result["status"] == "needs-more-info"
        assert "Missing last_mammogram" in result["rationale"][0]
        assert "Provide prior mammogram date" in result["request"]
        
        # Missing multiple fields should be ineligible
        payload_missing_multiple = {"sex": "female"}
        result = evaluate(payload_missing_multiple)
        assert result["status"] == "ineligible"

    def test_invalid_date_formats(self):
        """Test handling of invalid date formats"""
        invalid_dates = ["2024-13-01", "invalid-date", "2024/01/01", "", None]
        
        for invalid_date in invalid_dates:
            payload = {
                "sex": "female",
                "birthDate": invalid_date,
                "last_mammogram": "2024-01-01"
            }
            result = evaluate(payload)
            if invalid_date in [None, ""]:
                assert "Missing birthDate" in str(result["rationale"])
            else:
                # Invalid format should result in None parsing and missing birthDate
                assert result["status"] in ["ineligible", "needs-more-info"]


class TestFHIRMapping:
    """Test FHIR Bundle to BCS-E payload mapping"""

    def test_complete_fhir_bundle_mapping(self):
        """Test mapping a complete FHIR bundle with Patient and Procedure"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "test-patient",
                        "gender": "female",
                        "birthDate": "1968-05-10"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Procedure",
                        "id": "mammogram-1",
                        "code": {
                            "coding": [{
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "77067",
                                "display": "Screening mammography"
                            }]
                        },
                        "performedDateTime": "2024-12-01"
                    }
                }
            ]
        }
        
        result = map_fhir_bundle(bundle)
        expected = {
            "sex": "female",
            "birthDate": "1968-05-10",
            "last_mammogram": "2024-12-01"
        }
        assert result == expected

    def test_missing_patient_resource(self):
        """Test mapping bundle without Patient resource"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{
                "resource": {
                    "resourceType": "Procedure",
                    "code": {
                        "coding": [{
                            "system": "http://www.ama-assn.org/go/cpt",
                            "code": "77067"
                        }]
                    },
                    "performedDateTime": "2024-12-01"
                }
            }]
        }
        
        result = map_fhir_bundle(bundle)
        expected = {
            "sex": None,
            "birthDate": None,
            "last_mammogram": "2024-12-01"
        }
        assert result == expected

    def test_missing_mammogram_procedure(self):
        """Test mapping bundle without mammogram procedure"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{
                "resource": {
                    "resourceType": "Patient",
                    "gender": "female",
                    "birthDate": "1968-05-10"
                }
            }]
        }
        
        result = map_fhir_bundle(bundle)
        expected = {
            "sex": "female",
            "birthDate": "1968-05-10",
            "last_mammogram": None
        }
        assert result == expected

    def test_wrong_procedure_code(self):
        """Test filtering out procedures with wrong CPT codes"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "gender": "female",
                        "birthDate": "1968-05-10"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Procedure",
                        "code": {
                            "coding": [{
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "77066",  # Different CPT code
                                "display": "Different procedure"
                            }]
                        },
                        "performedDateTime": "2024-12-01"
                    }
                }
            ]
        }
        
        result = map_fhir_bundle(bundle)
        expected = {
            "sex": "female",
            "birthDate": "1968-05-10",
            "last_mammogram": None
        }
        assert result == expected

    def test_multiple_mammogram_procedures(self):
        """Test handling multiple mammogram procedures (should use first found)"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "gender": "female",
                        "birthDate": "1968-05-10"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Procedure",
                        "code": {
                            "coding": [{
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "77067"
                            }]
                        },
                        "performedDateTime": "2024-12-01"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Procedure", 
                        "code": {
                            "coding": [{
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "77067"
                            }]
                        },
                        "performedDateTime": "2024-06-01"
                    }
                }
            ]
        }
        
        result = map_fhir_bundle(bundle)
        # Should get the first mammogram found
        assert result["last_mammogram"] == "2024-12-01"

    def test_empty_bundle(self):
        """Test mapping empty or malformed bundles"""
        empty_bundle = {"resourceType": "Bundle", "entry": []}
        result = map_fhir_bundle(empty_bundle)
        expected = {"sex": None, "birthDate": None, "last_mammogram": None}
        assert result == expected
        
        # Test bundle with no entries key
        no_entries_bundle = {"resourceType": "Bundle"}
        result = map_fhir_bundle(no_entries_bundle)
        assert result == expected


class TestIntegrationScenarios:
    """Integration tests combining FHIR mapping and evaluation"""

    def test_end_to_end_eligible_patient(self):
        """Test complete workflow for eligible patient"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "gender": "female",
                        "birthDate": "1968-05-10"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Procedure",
                        "code": {
                            "coding": [{
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "77067"
                            }]
                        },
                        "performedDateTime": "2024-12-01"
                    }
                }
            ]
        }
        
        payload = map_fhir_bundle(bundle)
        result = evaluate(payload)
        
        assert result["status"] == "eligible"
        assert "female" in result["rationale"][0]
        assert "mammogram within 27 months" in result["rationale"][0]

    def test_end_to_end_ineligible_patient(self):
        """Test complete workflow for ineligible patient"""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection", 
            "entry": [{
                "resource": {
                    "resourceType": "Patient",
                    "gender": "male",
                    "birthDate": "1968-05-10"
                }
            }]
        }
        
        payload = map_fhir_bundle(bundle)
        result = evaluate(payload)
        
        assert result["status"] == "ineligible"
        assert "Requires female sex" in result["rationale"][0]