"""
Configuration management for the Agent Framework application.

This module handles application settings, environment variables,
and configuration loading from various sources.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    # Application settings
    APP_TITLE: str = ".NET Agent Framework AI Agent System"
    APP_VERSION: str = "2.0.0"
    FRONTEND_URL: Optional[str] = Field(default="*", alias="FRONTEND_URL")
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")
    ENVIRONMENT: str = Field(default="Production", alias="ENVIRONMENT")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # Azure OpenAI configuration
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT_NAME")
    AZURE_OPENAI_API_KEY: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-02-01", alias="AZURE_OPENAI_API_VERSION")
    
    # Azure AI Foundry configuration
    PROJECT_ENDPOINT: Optional[str] = Field(default=None, alias="PROJECT_ENDPOINT")
    AZURE_AI_PROJECT_ENDPOINT: Optional[str] = Field(default=None, alias="PROJECT_ENDPOINT")  # Alias for official SDK
    AZURE_AI_MODEL_DEPLOYMENT_NAME: Optional[str] = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT_NAME")  # Alias for official SDK
    PEOPLE_AGENT_ID: Optional[str] = Field(default=None, alias="PEOPLE_AGENT_ID")
    KNOWLEDGE_AGENT_ID: Optional[str] = Field(default=None, alias="KNOWLEDGE_AGENT_ID")
    
    # AWS Bedrock configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", alias="AWS_REGION")
    AWS_BEDROCK_MODEL_ID: str = Field(default="amazon.nova-pro-v1:0", alias="AWS_BEDROCK_MODEL_ID")
    AWS_BEDROCK_AGENT_ID: Optional[str] = Field(default=None, alias="AWS_BEDROCK_AGENT_ID")
    
    # Google Gemini configuration
    GOOGLE_API_KEY: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    GOOGLE_GEMINI_MODEL_ID: str = Field(default="gemini-2.0-flash", alias="GOOGLE_GEMINI_MODEL_ID")
    
    # Azure AI Content Safety configuration
    AZURE_CONTENT_SAFETY_ENDPOINT: Optional[str] = Field(default=None, alias="CONTENT_SAFETY_ENDPOINT")
    AZURE_CONTENT_SAFETY_KEY: Optional[str] = Field(default=None, alias="CONTENT_SAFETY_API_KEY")
    CONTENT_SAFETY_ENABLED: bool = Field(default=True, alias="CONTENT_SAFETY_ENABLED")
    CONTENT_SAFETY_SEVERITY_THRESHOLD: int = Field(default=5, alias="CONTENT_SAFETY_SEVERITY_THRESHOLD")  # Legacy single threshold (0-7)
    
    # Per-category thresholds (matching .NET implementation)
    CONTENT_SAFETY_THRESHOLD_HATE: int = Field(default=4, alias="CONTENT_SAFETY_THRESHOLD_HATE")
    CONTENT_SAFETY_THRESHOLD_SELFHARM: int = Field(default=4, alias="CONTENT_SAFETY_THRESHOLD_SELFHARM")
    CONTENT_SAFETY_THRESHOLD_SEXUAL: int = Field(default=4, alias="CONTENT_SAFETY_THRESHOLD_SEXUAL")
    CONTENT_SAFETY_THRESHOLD_VIOLENCE: int = Field(default=4, alias="CONTENT_SAFETY_THRESHOLD_VIOLENCE")
    
    # Input/Output filtering options
    CONTENT_SAFETY_BLOCK_UNSAFE_INPUT: bool = Field(default=True, alias="CONTENT_SAFETY_BLOCK_UNSAFE_INPUT")
    CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT: bool = Field(default=True, alias="CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT")
    
    # Blocklists support (comma-separated blocklist names)
    CONTENT_SAFETY_BLOCKLISTS: Optional[str] = Field(default=None, alias="CONTENT_SAFETY_BLOCKLISTS")
    
    # Output filtering actions: "redact", "placeholder", "empty"
    CONTENT_SAFETY_OUTPUT_ACTION: str = Field(default="redact", alias="CONTENT_SAFETY_OUTPUT_ACTION")
    CONTENT_SAFETY_PLACEHOLDER_TEXT: str = Field(
        default="[Content removed due to safety policy]", 
        alias="CONTENT_SAFETY_PLACEHOLDER_TEXT"
    )
    
    # Legacy aliases for backwards compatibility
    CONTENT_SAFETY_THRESHOLD: int = Field(default=4, alias="CONTENT_SAFETY_THRESHOLD")
    BLOCK_UNSAFE_INPUT: bool = Field(default=True, alias="BLOCK_UNSAFE_INPUT")
    FILTER_UNSAFE_OUTPUT: bool = Field(default=True, alias="FILTER_UNSAFE_OUTPUT")
    
    # Session management
    SESSION_STORAGE_TYPE: str = Field(default="file", alias="SESSION_STORAGE_TYPE")
    SESSION_STORAGE_PATH: str = Field(default="./sessions", alias="SESSION_STORAGE_PATH")
    REDIS_URL: Optional[str] = Field(default=None, alias="REDIS_URL")
    SESSION_CLEANUP_INTERVAL_HOURS: int = 24
    SESSION_MAX_AGE_DAYS: int = 7
    
    # Long-running memory feature
    ENABLE_LONG_RUNNING_MEMORY: bool = Field(default=False, alias="ENABLE_LONG_RUNNING_MEMORY")
    
    # Caching
    CACHE_ENABLED: bool = True
    CACHE_MAX_SIZE: int = 1000
    CACHE_TTL_SECONDS: int = 3600
    
    # Agent configurations (loaded from YAML)
    agents_config: Dict[str, Any] = {}
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_yaml_config()
    
    def _load_yaml_config(self):
        """Load agent configurations from YAML file."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config.yml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config and "agents" in yaml_config:
                        self.agents_config = yaml_config["agents"]
        except Exception as e:
            print(f"Warning: Could not load YAML config: {e}")
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent."""
        return self.agents_config.get(agent_name, {})
    
    def get_agent_instructions(self, agent_name: str) -> str:
        """Get instructions for a specific agent."""
        config = self.get_agent_config(agent_name)
        return config.get("instructions", "")
    
    def get_agent_description(self, agent_name: str) -> str:
        """Get description for a specific agent."""
        config = self.get_agent_config(agent_name)
        return config.get("description", "")


# Global settings instance
settings = Settings()