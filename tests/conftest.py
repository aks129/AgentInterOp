"""
Pytest configuration and fixtures for AgentInterOp tests
"""
import pytest
import os
import tempfile
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI application"""
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="function")
def clean_stores():
    """Clean in-memory stores before each test"""
    from app.store.memory import task_store, conversation_store, trace_store
    from app.protocols.a2a import _active_tasks
    from app.protocols.mcp import _mcp_conversations
    
    # Clear stores
    task_store._tasks.clear()
    conversation_store._conversations.clear() 
    trace_store._traces.clear()
    _active_tasks.clear()
    _mcp_conversations.clear()
    
    yield
    
    # Clean up after test
    task_store._tasks.clear()
    conversation_store._conversations.clear()
    trace_store._traces.clear()
    _active_tasks.clear()
    _mcp_conversations.clear()


@pytest.fixture(scope="function")
def temp_config():
    """Create temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "mode": {"role": "full_stack"},
            "protocol": {"default_transport": "a2a", "public_base_url": None},
            "scenario": {"active": "bcse", "options": {}},
            "data": {"options": {}},
            "simulation": {"delay_ms": 0, "error_rate": 0.0, "capacity_limit": None},
            "logging": {"level": "WARN", "redact_tokens": True}
        }
        import json
        json.dump(config_data, f)
        temp_path = f.name
    
    with patch('app.config.CONFIG_PATH', temp_path):
        yield temp_path
    
    # Clean up
    os.unlink(temp_path)


@pytest.fixture(scope="function")
def mock_anthropic_api():
    """Mock Anthropic API responses for testing"""
    def mock_narrative_to_json(text):
        return {
            "age_range": {"min": 50, "max": 74},
            "required_sex": "female",
            "screening_interval_months": 27
        }
    
    with patch('app.llm.anthropic.narrative_to_json', side_effect=mock_narrative_to_json):
        yield


@pytest.fixture(scope="function")
def mock_fhir_server():
    """Mock FHIR server responses for testing"""
    mock_capabilities = {
        "resourceType": "CapabilityStatement",
        "fhirVersion": "4.0.1",
        "rest": [{"mode": "server"}]
    }
    
    mock_patient_search = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{
            "resource": {
                "resourceType": "Patient",
                "id": "test-patient-1",
                "name": [{"given": ["Test"], "family": "Patient"}],
                "gender": "female",
                "birthDate": "1968-05-10"
            }
        }]
    }
    
    mock_patient_everything = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient", 
                    "id": "test-patient-1",
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
                            "code": "77067"
                        }]
                    },
                    "performedDateTime": "2024-12-01"
                }
            }
        ]
    }
    
    with patch('app.fhir.connector.build_connector') as mock_connector:
        mock_conn = mock_connector.return_value
        mock_conn.capabilities.return_value = mock_capabilities
        mock_conn.search.return_value = mock_patient_search
        mock_conn.patient_everything.return_value = mock_patient_everything
        yield mock_conn


@pytest.fixture(scope="function")
def sample_fhir_bundles():
    """Provide sample FHIR bundles for testing"""
    eligible_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "eligible-patient",
                    "gender": "female", 
                    "birthDate": "1968-05-10"
                }
            },
            {
                "resource": {
                    "resourceType": "Procedure",
                    "id": "recent-mammogram",
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
    
    ineligible_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{
            "resource": {
                "resourceType": "Patient",
                "id": "ineligible-patient", 
                "gender": "male",
                "birthDate": "1968-05-10"
            }
        }]
    }
    
    missing_data_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{
            "resource": {
                "resourceType": "Patient",
                "id": "missing-data-patient",
                "gender": "female",
                "birthDate": "1968-05-10"
                # Missing mammogram procedure
            }
        }]
    }
    
    return {
        "eligible": eligible_bundle,
        "ineligible": ineligible_bundle, 
        "missing_data": missing_data_bundle
    }


@pytest.fixture(scope="session")
def sample_payloads():
    """Provide sample BCS-E payloads for testing"""
    return {
        "eligible": {
            "sex": "female",
            "birthDate": "1968-05-10",
            "last_mammogram": "2024-12-01"
        },
        "ineligible_sex": {
            "sex": "male", 
            "birthDate": "1968-05-10",
            "last_mammogram": "2024-12-01"
        },
        "ineligible_age": {
            "sex": "female",
            "birthDate": "2010-01-01",  # Too young
            "last_mammogram": "2024-12-01"
        },
        "needs_more_info": {
            "sex": "female",
            "birthDate": "1968-05-10"
            # Missing mammogram date
        },
        "old_mammogram": {
            "sex": "female",
            "birthDate": "1968-05-10", 
            "last_mammogram": "2020-01-01"  # Over 27 months ago
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    test_env_vars = {
        "APP_ENV": "test",
        "SESSION_SECRET": "test-secret-key",
        "ANTHROPIC_API_KEY": "test-api-key"
    }
    
    # Store original values
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value