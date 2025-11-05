"""
Healthcare Agent Management API
Provides CRUD operations for agents with A2A compliance
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.agents.registry import (
    agent_registry,
    HealthcareAgent,
    AgentConstitution,
    AgentPlan,
    AgentCard,
    AgentSkill,
    create_breast_cancer_screening_agent
)

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "data" / "agent_templates"

router = APIRouter(prefix="/api/agents", tags=["agents"])


# Request/Response Models

class CreateAgentRequest(BaseModel):
    """Request to create a new agent"""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    purpose: str = Field(..., description="Agent purpose")
    domain: str = Field(..., description="Healthcare domain")
    role: str = Field(default="applicant", description="Agent role (applicant/administrator)")
    constitution: AgentConstitution
    plan: AgentPlan
    agent_card: AgentCard
    implementation_class: Optional[str] = None
    scenario_id: Optional[str] = None


class UpdateAgentRequest(BaseModel):
    """Request to update an agent"""
    name: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    domain: Optional[str] = None
    role: Optional[str] = None
    constitution: Optional[AgentConstitution] = None
    plan: Optional[AgentPlan] = None
    agent_card: Optional[AgentCard] = None
    status: Optional[str] = None
    version: Optional[str] = None


class AgentListResponse(BaseModel):
    """Response with list of agents"""
    agents: List[HealthcareAgent]
    total: int


class AgentResponse(BaseModel):
    """Single agent response"""
    agent: HealthcareAgent
    message: Optional[str] = None


# API Endpoints

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by status"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    role: Optional[str] = Query(None, description="Filter by role")
):
    """
    List all healthcare agents with optional filters
    """
    try:
        agents = agent_registry.list_agents(status=status, domain=domain, role=role)
        return AgentListResponse(agents=agents, total=len(agents))
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """
    Get a specific agent by ID
    """
    try:
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return AgentResponse(agent=agent)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(request: CreateAgentRequest):
    """
    Create a new healthcare agent
    """
    try:
        agent_data = request.model_dump()
        agent = agent_registry.create_agent(agent_data)
        return AgentResponse(agent=agent, message="Agent created successfully")
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, request: UpdateAgentRequest):
    """
    Update an existing agent
    """
    try:
        # Filter out None values
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        agent = agent_registry.update_agent(agent_id, updates)
        return AgentResponse(agent=agent, message="Agent updated successfully")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """
    Delete (archive) an agent
    """
    try:
        success = agent_registry.delete_agent(agent_id)
        if success:
            return {"message": f"Agent {agent_id} archived successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to archive agent")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/card")
async def get_agent_card(agent_id: str):
    """
    Get A2A-compliant agent card for discovery
    """
    try:
        card = agent_registry.get_agent_card(agent_id)
        if not card:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return card
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/activate")
async def activate_agent(agent_id: str):
    """
    Activate an agent
    """
    try:
        agent = agent_registry.update_agent(agent_id, {"status": "active"})
        return AgentResponse(agent=agent, message="Agent activated successfully")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/deactivate")
async def deactivate_agent(agent_id: str):
    """
    Deactivate an agent
    """
    try:
        agent = agent_registry.update_agent(agent_id, {"status": "inactive"})
        return AgentResponse(agent=agent, message="Agent deactivated successfully")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deactivating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/samples/bcse", response_model=AgentResponse, status_code=201)
async def create_bcse_sample():
    """
    Create the Breast Cancer Screening Eligibility sample agent
    """
    try:
        # Check if already exists
        existing = agent_registry.get_agent("bcse_agent_001")
        if existing:
            return AgentResponse(
                agent=existing,
                message="BCS-E sample agent already exists"
            )

        agent = create_breast_cancer_screening_agent()
        return AgentResponse(
            agent=agent,
            message="BCS-E sample agent created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating BCS-E sample agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/constitution")
async def get_agent_constitution(agent_id: str):
    """
    Get agent constitution (spec-kit driven development)
    """
    try:
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return agent.constitution.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent constitution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/plan")
async def get_agent_plan(agent_id: str):
    """
    Get agent operational plan
    """
    try:
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return agent.plan.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/list")
async def list_domains():
    """
    List available healthcare domains
    """
    return {
        "domains": [
            {"id": "preventive_screening", "name": "Preventive Screening", "description": "Cancer screening and prevention"},
            {"id": "clinical_trial", "name": "Clinical Trial", "description": "Clinical trial enrollment"},
            {"id": "referral_specialist", "name": "Specialist Referral", "description": "Specialist referral coordination"},
            {"id": "prior_auth", "name": "Prior Authorization", "description": "Prior authorization processing"},
            {"id": "chronic_care", "name": "Chronic Care", "description": "Chronic disease management"},
            {"id": "emergency_care", "name": "Emergency Care", "description": "Emergency care triage"},
            {"id": "mental_health", "name": "Mental Health", "description": "Mental health services"},
            {"id": "pharmacy", "name": "Pharmacy", "description": "Pharmacy benefits management"}
        ]
    }


@router.get("/templates/list")
async def list_templates():
    """
    List available agent templates from JSON files
    """
    try:
        templates = []

        if TEMPLATES_DIR.exists():
            for template_file in TEMPLATES_DIR.glob("*.json"):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        templates.append({
                            "id": template_data.get("id"),
                            "name": template_data.get("name"),
                            "domain": template_data.get("domain"),
                            "description": template_data.get("description"),
                            "role": template_data.get("role"),
                            "tags": template_data.get("tags", [])
                        })
                except Exception as e:
                    logger.warning(f"Failed to load template {template_file}: {e}")
                    continue

        return {"templates": templates, "count": len(templates)}
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """
    Get a specific agent template by ID
    """
    try:
        if not TEMPLATES_DIR.exists():
            raise HTTPException(status_code=404, detail="Templates directory not found")

        # Find template file
        for template_file in TEMPLATES_DIR.glob("*.json"):
            with open(template_file, 'r') as f:
                template_data = json.load(f)
                if template_data.get("id") == template_id:
                    return template_data

        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/instantiate", response_model=AgentResponse, status_code=201)
async def create_agent_from_template(
    template_id: str,
    customizations: Optional[Dict[str, Any]] = Body(default={})
):
    """
    Create a new agent from a template with optional customizations

    Customizations can override:
    - name: Agent name
    - description: Agent description
    - Any other top-level fields
    """
    try:
        # Load template
        template_data = None
        if TEMPLATES_DIR.exists():
            for template_file in TEMPLATES_DIR.glob("*.json"):
                with open(template_file, 'r') as f:
                    data = json.load(f)
                    if data.get("id") == template_id:
                        template_data = data
                        break

        if not template_data:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        # Create agent data from template
        agent_data = {
            "name": template_data["name"],
            "description": template_data["description"],
            "purpose": template_data["purpose"],
            "domain": template_data["domain"],
            "role": template_data["role"],
            "constitution": template_data["constitution"],
            "plan": template_data["plan"],
            "agent_card": template_data["agent_card"],
            "version": template_data.get("version", "1.0.0"),
            "status": "active"  # Templates start as active
        }

        # Apply customizations
        if customizations:
            agent_data.update(customizations)
            # If name was customized, also update agent_card name
            if "name" in customizations:
                agent_data["agent_card"]["name"] = customizations["name"]

        # Create agent
        agent = agent_registry.create_agent(agent_data)

        return AgentResponse(
            agent=agent,
            message=f"Agent created from template '{template_id}'"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent from template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
