"""
Healthcare Agent Registry System
Manages dynamic agent creation, lifecycle, and discovery with A2A compliance
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Agent storage path
AGENTS_DIR = Path(__file__).parent.parent / "data" / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)


class AgentConstitution(BaseModel):
    """Agent constitution based on spec-kit driven development"""
    purpose: str = Field(..., description="Primary purpose of the agent")
    domain: str = Field(..., description="Healthcare domain (e.g., screening, diagnosis, referral)")
    constraints: List[str] = Field(default_factory=list, description="Operational constraints")
    ethics: List[str] = Field(default_factory=list, description="Ethical guidelines")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")


class AgentPlan(BaseModel):
    """Agent operational plan"""
    goals: List[str] = Field(default_factory=list, description="Primary goals")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="Task definitions")
    workflows: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow definitions")
    success_criteria: List[str] = Field(default_factory=list, description="Success metrics")


class AgentSkill(BaseModel):
    """A2A-compliant skill definition"""
    name: str
    description: str
    type: str = "discovery"
    scenario: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    a2a: Dict[str, str] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """A2A-compliant agent card"""
    protocolVersion: str = "0.2.9"
    preferredTransport: str = "JSONRPC"
    name: str
    description: str
    role: str
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    skills: List[AgentSkill] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    supported_formats: List[str] = Field(default_factory=list)


class HealthcareAgent(BaseModel):
    """Healthcare Agent Definition"""
    id: str
    name: str
    description: str
    purpose: str
    domain: str
    role: str = "applicant"  # applicant or administrator

    # ADK Components
    constitution: AgentConstitution
    plan: AgentPlan

    # A2A Compliance
    agent_card: AgentCard

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "system"
    version: str = "1.0.0"
    status: str = "active"  # active, inactive, archived

    # Implementation
    implementation_class: Optional[str] = None  # Python class path if custom implementation
    scenario_id: Optional[str] = None  # Link to scenario


class AgentRegistry:
    """Central registry for healthcare agents"""

    def __init__(self):
        self.agents: Dict[str, HealthcareAgent] = {}
        self._load_all_agents()
        logger.info(f"Agent Registry initialized with {len(self.agents)} agents")

    def _load_all_agents(self):
        """Load all agents from storage"""
        try:
            for agent_file in AGENTS_DIR.glob("*.json"):
                with open(agent_file, 'r') as f:
                    agent_data = json.load(f)
                    agent = HealthcareAgent(**agent_data)
                    self.agents[agent.id] = agent
        except Exception as e:
            logger.error(f"Error loading agents: {e}")

    def create_agent(self, agent_data: Dict[str, Any]) -> HealthcareAgent:
        """Create a new healthcare agent"""
        try:
            # Generate ID if not provided
            if 'id' not in agent_data:
                agent_data['id'] = f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create agent
            agent = HealthcareAgent(**agent_data)

            # Save to storage
            self._save_agent(agent)

            # Add to registry
            self.agents[agent.id] = agent

            logger.info(f"Created agent: {agent.id} - {agent.name}")
            return agent

        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise

    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> HealthcareAgent:
        """Update an existing agent"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")

        try:
            agent = self.agents[agent_id]
            agent_dict = agent.model_dump()
            agent_dict.update(updates)
            agent_dict['updated_at'] = datetime.now().isoformat()

            updated_agent = HealthcareAgent(**agent_dict)

            self._save_agent(updated_agent)
            self.agents[agent_id] = updated_agent

            logger.info(f"Updated agent: {agent_id}")
            return updated_agent

        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            raise

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent (soft delete - marks as archived)"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")

        try:
            self.update_agent(agent_id, {"status": "archived"})
            logger.info(f"Archived agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[HealthcareAgent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)

    def list_agents(self,
                   status: Optional[str] = None,
                   domain: Optional[str] = None,
                   role: Optional[str] = None) -> List[HealthcareAgent]:
        """List agents with optional filters"""
        agents = list(self.agents.values())

        if status:
            agents = [a for a in agents if a.status == status]
        if domain:
            agents = [a for a in agents if a.domain == domain]
        if role:
            agents = [a for a in agents if a.role == role]

        return agents

    def get_agent_card(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get A2A agent card for an agent"""
        agent = self.get_agent(agent_id)
        if agent:
            return agent.agent_card.model_dump()
        return None

    def _save_agent(self, agent: HealthcareAgent):
        """Save agent to storage"""
        try:
            agent_path = AGENTS_DIR / f"{agent.id}.json"
            with open(agent_path, 'w') as f:
                json.dump(agent.model_dump(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving agent: {e}")
            raise


# Global registry instance
agent_registry = AgentRegistry()


def create_breast_cancer_screening_agent() -> HealthcareAgent:
    """
    Create the Breast Cancer Screening Eligibility (BCS-E) agent
    This serves as a template for other healthcare agents
    """
    constitution = AgentConstitution(
        purpose="Determine eligibility for breast cancer screening benefits",
        domain="preventive_screening",
        constraints=[
            "Must follow USPSTF guidelines for breast cancer screening",
            "Age range: 50-74 years for routine screening",
            "Must verify recent mammogram history (within 27 months)",
            "Gender requirement: Female patients only for mammography screening"
        ],
        ethics=[
            "Prioritize patient safety and appropriate care",
            "Ensure equitable access to screening services",
            "Protect patient privacy and data confidentiality",
            "Provide clear explanations for eligibility decisions"
        ],
        capabilities=[
            "FHIR R4 resource processing",
            "Age calculation from birthDate",
            "Mammogram history verification",
            "QuestionnaireResponse generation",
            "Decision artifact creation"
        ]
    )

    plan = AgentPlan(
        goals=[
            "Accurately determine BCS-E eligibility based on clinical criteria",
            "Generate compliant FHIR artifacts for decisions",
            "Provide transparent rationale for all determinations",
            "Support both A2A and MCP protocol interactions"
        ],
        tasks=[
            {
                "id": "load_patient_data",
                "description": "Load patient FHIR bundle",
                "inputs": ["patient_id"],
                "outputs": ["fhir_bundle"]
            },
            {
                "id": "extract_demographics",
                "description": "Extract age, gender, and demographics",
                "inputs": ["fhir_bundle"],
                "outputs": ["age", "gender", "birthdate"]
            },
            {
                "id": "check_mammogram_history",
                "description": "Verify recent mammogram procedures",
                "inputs": ["fhir_bundle"],
                "outputs": ["last_mammogram_date", "abstraction_used"]
            },
            {
                "id": "evaluate_eligibility",
                "description": "Apply BCS-E criteria",
                "inputs": ["age", "gender", "last_mammogram_date"],
                "outputs": ["decision", "criteria_met"]
            },
            {
                "id": "generate_artifacts",
                "description": "Create decision artifacts",
                "inputs": ["decision", "rationale", "resources_used"],
                "outputs": ["decision_bundle", "artifacts"]
            }
        ],
        workflows=[
            {
                "name": "eligibility_determination",
                "steps": [
                    "load_patient_data",
                    "extract_demographics",
                    "check_mammogram_history",
                    "evaluate_eligibility",
                    "generate_artifacts"
                ]
            }
        ],
        success_criteria=[
            "Decision accuracy >= 95%",
            "Response time < 2 seconds",
            "FHIR compliance 100%",
            "Clear rationale provided for all decisions"
        ]
    )

    agent_card = AgentCard(
        name="BCS-E Eligibility Agent",
        description="Breast Cancer Screening Eligibility determination with FHIR validation",
        role="administrator",
        capabilities={
            "streaming": True,
            "protocols": ["A2A", "MCP"],
            "fhir": True,
            "ai_transparency": True
        },
        skills=[
            AgentSkill(
                name="bcse_eligibility_determination",
                description="Validate BCS-E eligibility criteria and generate decision artifacts",
                type="discovery",
                scenario="healthcare_eligibility",
                inputs=["questionnaire_response", "patient_resource"],
                outputs=["decision_text", "artifacts", "rationale"],
                a2a={"config64": "YmNzZS1hZ2VudA=="}
            )
        ],
        methods=["requirements_message", "validate", "finalize", "load_patient", "answer_requirements"],
        supported_formats=["application/fhir+json", "application/json"]
    )

    agent_data = {
        "id": "bcse_agent_001",
        "name": "BCS-E Eligibility Agent",
        "description": "Determines eligibility for breast cancer screening benefits based on USPSTF guidelines",
        "purpose": "Automate breast cancer screening eligibility determinations",
        "domain": "preventive_screening",
        "role": "administrator",
        "constitution": constitution.model_dump(),
        "plan": plan.model_dump(),
        "agent_card": agent_card.model_dump(),
        "implementation_class": "app.agents.administrator.AdministratorAgent",
        "scenario_id": "bcse",
        "version": "1.0.0",
        "status": "active"
    }

    return agent_registry.create_agent(agent_data)
