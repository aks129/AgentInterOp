from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import os
from app.config import CONFIG_PATH


class SchedulingConfig(BaseModel):
    """Configuration for SMART Scheduling Links integration."""
    
    publishers: List[str] = Field(
        default_factory=list,
        description="List of base URLs for bulk publishers (each must support /$bulk-publish)"
    )
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache TTL for publisher data in seconds"
    )
    default_specialty: Optional[str] = Field(
        default="mammography",
        description="Default specialty for filtering (e.g., 'mammography')"
    )
    default_radius_km: Optional[int] = Field(
        default=50,
        description="Default search radius in kilometers"
    )
    default_timezone: Optional[str] = Field(
        default="America/New_York",
        description="Default timezone for slot display"
    )


def get_scheduling_config() -> SchedulingConfig:
    """Load scheduling configuration from the existing config system."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                full_config = json.load(f)
                scheduling_data = full_config.get("scheduling", {})
                return SchedulingConfig(**scheduling_data)
    except Exception as e:
        print(f"[WARN] Scheduling config load failed: {e}")
    
    # Return default config
    return SchedulingConfig()


def save_scheduling_config(config: SchedulingConfig) -> None:
    """Save scheduling configuration to the existing config system."""
    try:
        # Load full config
        full_config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                full_config = json.load(f)
        
        # Update scheduling section
        full_config["scheduling"] = json.loads(config.model_dump_json())
        
        # Save back to file
        with open(CONFIG_PATH, "w") as f:
            json.dump(full_config, f, indent=2)
            
    except Exception as e:
        print(f"[WARN] Scheduling config save failed: {e}")


def update_scheduling_config(patch: Dict[str, Any]) -> SchedulingConfig:
    """Update scheduling configuration with partial data."""
    current = get_scheduling_config()
    merged = json.loads(current.model_dump_json())
    merged.update(patch)
    new_config = SchedulingConfig(**merged)
    save_scheduling_config(new_config)
    return new_config