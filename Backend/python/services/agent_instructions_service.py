"""
Agent Instructions Service for loading agent configurations from config.yml.

Matches .NET AgentInstructionsService pattern.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

logger = logging.getLogger(__name__)


class AgentInstructionsService:
    """
    Service for loading agent instructions and descriptions from config.yml.
    
    Matches .NET AgentInstructionsService structure.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the instructions service with config file path."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yml"
        
        self._config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
        
        logger.info(f"AgentInstructionsService initialized from {self._config_path}")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Loaded config from {self._config_path}")
            else:
                logger.warning(f"Config file not found: {self._config_path}")
                self._config = {}
        except Exception as ex:
            logger.error(f"Failed to load config: {str(ex)}")
            self._config = {}
    
    def get_agent_instructions(self, agent_name: str) -> str:
        """
        Get the instructions for a specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., 'azure_openai_agent', 'bedrock_agent')
            
        Returns:
            Agent instructions string, or default instructions if not found.
        """
        agents_config = self._config.get("agents", {})
        agent_config = agents_config.get(agent_name, {})
        
        instructions = agent_config.get("instructions", "")
        
        if not instructions:
            # Return default instructions
            instructions = f"You are a helpful AI assistant named {agent_name}."
            logger.debug(f"Using default instructions for agent: {agent_name}")
        
        return instructions
    
    def get_agent_description(self, agent_name: str) -> str:
        """
        Get the description for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent description string, or default description if not found.
        """
        agents_config = self._config.get("agents", {})
        agent_config = agents_config.get(agent_name, {})
        
        # Check metadata for description first
        metadata = agent_config.get("metadata", {})
        description = metadata.get("description", "")
        
        if not description:
            description = agent_config.get("description", f"AI Agent: {agent_name}")
        
        return description
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """
        Check if an agent is enabled in the configuration.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if agent is enabled (default), False if explicitly disabled.
        """
        agents_config = self._config.get("agents", {})
        agent_config = agents_config.get(agent_name, {})
        
        return agent_config.get("enabled", True)
    
    def get_agent_metadata(self, agent_name: str) -> Dict[str, Any]:
        """
        Get all metadata for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary of agent metadata.
        """
        agents_config = self._config.get("agents", {})
        agent_config = agents_config.get(agent_name, {})
        
        return agent_config.get("metadata", {})
    
    def get_azure_openai_config(self) -> Dict[str, Any]:
        """Get Azure OpenAI configuration."""
        return self._config.get("azure_openai", {})
    
    def get_ms_foundry_config(self) -> Dict[str, Any]:
        """Get Microsoft Foundry configuration."""
        return self._config.get("ms_foundry", {})
    
    def get_all_agent_names(self) -> list:
        """Get list of all configured agent names."""
        agents_config = self._config.get("agents", {})
        return list(agents_config.keys())

