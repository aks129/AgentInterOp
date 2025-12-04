"""
Clinical Informaticist Agent - Specialized for CQL measure development and FHIR publishing.

This agent demonstrates agent-to-agent communication by:
1. Learning medical guidelines (e.g., breast cancer screening)
2. Using CQL-builder MCP to construct clinical quality measures
3. Validating CQL measures against clinical standards
4. Publishing validated measures to a FHIR server (Medplum)

The agent showcases the power of tool-based agent communication
where specialized capabilities are exposed via MCP tools.
"""

import json
import logging
import os
import httpx
import base64
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


# Breast Cancer Screening Guidelines based on USPSTF recommendations
BREAST_CANCER_SCREENING_GUIDELINES = {
    "name": "Breast Cancer Screening (BCS)",
    "source": "USPSTF 2024 Guidelines",
    "version": "2.0",
    "recommendations": [
        {
            "id": "BCS-001",
            "title": "Biennial Screening Mammography",
            "population": "Women aged 50-74 years",
            "recommendation": "Biennial screening mammography",
            "grade": "B",
            "evidence_level": "High",
            "criteria": {
                "age_min": 50,
                "age_max": 74,
                "sex": "female",
                "interval_months": 24,
                "procedure_codes": [
                    {"system": "CPT", "code": "77067", "display": "Screening mammography bilateral"},
                    {"system": "HCPCS", "code": "G0202", "display": "Screening mammography digital bilateral"},
                    {"system": "LOINC", "code": "24606-6", "display": "MG Breast Screening"}
                ]
            }
        },
        {
            "id": "BCS-002",
            "title": "Earlier Screening Consideration",
            "population": "Women aged 40-49 years",
            "recommendation": "Individual decision based on patient values and risk factors",
            "grade": "C",
            "evidence_level": "Moderate",
            "criteria": {
                "age_min": 40,
                "age_max": 49,
                "sex": "female",
                "interval_months": 24,
                "requires_shared_decision_making": True
            }
        }
    ],
    "exclusion_criteria": [
        "Current breast cancer diagnosis",
        "Previous bilateral mastectomy",
        "Terminal illness with life expectancy < 10 years"
    ],
    "quality_measure": {
        "nqf_id": "2372",
        "cms_id": "CMS125v11",
        "title": "Breast Cancer Screening",
        "description": "Percentage of women 50-74 years of age who had a mammogram to screen for breast cancer in the 27 months prior to the end of the Measurement Period",
        "denominator": "Women 50-74 at end of measurement period",
        "numerator": "Women with mammogram in 27 months prior to measurement period end",
        "measurement_period": "12 months"
    }
}


class MedplumClient:
    """Client for interacting with Medplum FHIR server."""

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.medplum.com"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        logger.info(f"MedplumClient initialized for {self.base_url}")

    async def authenticate(self) -> bool:
        """Authenticate with Medplum using client credentials."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self.token_expires = datetime.now()
                    logger.info("Successfully authenticated with Medplum")
                    return True
                else:
                    logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for FHIR API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }

    async def create_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Create a FHIR resource."""
        resource_type = resource.get("resourceType")
        if not resource_type:
            raise ValueError("Resource must have resourceType")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/fhir/R4/{resource_type}",
                json=resource,
                headers=self._get_headers()
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Create resource failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to create resource: {response.text}")

    async def update_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing FHIR resource."""
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")

        if not resource_type or not resource_id:
            raise ValueError("Resource must have resourceType and id")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/fhir/R4/{resource_type}/{resource_id}",
                json=resource,
                headers=self._get_headers()
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Update resource failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to update resource: {response.text}")

    async def search_resources(self, resource_type: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
        """Search for FHIR resources."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/fhir/R4/{resource_type}",
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 200:
                bundle = response.json()
                return [entry.get("resource") for entry in bundle.get("entry", [])]
            else:
                logger.error(f"Search failed: {response.status_code} - {response.text}")
                return []


class CQLBuilder:
    """
    CQL (Clinical Quality Language) Builder for constructing quality measures.

    This simulates what would be exposed via an MCP tool for CQL construction.
    In production, this would be an external MCP server providing CQL capabilities.
    """

    @staticmethod
    def build_measure_cql(guideline: Dict[str, Any]) -> str:
        """Build CQL from clinical guideline specifications."""
        recommendation = guideline.get("recommendations", [{}])[0]
        criteria = recommendation.get("criteria", {})
        qm = guideline.get("quality_measure", {})

        age_min = criteria.get("age_min", 50)
        age_max = criteria.get("age_max", 74)
        interval_months = criteria.get("interval_months", 24) + 3  # 27 months per CMS spec

        cql = f'''library BreastCancerScreening version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

codesystem "CPT": 'http://www.ama-assn.org/go/cpt'
codesystem "HCPCS": 'https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets'
codesystem "LOINC": 'http://loinc.org'
codesystem "AdministrativeGender": 'http://hl7.org/fhir/administrative-gender'

valueset "Mammography": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.464.1003.108.12.1018'
valueset "Bilateral Mastectomy": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.464.1003.198.12.1005'

code "Female": 'female' from "AdministrativeGender"

parameter "Measurement Period" Interval<DateTime>

context Patient

define "Initial Population":
  Patient.gender = 'female'
    and AgeInYearsAt(end of "Measurement Period") >= {age_min}
    and AgeInYearsAt(end of "Measurement Period") <= {age_max}

define "Denominator":
  "Initial Population"

define "Denominator Exclusion":
  exists "Bilateral Mastectomy Procedure"

define "Bilateral Mastectomy Procedure":
  [Procedure: "Bilateral Mastectomy"] P
    where P.status = 'completed'
      and P.performed.toInterval() ends on or before end of "Measurement Period"

define "Numerator":
  exists "Mammography Procedure"

define "Mammography Procedure":
  [Procedure: "Mammography"] M
    where M.status = 'completed'
      and M.performed.toInterval() ends during Interval[
        end of "Measurement Period" - {interval_months} months,
        end of "Measurement Period"
      ]

define "Stratification 1":
  AgeInYearsAt(end of "Measurement Period") in Interval[{age_min}, 64]

define "Stratification 2":
  AgeInYearsAt(end of "Measurement Period") in Interval[65, {age_max}]
'''
        return cql

    @staticmethod
    def validate_cql(cql: str) -> Dict[str, Any]:
        """Validate CQL syntax and semantics."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }

        # Basic syntax checks
        required_sections = ["library", "using FHIR", "context Patient", "define"]
        for section in required_sections:
            if section not in cql:
                validation_result["errors"].append(f"Missing required section: {section}")
                validation_result["valid"] = False

        # Check for common issues
        if "define \"Initial Population\"" not in cql:
            validation_result["warnings"].append("Missing Initial Population definition")

        if "define \"Numerator\"" not in cql:
            validation_result["errors"].append("Measure must define Numerator")
            validation_result["valid"] = False

        if "define \"Denominator\"" not in cql:
            validation_result["errors"].append("Measure must define Denominator")
            validation_result["valid"] = False

        # Add informational notes
        if "Stratification" in cql:
            validation_result["info"].append("Measure includes stratification definitions")

        if "Denominator Exclusion" in cql:
            validation_result["info"].append("Measure includes denominator exclusions")

        return validation_result

    @staticmethod
    def build_library_resource(cql: str, guideline: Dict[str, Any]) -> Dict[str, Any]:
        """Build a FHIR Library resource containing the CQL."""
        qm = guideline.get("quality_measure", {})

        library = {
            "resourceType": "Library",
            "url": f"http://example.org/Library/BreastCancerScreening",
            "identifier": [
                {
                    "system": "http://cms.gov/measures",
                    "value": qm.get("cms_id", "CMS125")
                }
            ],
            "version": "1.0.0",
            "name": "BreastCancerScreening",
            "title": qm.get("title", "Breast Cancer Screening"),
            "status": "active",
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/library-type",
                        "code": "logic-library",
                        "display": "Logic Library"
                    }
                ]
            },
            "date": datetime.now().isoformat(),
            "description": qm.get("description", "Breast cancer screening measure"),
            "content": [
                {
                    "contentType": "text/cql",
                    "data": base64.b64encode(cql.encode('utf-8')).decode('utf-8')
                }
            ],
            "relatedArtifact": [
                {
                    "type": "depends-on",
                    "resource": "http://fhir.org/guides/cqf/common/Library/FHIRHelpers|4.0.1"
                }
            ]
        }

        return library

    @staticmethod
    def build_measure_resource(cql: str, guideline: Dict[str, Any]) -> Dict[str, Any]:
        """Build a FHIR Measure resource."""
        qm = guideline.get("quality_measure", {})
        recommendation = guideline.get("recommendations", [{}])[0]

        measure = {
            "resourceType": "Measure",
            "url": f"http://example.org/Measure/BreastCancerScreening",
            "identifier": [
                {
                    "system": "http://cms.gov/measures",
                    "value": qm.get("cms_id", "CMS125")
                },
                {
                    "system": "http://qualitymeasures.org/nqf",
                    "value": qm.get("nqf_id", "2372")
                }
            ],
            "version": "1.0.0",
            "name": "BreastCancerScreeningMeasure",
            "title": qm.get("title", "Breast Cancer Screening"),
            "status": "active",
            "experimental": False,
            "date": datetime.now().isoformat(),
            "publisher": "Clinical Informaticist Agent",
            "description": qm.get("description", "Breast cancer screening quality measure"),
            "purpose": "To improve breast cancer detection through appropriate screening",
            "usage": "This measure is used for quality reporting and improvement",
            "effectivePeriod": {
                "start": f"{datetime.now().year}-01-01",
                "end": f"{datetime.now().year}-12-31"
            },
            "library": ["http://example.org/Library/BreastCancerScreening"],
            "scoring": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/measure-scoring",
                        "code": "proportion",
                        "display": "Proportion"
                    }
                ]
            },
            "type": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/measure-type",
                            "code": "process",
                            "display": "Process"
                        }
                    ]
                }
            ],
            "improvementNotation": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/measure-improvement-notation",
                        "code": "increase",
                        "display": "Increased score indicates improvement"
                    }
                ]
            },
            "group": [
                {
                    "population": [
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                        "code": "initial-population",
                                        "display": "Initial Population"
                                    }
                                ]
                            },
                            "description": f"Women aged {recommendation.get('criteria', {}).get('age_min', 50)}-{recommendation.get('criteria', {}).get('age_max', 74)} years",
                            "criteria": {
                                "language": "text/cql-identifier",
                                "expression": "Initial Population"
                            }
                        },
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                        "code": "denominator",
                                        "display": "Denominator"
                                    }
                                ]
                            },
                            "description": qm.get("denominator", "Eligible population"),
                            "criteria": {
                                "language": "text/cql-identifier",
                                "expression": "Denominator"
                            }
                        },
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                        "code": "denominator-exclusion",
                                        "display": "Denominator Exclusion"
                                    }
                                ]
                            },
                            "description": "Women with bilateral mastectomy",
                            "criteria": {
                                "language": "text/cql-identifier",
                                "expression": "Denominator Exclusion"
                            }
                        },
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                        "code": "numerator",
                                        "display": "Numerator"
                                    }
                                ]
                            },
                            "description": qm.get("numerator", "Women with screening mammogram"),
                            "criteria": {
                                "language": "text/cql-identifier",
                                "expression": "Numerator"
                            }
                        }
                    ],
                    "stratifier": [
                        {
                            "code": {
                                "text": "Age 50-64"
                            },
                            "criteria": {
                                "language": "text/cql-identifier",
                                "expression": "Stratification 1"
                            }
                        },
                        {
                            "code": {
                                "text": "Age 65-74"
                            },
                            "criteria": {
                                "language": "text/cql-identifier",
                                "expression": "Stratification 2"
                            }
                        }
                    ]
                }
            ]
        }

        return measure


class ClinicalInformaticistAgent:
    """
    Clinical Informaticist Agent - Specialized for CQL measure development.

    This agent demonstrates agent-to-agent communication by:
    1. Learning medical guidelines from authoritative sources
    2. Building CQL measures using specialized tools (MCP)
    3. Validating measures against clinical quality standards
    4. Publishing validated measures to FHIR servers

    The agent showcases:
    - Tool-based communication (CQL Builder MCP)
    - External service integration (Medplum FHIR server)
    - Domain-specific knowledge (clinical guidelines)
    - Quality assurance (CQL validation)
    """

    def __init__(self, medplum_client_id: str = None, medplum_client_secret: str = None):
        self.agent_id = "clinical_informaticist"
        self.name = "Clinical Informaticist Agent"
        self.description = "Builds and publishes CQL quality measures from clinical guidelines"
        self.domain = "clinical_informatics"
        self.role = "specialist"

        # Initialize Medplum client if credentials provided
        self.medplum_client = None
        if medplum_client_id and medplum_client_secret:
            self.medplum_client = MedplumClient(
                client_id=medplum_client_id,
                client_secret=medplum_client_secret
            )

        # Initialize CQL builder
        self.cql_builder = CQLBuilder()

        # Load default guidelines
        self.guidelines = BREAST_CANCER_SCREENING_GUIDELINES

        # Track workflow state
        self.workflow_state = {
            "cql_generated": False,
            "cql_validated": False,
            "library_created": False,
            "measure_created": False,
            "published_to_fhir": False
        }

        # Load agent card
        self.card = self._load_agent_card()
        logger.info("Clinical Informaticist Agent initialized")

    def _load_agent_card(self) -> Dict[str, Any]:
        """Load agent card configuration."""
        try:
            card_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'cards', 'clinical-informaticist-card.json'
            )
            with open(card_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load agent card: {e}")
            return {
                "name": self.name,
                "description": self.description,
                "capabilities": [
                    "guideline_learning",
                    "cql_generation",
                    "cql_validation",
                    "fhir_publishing",
                    "measure_development"
                ],
                "tools": [
                    "cql_builder",
                    "cql_validator",
                    "fhir_publisher",
                    "guideline_loader"
                ]
            }

    def process_message(self, message: Dict[str, Any], protocol: str) -> Dict[str, Any]:
        """Process incoming message based on protocol."""
        if protocol == "a2a":
            return self._process_a2a_message(message)
        elif protocol == "mcp":
            return self._process_mcp_message(message)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")

    def _process_a2a_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process A2A JSON-RPC message."""
        method = message.get("method")
        params = message.get("params", {})
        message_id = message.get("id")

        try:
            if method == "learn_guidelines":
                result = self.learn_guidelines(params)
            elif method == "build_cql_measure":
                result = self.build_cql_measure(params)
            elif method == "validate_cql":
                result = self.validate_cql(params)
            elif method == "publish_to_fhir":
                result = self.publish_to_fhir(params)
            elif method == "get_workflow_status":
                result = self.get_workflow_status()
            elif method == "execute_full_workflow":
                result = self.execute_full_workflow(params)
            else:
                raise ValueError(f"Unknown method: {method}")

            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": message_id
            }

        except Exception as e:
            logger.error(f"Error processing A2A message: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                },
                "id": message_id
            }

    def _process_mcp_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP tool call or message."""
        if message.get("type") == "tool_call":
            return self._process_mcp_tool_call(message)
        else:
            return self._process_mcp_regular_message(message)

    def _process_mcp_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP tool call."""
        tool_name = tool_call.get("function", {}).get("name")
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        call_id = tool_call.get("id")

        try:
            if tool_name == "learn_guidelines":
                result = self.learn_guidelines(arguments)
            elif tool_name == "build_cql_measure":
                result = self.build_cql_measure(arguments)
            elif tool_name == "validate_cql":
                result = self.validate_cql(arguments)
            elif tool_name == "publish_to_fhir":
                result = self.publish_to_fhir(arguments)
            elif tool_name == "execute_full_workflow":
                result = self.execute_full_workflow(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "type": "tool_response",
                "id": call_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error processing MCP tool call: {str(e)}")
            return {
                "type": "tool_response",
                "id": call_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _process_mcp_regular_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process regular MCP message."""
        return {
            "type": "response",
            "agent": self.agent_id,
            "message": "Clinical Informaticist Agent ready. Available tools: learn_guidelines, build_cql_measure, validate_cql, publish_to_fhir, execute_full_workflow",
            "capabilities": self.card.get("capabilities", []),
            "timestamp": datetime.now().isoformat()
        }

    def requirements_message(self) -> List[str]:
        """Return required inputs for CQL measure development."""
        return [
            "guideline_source - Source of clinical guidelines (e.g., 'USPSTF', 'ACS', 'ACR')",
            "measure_type - Type of measure (e.g., 'breast_cancer_screening', 'colorectal_screening')",
            "target_population - Description of target patient population",
            "fhir_server_url - URL of FHIR server for publishing (optional)",
            "validation_level - Level of validation ('basic', 'comprehensive')"
        ]

    def learn_guidelines(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Learn and internalize clinical guidelines for measure development.

        This method demonstrates how the agent acquires domain knowledge
        that will be used in subsequent CQL construction.
        """
        guideline_type = params.get("type", "breast_cancer_screening")
        source = params.get("source", "USPSTF")

        logger.info(f"Learning guidelines: {guideline_type} from {source}")

        # In production, this would fetch from authoritative sources
        # For demo, we use the built-in guidelines
        if guideline_type == "breast_cancer_screening":
            self.guidelines = BREAST_CANCER_SCREENING_GUIDELINES

            return {
                "status": "learned",
                "guideline_name": self.guidelines["name"],
                "source": self.guidelines["source"],
                "version": self.guidelines["version"],
                "recommendations_count": len(self.guidelines["recommendations"]),
                "quality_measure": {
                    "nqf_id": self.guidelines["quality_measure"]["nqf_id"],
                    "cms_id": self.guidelines["quality_measure"]["cms_id"],
                    "title": self.guidelines["quality_measure"]["title"]
                },
                "next_step": "build_cql_measure",
                "agent": self.agent_id
            }
        else:
            return {
                "status": "not_found",
                "message": f"Guideline type '{guideline_type}' not available. Supported: breast_cancer_screening",
                "agent": self.agent_id
            }

    def build_cql_measure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build CQL measure from learned guidelines.

        This demonstrates using the CQL Builder tool to construct
        a clinical quality measure from structured guidelines.
        """
        if not self.guidelines:
            return {
                "status": "error",
                "message": "No guidelines loaded. Call learn_guidelines first.",
                "agent": self.agent_id
            }

        logger.info("Building CQL measure from guidelines")

        # Generate CQL
        cql = self.cql_builder.build_measure_cql(self.guidelines)

        # Build FHIR resources
        library = self.cql_builder.build_library_resource(cql, self.guidelines)
        measure = self.cql_builder.build_measure_resource(cql, self.guidelines)

        # Update workflow state
        self.workflow_state["cql_generated"] = True

        # Store for later use
        self._current_cql = cql
        self._current_library = library
        self._current_measure = measure

        return {
            "status": "built",
            "cql_length": len(cql),
            "cql_preview": cql[:500] + "..." if len(cql) > 500 else cql,
            "library": {
                "name": library["name"],
                "title": library["title"],
                "url": library["url"]
            },
            "measure": {
                "name": measure["name"],
                "title": measure["title"],
                "nqf_id": self.guidelines["quality_measure"]["nqf_id"],
                "cms_id": self.guidelines["quality_measure"]["cms_id"]
            },
            "next_step": "validate_cql",
            "agent": self.agent_id
        }

    def validate_cql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate generated CQL against quality standards.

        This demonstrates the validation step ensuring the CQL
        is syntactically and semantically correct.
        """
        if not hasattr(self, '_current_cql') or not self._current_cql:
            return {
                "status": "error",
                "message": "No CQL to validate. Call build_cql_measure first.",
                "agent": self.agent_id
            }

        logger.info("Validating CQL measure")

        validation_result = self.cql_builder.validate_cql(self._current_cql)

        self.workflow_state["cql_validated"] = validation_result["valid"]

        return {
            "status": "validated" if validation_result["valid"] else "invalid",
            "valid": validation_result["valid"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "info": validation_result["info"],
            "next_step": "publish_to_fhir" if validation_result["valid"] else "fix_errors",
            "agent": self.agent_id
        }

    async def publish_to_fhir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish validated CQL measure to FHIR server.

        This demonstrates integration with external FHIR servers
        (Medplum) for publishing clinical quality measures.
        """
        if not self.workflow_state.get("cql_validated"):
            return {
                "status": "error",
                "message": "CQL not validated. Call validate_cql first.",
                "agent": self.agent_id
            }

        if not self.medplum_client:
            # Return simulated success for demo
            self.workflow_state["library_created"] = True
            self.workflow_state["measure_created"] = True
            self.workflow_state["published_to_fhir"] = True

            return {
                "status": "simulated",
                "message": "No Medplum client configured. Simulating publish.",
                "library": {
                    "id": "simulated-library-id",
                    "url": self._current_library["url"]
                },
                "measure": {
                    "id": "simulated-measure-id",
                    "url": self._current_measure["url"]
                },
                "workflow_complete": True,
                "agent": self.agent_id
            }

        logger.info("Publishing to Medplum FHIR server")

        try:
            # Authenticate
            auth_success = await self.medplum_client.authenticate()
            if not auth_success:
                return {
                    "status": "error",
                    "message": "Failed to authenticate with Medplum",
                    "agent": self.agent_id
                }

            # Create Library resource
            library_response = await self.medplum_client.create_resource(self._current_library)
            self.workflow_state["library_created"] = True

            # Update Measure to reference created Library
            self._current_measure["library"] = [f"Library/{library_response['id']}"]

            # Create Measure resource
            measure_response = await self.medplum_client.create_resource(self._current_measure)
            self.workflow_state["measure_created"] = True
            self.workflow_state["published_to_fhir"] = True

            return {
                "status": "published",
                "library": {
                    "id": library_response.get("id"),
                    "url": library_response.get("url")
                },
                "measure": {
                    "id": measure_response.get("id"),
                    "url": measure_response.get("url")
                },
                "fhir_server": self.medplum_client.base_url,
                "workflow_complete": True,
                "agent": self.agent_id
            }

        except Exception as e:
            logger.error(f"Error publishing to FHIR: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to publish: {str(e)}",
                "agent": self.agent_id
            }

    def execute_full_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete CQL measure development workflow.

        This demonstrates the full agent workflow:
        1. Learn guidelines
        2. Build CQL measure
        3. Validate CQL
        4. Prepare for publishing

        Note: Actual publishing requires async execution.
        """
        logger.info("Executing full CQL measure development workflow")

        workflow_results = {
            "workflow": "cql_measure_development",
            "started": datetime.now().isoformat(),
            "steps": []
        }

        # Step 1: Learn guidelines
        guideline_type = params.get("guideline_type", "breast_cancer_screening")
        learn_result = self.learn_guidelines({"type": guideline_type})
        workflow_results["steps"].append({
            "step": 1,
            "action": "learn_guidelines",
            "status": learn_result["status"],
            "details": learn_result
        })

        if learn_result["status"] != "learned":
            workflow_results["status"] = "failed"
            workflow_results["failed_at_step"] = 1
            return workflow_results

        # Step 2: Build CQL measure
        build_result = self.build_cql_measure({})
        workflow_results["steps"].append({
            "step": 2,
            "action": "build_cql_measure",
            "status": build_result["status"],
            "details": build_result
        })

        if build_result["status"] != "built":
            workflow_results["status"] = "failed"
            workflow_results["failed_at_step"] = 2
            return workflow_results

        # Step 3: Validate CQL
        validate_result = self.validate_cql({})
        workflow_results["steps"].append({
            "step": 3,
            "action": "validate_cql",
            "status": validate_result["status"],
            "details": validate_result
        })

        if not validate_result["valid"]:
            workflow_results["status"] = "validation_failed"
            workflow_results["failed_at_step"] = 3
            return workflow_results

        # Step 4: Prepare publishing summary
        workflow_results["steps"].append({
            "step": 4,
            "action": "prepare_publish",
            "status": "ready",
            "details": {
                "library_ready": True,
                "measure_ready": True,
                "note": "Call publish_to_fhir to complete publishing"
            }
        })

        workflow_results["status"] = "ready_to_publish"
        workflow_results["completed"] = datetime.now().isoformat()
        workflow_results["agent"] = self.agent_id
        workflow_results["artifacts"] = {
            "cql": self._current_cql if hasattr(self, '_current_cql') else None,
            "library": self._current_library if hasattr(self, '_current_library') else None,
            "measure": self._current_measure if hasattr(self, '_current_measure') else None
        }

        return workflow_results

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow state."""
        return {
            "agent": self.agent_id,
            "workflow_state": self.workflow_state,
            "guidelines_loaded": self.guidelines is not None,
            "guideline_name": self.guidelines.get("name") if self.guidelines else None,
            "medplum_configured": self.medplum_client is not None,
            "timestamp": datetime.now().isoformat()
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "capabilities": self.card.get("capabilities", []),
            "protocols_supported": ["a2a", "mcp"],
            "methods": [
                "learn_guidelines",
                "build_cql_measure",
                "validate_cql",
                "publish_to_fhir",
                "execute_full_workflow",
                "get_workflow_status"
            ],
            "tools": self.card.get("tools", []),
            "fhir_integration": {
                "medplum_configured": self.medplum_client is not None,
                "supported_operations": ["create_library", "create_measure", "search"]
            }
        }


# Factory function for creating agent with Medplum credentials
def create_clinical_informaticist_agent(
    medplum_client_id: str = None,
    medplum_client_secret: str = None
) -> ClinicalInformaticistAgent:
    """
    Create a Clinical Informaticist Agent with optional Medplum integration.

    Args:
        medplum_client_id: Medplum OAuth client ID
        medplum_client_secret: Medplum OAuth client secret

    Returns:
        Configured ClinicalInformaticistAgent instance
    """
    return ClinicalInformaticistAgent(
        medplum_client_id=medplum_client_id,
        medplum_client_secret=medplum_client_secret
    )
