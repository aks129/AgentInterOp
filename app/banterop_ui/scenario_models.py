"""Pydantic models for Banterop-style scenarios"""
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field


class ScenarioMetadata(BaseModel):
    """Scenario metadata"""
    id: str = Field(..., description="Unique scenario identifier")
    name: Optional[str] = Field(None, description="Human readable name")
    description: Optional[str] = Field(None, description="Scenario description")
    version: Optional[str] = Field("1.0.0", description="Scenario version")
    tags: Optional[List[str]] = Field(default_factory=list, description="Scenario tags")


class ScenarioTool(BaseModel):
    """Tool definition for scenarios"""
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tool parameters schema")
    # Allow unknown fields for tool extensions
    
    class Config:
        extra = "allow"


class ScenarioKB(BaseModel):
    """Knowledge base entry for scenarios"""
    id: str = Field(..., description="KB entry identifier")
    type: Optional[str] = Field("text", description="KB entry type")
    content: str = Field(..., description="KB content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="KB metadata")
    
    class Config:
        extra = "allow"


class ScenarioAgent(BaseModel):
    """Agent definition for scenarios"""
    agentId: str = Field(..., description="Agent identifier")
    name: Optional[str] = Field(None, description="Agent name")
    role: Optional[str] = Field(None, description="Agent role")
    systemPrompt: str = Field(..., description="System prompt for the agent")
    goals: Optional[List[str]] = Field(default_factory=list, description="Agent goals")
    tools: Optional[List[Union[str, ScenarioTool]]] = Field(default_factory=list, description="Available tools")
    knowledgeBase: Optional[List[Union[str, ScenarioKB]]] = Field(default_factory=list, description="Knowledge base")
    messageToUseWhenInitiatingConversation: Optional[str] = Field(None, description="Initial message template")
    capabilities: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent capabilities")
    
    class Config:
        extra = "allow"


class Scenario(BaseModel):
    """Complete scenario definition"""
    metadata: ScenarioMetadata = Field(..., description="Scenario metadata")
    agents: List[ScenarioAgent] = Field(..., description="Scenario agents")
    tools: Optional[List[ScenarioTool]] = Field(default_factory=list, description="Global tools")
    knowledgeBase: Optional[List[ScenarioKB]] = Field(default_factory=list, description="Global knowledge base")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Scenario settings")
    
    class Config:
        extra = "allow"
    
    def get_agent_by_id(self, agent_id: str) -> Optional[ScenarioAgent]:
        """Get agent by ID"""
        for agent in self.agents:
            if agent.agentId == agent_id:
                return agent
        return None
    
    def get_agent_ids(self) -> List[str]:
        """Get list of all agent IDs"""
        return [agent.agentId for agent in self.agents]


class RunConfig(BaseModel):
    """Configuration for a scenario run"""
    scenarioUrl: str = Field(..., description="URL to scenario JSON")
    myAgentId: str = Field(..., description="Local agent ID to use")
    remoteAgentCardUrl: Optional[str] = Field(None, description="Remote agent card URL")
    conversationMode: str = Field("remote", description="local or remote")
    fhir: Optional[Dict[str, Any]] = Field(default_factory=dict, description="FHIR configuration")
    bcse: Optional[Dict[str, Any]] = Field(default_factory=dict, description="BCS evaluation settings")
    
    class Config:
        extra = "allow"


class RunContext(BaseModel):
    """Runtime context for a scenario run"""
    runId: str = Field(..., description="Unique run identifier")
    config: RunConfig = Field(..., description="Run configuration")
    scenario: Optional[Scenario] = Field(None, description="Loaded scenario")
    remoteAgentCard: Optional[Dict[str, Any]] = Field(None, description="Remote agent card")
    remoteA2aUrl: Optional[str] = Field(None, description="Resolved A2A URL")
    taskId: Optional[str] = Field(None, description="A2A task ID")
    status: str = Field("initialized", description="Run status")
    transcript: List[Dict[str, Any]] = Field(default_factory=list, description="Message history")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")
    fhirFacts: Optional[Dict[str, Any]] = Field(None, description="FHIR patient facts")
    bcsEvaluation: Optional[Dict[str, Any]] = Field(None, description="BCS evaluation result")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        extra = "allow"