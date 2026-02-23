"""
Configuration management for the Evolutionary Hub.
Uses environment variables with Pydantic validation for type safety.
"""
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

class ModuleConfig(BaseModel):
    """Configuration for individual modules"""
    module_id: str = Field(..., min_length=3)
    domain: str = Field(..., description="Domain category of the module")
    version: str = Field(default="1.0.0")
    dependencies: List[str] = Field(default_factory=list)
    evolution_strategy: str = Field(default="gradient", choices=["gradient", "genetic", "reinforcement"])
    update_frequency_minutes: int = Field(default=60, ge=5)
    
    @validator('dependencies')
    def validate_dependencies(cls, v):
        """Ensure no circular dependencies"""
        for dep in v:
            if dep == cls.module_id:
                raise ValueError(f"Module cannot depend on itself: {dep}")
        return v

class HubConfig(BaseSettings):
    """Main hub configuration with environment variable support"""
    # Firebase Configuration
    firebase_project_id: str = Field(..., env="FIREBASE_PROJECT_ID")
    firebase_credentials_path: Optional[str] = Field(None, env="FIREBASE_CREDENTIALS_PATH")
    
    # Evolution Engine
    evolution_cycle_hours: int = Field(default=24, ge=1)
    performance_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_concurrent_evolutions: int = Field(default=5, ge=1)
    
    # Middleware
    middleware_port: int = Field(default=8000, ge=1024, le=65535)
    message_timeout_seconds: int = Field(default=30, ge=5)
    max_retry_attempts: int = Field(default=3, ge=0)
    
    # Module Registry
    modules: Dict[str, ModuleConfig] = Field(default_factory=dict)
    
    # Logging
    log_level: str = Field(default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

def initialize_firebase(config: HubConfig) -> firestore.Client:
    """
    Initialize Firebase connection with robust error handling
    
    Args:
        config: Hub configuration object
        
    Returns:
        Initialized Firestore client
        
    Raises:
        ValueError: If credentials are invalid
        RuntimeError: If Firebase initialization fails
    """
    try:
        # Check if Firebase app is already initialized
        if firebase_admin._apps:
            logger.info("Firebase already initialized, returning existing client")
            return firestore.client()
        
        creds = None
        
        # Try credentials path first
        if config.firebase_credentials_path:
            cred_path = Path(config.firebase_credentials_path)
            if cred_path.exists():
                creds = credentials.Certificate(str(cred_path))
                logger.info(f"Using Firebase credentials from file: {cred_path}")
            else:
                logger.warning(f"Credentials file not found: {cred_path}")
        
        # Fallback to application default credentials
        if not creds:
            logger.info("Using Firebase application default credentials")
            creds = credentials.ApplicationDefault()
        
        # Initialize Firebase app
        firebase_admin.initialize_app(
            creds,
            {'projectId': config.firebase_project_id}
        )
        
        logger.info("Firebase initialized successfully")
        return firestore.client()
        
    except Exception as e:
        logger.error("Firebase initialization failed", error=str(e))
        raise RuntimeError(f"Firebase initialization failed: {e}")

# Global configuration instance
_config = None

def get_config() -> HubConfig:
    """Singleton pattern for configuration"""
    global _config
    if _config is None:
        _config = HubConfig()
        logger.info("Configuration loaded", config=_config.dict(exclude={'firebase_credentials_path'}))
    return _config