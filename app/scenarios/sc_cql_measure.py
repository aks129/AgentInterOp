"""
CQL Measure Development Scenario

This scenario demonstrates the Clinical Informaticist Agent's capabilities
for building, validating, and publishing CQL (Clinical Quality Language)
measures based on clinical guidelines.

The scenario showcases agent-to-agent communication where:
1. A requesting agent provides clinical guidelines or measure requirements
2. The Clinical Informaticist Agent processes the request
3. CQL is generated, validated, and can be published to FHIR servers

This is particularly useful for:
- Quality measure development workflows
- Clinical decision support rule creation
- Healthcare interoperability demonstrations
"""

from typing import Tuple, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

LABEL = "CQL Measure Development"

EXAMPLES = [
    {
        "guideline_type": "breast_cancer_screening",
        "source": "USPSTF",
        "action": "build_measure",
        "expected_output": "CQL measure for breast cancer screening"
    },
    {
        "guideline_type": "breast_cancer_screening",
        "action": "execute_full_workflow",
        "publish_to_fhir": False,
        "expected_output": "Complete workflow execution with CQL, Library, and Measure"
    }
]


def requirements() -> str:
    """Return requirements for CQL measure development scenario."""
    return (
        "Provide: guideline_type (e.g., 'breast_cancer_screening'), "
        "action ('learn_guidelines', 'build_measure', 'validate', 'publish', 'execute_full_workflow'), "
        "and optionally: source (guideline source), fhir_credentials (for publishing), "
        "validation_level ('basic' or 'comprehensive')."
    )


def evaluate(applicant_payload: Dict[str, Any], patient_bundle: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Evaluate a CQL measure development request.

    This scenario doesn't evaluate patient eligibility - instead it:
    1. Validates the request parameters
    2. Executes the requested CQL development action
    3. Returns the results as artifacts

    Args:
        applicant_payload: Request containing action and parameters
        patient_bundle: Not used in this scenario (can contain context)

    Returns:
        Tuple of (decision, rationale, artifacts)
        - decision: "completed", "needs-more-info", or "error"
        - rationale: Description of what was done
        - artifacts: Generated CQL, Library, Measure resources
    """
    from app.agents.clinical_informaticist import ClinicalInformaticistAgent

    logger.info(f"CQL Measure scenario: evaluating request")

    # Extract parameters
    action = applicant_payload.get("action", "execute_full_workflow")
    guideline_type = applicant_payload.get("guideline_type", "breast_cancer_screening")
    source = applicant_payload.get("source", "USPSTF")

    # Get Medplum credentials if provided
    fhir_credentials = applicant_payload.get("fhir_credentials", {})
    medplum_client_id = fhir_credentials.get("client_id")
    medplum_client_secret = fhir_credentials.get("client_secret")

    # Create agent
    agent = ClinicalInformaticistAgent(
        medplum_client_id=medplum_client_id,
        medplum_client_secret=medplum_client_secret
    )

    artifacts = []

    try:
        if action == "learn_guidelines":
            result = agent.learn_guidelines({
                "type": guideline_type,
                "source": source
            })

            if result["status"] == "learned":
                return (
                    "completed",
                    f"Successfully learned {result['guideline_name']} guidelines from {source}. "
                    f"Found {result['recommendations_count']} recommendations. "
                    f"Quality measure: {result['quality_measure']['cms_id']}",
                    [{"type": "guidelines_summary", "data": result}]
                )
            else:
                return (
                    "needs-more-info",
                    f"Could not load guidelines: {result.get('message', 'Unknown error')}",
                    []
                )

        elif action == "build_measure":
            # First learn guidelines
            learn_result = agent.learn_guidelines({
                "type": guideline_type,
                "source": source
            })

            if learn_result["status"] != "learned":
                return (
                    "needs-more-info",
                    f"Could not load guidelines: {learn_result.get('message', 'Unknown error')}",
                    []
                )

            # Then build measure
            build_result = agent.build_cql_measure({})

            if build_result["status"] == "built":
                # Get full CQL for artifact
                cql = agent._current_cql if hasattr(agent, '_current_cql') else None
                library = agent._current_library if hasattr(agent, '_current_library') else None
                measure = agent._current_measure if hasattr(agent, '_current_measure') else None

                artifacts = []
                if cql:
                    artifacts.append({
                        "type": "cql",
                        "name": "BreastCancerScreening.cql",
                        "content": cql
                    })
                if library:
                    artifacts.append({
                        "type": "fhir_library",
                        "name": "Library-BreastCancerScreening.json",
                        "content": library
                    })
                if measure:
                    artifacts.append({
                        "type": "fhir_measure",
                        "name": "Measure-BreastCancerScreening.json",
                        "content": measure
                    })

                return (
                    "completed",
                    f"Successfully built CQL measure: {build_result['library']['title']}. "
                    f"CQL length: {build_result['cql_length']} characters. "
                    f"CMS ID: {build_result['measure']['cms_id']}",
                    artifacts
                )
            else:
                return (
                    "error",
                    f"Failed to build measure: {build_result.get('message', 'Unknown error')}",
                    []
                )

        elif action == "validate":
            # Need to build first to have something to validate
            agent.learn_guidelines({"type": guideline_type, "source": source})
            agent.build_cql_measure({})
            validate_result = agent.validate_cql({})

            if validate_result["valid"]:
                return (
                    "completed",
                    f"CQL validation passed. {len(validate_result.get('info', []))} info messages.",
                    [{"type": "validation_result", "data": validate_result}]
                )
            else:
                return (
                    "needs-more-info",
                    f"CQL validation failed with {len(validate_result['errors'])} errors: "
                    f"{'; '.join(validate_result['errors'])}",
                    [{"type": "validation_result", "data": validate_result}]
                )

        elif action == "execute_full_workflow":
            workflow_result = agent.execute_full_workflow({
                "guideline_type": guideline_type
            })

            if workflow_result["status"] == "ready_to_publish":
                artifacts_data = workflow_result.get("artifacts", {})

                artifacts = []
                if artifacts_data.get("cql"):
                    artifacts.append({
                        "type": "cql",
                        "name": "BreastCancerScreening.cql",
                        "content": artifacts_data["cql"]
                    })
                if artifacts_data.get("library"):
                    artifacts.append({
                        "type": "fhir_library",
                        "name": "Library-BreastCancerScreening.json",
                        "content": artifacts_data["library"]
                    })
                if artifacts_data.get("measure"):
                    artifacts.append({
                        "type": "fhir_measure",
                        "name": "Measure-BreastCancerScreening.json",
                        "content": artifacts_data["measure"]
                    })

                step_summary = " -> ".join([
                    f"{step['action']}({step['status']})"
                    for step in workflow_result.get("steps", [])
                ])

                return (
                    "completed",
                    f"Full workflow completed successfully. Steps: {step_summary}. "
                    f"Ready to publish to FHIR server.",
                    artifacts
                )
            else:
                failed_step = workflow_result.get("failed_at_step", "unknown")
                return (
                    "error",
                    f"Workflow failed at step {failed_step}: {workflow_result.get('status', 'unknown')}",
                    [{"type": "workflow_result", "data": workflow_result}]
                )

        elif action == "get_status":
            status = agent.get_workflow_status()
            return (
                "completed",
                f"Workflow status retrieved. Guidelines loaded: {status['guidelines_loaded']}, "
                f"Medplum configured: {status['medplum_configured']}",
                [{"type": "status", "data": status}]
            )

        else:
            return (
                "needs-more-info",
                f"Unknown action '{action}'. Supported actions: learn_guidelines, build_measure, "
                f"validate, execute_full_workflow, get_status",
                []
            )

    except Exception as e:
        logger.error(f"CQL Measure scenario error: {str(e)}")
        return (
            "error",
            f"Error during CQL measure development: {str(e)}",
            []
        )


# Additional helper functions for the scenario

def get_supported_guidelines() -> List[Dict[str, str]]:
    """Return list of supported clinical guidelines."""
    return [
        {
            "type": "breast_cancer_screening",
            "name": "Breast Cancer Screening (BCS)",
            "source": "USPSTF",
            "cms_id": "CMS125v11",
            "nqf_id": "2372"
        }
        # Future: Add more guidelines as they're implemented
    ]


def get_scenario_info() -> Dict[str, Any]:
    """Return detailed information about this scenario."""
    return {
        "scenario": "cql_measure",
        "label": LABEL,
        "description": "Build and publish CQL quality measures from clinical guidelines",
        "capabilities": [
            "Learn clinical guidelines from authoritative sources",
            "Generate CQL (Clinical Quality Language) code",
            "Build FHIR Library and Measure resources",
            "Validate CQL syntax and semantics",
            "Publish to FHIR servers (Medplum)"
        ],
        "supported_guidelines": get_supported_guidelines(),
        "actions": [
            {
                "name": "learn_guidelines",
                "description": "Load and internalize clinical guidelines"
            },
            {
                "name": "build_measure",
                "description": "Generate CQL and FHIR resources from guidelines"
            },
            {
                "name": "validate",
                "description": "Validate generated CQL"
            },
            {
                "name": "execute_full_workflow",
                "description": "Run complete workflow: learn, build, validate"
            },
            {
                "name": "get_status",
                "description": "Get current workflow status"
            }
        ],
        "integration": {
            "fhir_servers": ["Medplum"],
            "protocols": ["A2A", "MCP"]
        }
    }
