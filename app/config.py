from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import date
import os, json, base64

CONFIG_PATH = os.getenv("APP_CONFIG_PATH", "app/config.runtime.json")

class ScenarioConfig(BaseModel):
    # Which scenario is active and scenario-specific options
    active: Literal["bcse", "clinical_trial", "referral_specialist", "prior_auth", "custom"] = "bcse"
    options: Dict[str, Any] = Field(default_factory=dict)

class ProtocolConfig(BaseModel):
    # Which transport to show by default in the UI
    default_transport: Literal["a2a", "mcp"] = "a2a"
    # Public base URL stub for A2A discovery (can be empty in Replit)
    public_base_url: Optional[str] = None

class OperationMode(BaseModel):
    # Applicant-only = client; Administrator-only = server; Full-stack = both
    role: Literal["applicant_only", "administrator_only", "full_stack"] = "full_stack"

class DataSources(BaseModel):
    # Where Applicant reads data from
    allow_fhir_mcp: bool = True
    allow_local_bundle: bool = True
    allow_free_text_context: bool = True

class Simulation(BaseModel):
    measurement_date: Optional[date] = None
    # latency/error injection to simulate "admin evaluating rules"
    admin_processing_ms: int = 1200
    error_injection_rate: float = 0.0  # 0..1
    capacity_limit: Optional[int] = None  # used by referral/prior-auth demos

class LoggingConfig(BaseModel):
    level: Literal["DEBUG","INFO","WARN","ERROR"] = "INFO"
    persist_transcript: bool = True

class ConnectathonConfig(BaseModel):
    mode: OperationMode = OperationMode()
    protocol: ProtocolConfig = ProtocolConfig()
    scenario: ScenarioConfig = ScenarioConfig()
    data: DataSources = DataSources()
    simulation: Simulation = Simulation()
    logging: LoggingConfig = LoggingConfig()
    tags: List[str] = Field(default_factory=lambda: ["connectathon", "demo"])

def load_config() -> ConnectathonConfig:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return ConnectathonConfig(**json.load(f))
    cfg = ConnectathonConfig()
    save_config(cfg)
    return cfg

def save_config(cfg: ConnectathonConfig) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(json.loads(cfg.model_dump_json()), f, indent=2)

def update_config(patch: Dict[str, Any]) -> ConnectathonConfig:
    current = load_config()
    merged = json.loads(current.model_dump_json())
    # shallow merge (sufficient for demo); nested keys can be patched via dotted keys in UI later
    merged.update(patch)
    new = ConnectathonConfig(**merged)
    save_config(new)
    return new