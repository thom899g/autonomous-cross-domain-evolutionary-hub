"""
Base Module class for the Evolutionary Hub.
All domain-specific modules must inherit from this base class.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import uuid
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog
import numpy as np
from pydantic import BaseModel, Field

from config import get_config, logger
from utils.exceptions import ModuleError, EvolutionError

@dataclass
class PerformanceMetrics:
    """Performance tracking for modules"""
    accuracy: float = 0.0
    latency_ms: float = 0.0
    resource_usage: float = 0.0
    error_rate: float = 0.0
    uptime_percentage: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'accuracy': self.accuracy,
            'latency_ms': self.latency_ms,
            'resource_usage': self.resource_usage,
            'error_rate': self.error_rate,
            'uptime_percentage': self.uptime_percentage,
            'last_updated': self.last_updated.isoformat()
        }

class ModuleMetadata(BaseModel):
    """Module metadata for registration and discovery"""
    module_id: str
    module_name: str
    domain: str
    version: str
    status: str = Field(default="INACTIVE", choices=["INACTIVE", "ACTIVE", "EVOLVING", "ERROR"])
    dependencies: List[str] = Field(default