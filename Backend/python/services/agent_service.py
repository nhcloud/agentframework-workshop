"""
Agent service for managing agent instances and operations.

This service handles agent creation, management, and execution,
similar to the .NET AgentService.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from agents import create_agent, AVAILABLE_AGENTS
from models.chat_models import AgentInfo


logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing agent instances and operations.
    
    This service provides functionality to:
    - Create and manage agent instances
    - Execute agent operations
    - Track agent availability and status
    """
    
    def __init__(self):
        """Initialize the agent service."""
        self._agents: Dict[str, Any] = {}  # Using Any since we have different agent types
        self._agent_cache: Dict[str, Any] = {}
        logger.info("AgentService initialized using Microsoft Agent Framework")
    
    async def get_agent(self, agent_name: str):
        """
        Get an agent instance by name using Microsoft Agent Framework.
        
        Args:
            agent_name: The name of the agent to retrieve
            
        Returns:
            The agent instance or None if not found
        """
        try:
            # Check if agent is already cached and has required attributes
            if agent_name in self._agents:
                cached_agent = self._agents[agent_name]
                # Ensure cached agent has both agent_type and agent attributes
                if hasattr(cached_agent, 'agent_type') and hasattr(cached_agent, 'agent') and cached_agent.agent is not None:
                    logger.debug(f"Returning cached agent: {agent_name}")
                    return cached_agent
                else:
                    # Remove outdated cached agent
                    logger.warning(f"Removing invalid cached agent {agent_name} (missing agent_type or agent attribute)")
                    del self._agents[agent_name]
            
            # Create new agent instance
            agent = create_agent(agent_name)
            
            # Initialize the agent (async for Azure AI agents, sync for others)
            if hasattr(agent, 'initialize') and hasattr(agent.initialize, '__call__'):
                if agent_name in ['people_lookup', 'knowledge_finder']:
                    await agent.initialize()  # Async initialize for Azure AI agents
                else:
                    agent.initialize()  # Sync initialize for generic, bedrock, and gemini agents
            
            # Ensure agent has required attributes for group chat compatibility
            if not hasattr(agent, 'agent_type'):
                logger.error(f"Agent {agent_name} missing required agent_type attribute")
                raise AttributeError(f"Agent {agent_name} is missing agent_type attribute")
            
            if not hasattr(agent, 'agent'):
                logger.error(f"Agent {agent_name} missing required agent attribute")
                raise AttributeError(f"Agent {agent_name} is missing agent attribute")
            
            if agent.agent is None:
                logger.error(f"Agent {agent_name} has agent attribute but it is None")
                raise ValueError(f"Agent {agent_name} agent attribute is None - initialization may have failed")
            
            # Cache the agent
            self._agents[agent_name] = agent
            
            logger.info(f"✓ Created and cached agent: {agent_name} (type: {agent.agent_type}, agent: {type(agent.agent).__name__})")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to get agent {agent_name}: {str(e)}")
            return None
    
    def get_available_agents(self) -> List[AgentInfo]:
        """
        Get list of all available agents.
        
        Returns:
            List of available agent information
        """
        try:
            agents = []
            for agent_config in AVAILABLE_AGENTS:
                agent_info = AgentInfo(
                    name=agent_config["name"],
                    description=agent_config["description"],
                    type=agent_config["type"],
                    enabled=True
                )
                agents.append(agent_info)
            
            logger.debug(f"Retrieved {len(agents)} available agents")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to get available agents: {str(e)}")
            return []
    
    async def chat_with_agent(self, agent_name: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a chat conversation with a specific agent using Microsoft Agent Framework.
        
        Args:
            agent_name: The name of the agent to chat with
            message: The user message
            context: Optional context including conversation_id
            
        Returns:
            The agent's response in a structured format
        """
        try:
            agent = await self.get_agent(agent_name)
            if not agent:
                raise ValueError(f"Agent {agent_name} not found or could not be created")
            
            # Execute the agent (now async with Agent Framework)
            response = await agent.run(message, context)
            
            # Format the response
            metadata = {
                "agent_name": agent.name,
                "framework": "Microsoft Agent Framework"
            }
            # Only add agent_id if it exists (Azure AI agents have it, GenericAgent doesn't)
            if hasattr(agent, 'agent_id'):
                metadata["agent_id"] = agent.agent_id
            
            result = {
                "content": response,  # response from Agent Framework
                "agent": agent_name,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            
            logger.info(f"Successfully executed chat with Agent Framework agent {agent_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to chat with agent {agent_name}: {str(e)}")
            raise
    
    async def chat_with_agent_stream(self, agent_name: str, message: str, history: Optional[List] = None):
        """
        Execute a streaming chat conversation with a specific agent.
        
        Args:
            agent_name: The name of the agent to chat with
            message: The user message
            history: Optional conversation history
            
        Yields:
            Agent response updates
        """
        try:
            agent = await self.get_agent(agent_name)
            if not agent:
                raise ValueError(f"Agent {agent_name} not found or could not be created")
            
            # Execute the agent with streaming
            async for update in agent.run_stream(message):
                yield {
                    "content": update.text if hasattr(update, 'text') else str(update),
                    "agent": agent_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_complete": False
                }
            
            # Send completion signal
            yield {
                "content": "",
                "agent": agent_name,
                "timestamp": datetime.utcnow().isoformat(),
                "is_complete": True
            }
            
            logger.info(f"Successfully completed streaming chat with agent {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to stream chat with agent {agent_name}: {str(e)}")
            raise
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """
        Get the status of a specific agent.
        
        Args:
            agent_name: The name of the agent
            
        Returns:
            Agent status information
        """
        try:
            is_cached = agent_name in self._agents
            agent_config = next((config for config in AVAILABLE_AGENTS if config["name"] == agent_name), None)
            
            if not agent_config:
                return {"status": "not_found", "agent": agent_name}
            
            status = {
                "agent": agent_name,
                "status": "available",
                "cached": is_cached,
                "type": agent_config["type"],
                "description": agent_config["description"]
            }
            
            if is_cached:
                agent = self._agents[agent_name]
                status["initialized"] = getattr(agent, '_initialized', False)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get agent status for {agent_name}: {str(e)}")
            return {"status": "error", "agent": agent_name, "error": str(e)}
    
    async def cleanup(self):
        """Clean up agent resources."""
        try:
            # Clean up individual agents
            for agent_name, agent in self._agents.items():
                try:
                    if hasattr(agent, 'cleanup') and hasattr(agent.cleanup, '__call__'):
                        if agent_name in ['people_lookup', 'knowledge_finder']:
                            await agent.cleanup()  # Async cleanup for Azure AI agents
                        else:
                            agent.cleanup()  # Sync cleanup for generic agent
                except Exception as e:
                    logger.error(f"Error cleaning up agent {agent_name}: {str(e)}")
            
            self._agents.clear()
            self._agent_cache.clear()
            logger.info("AgentService cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during AgentService cleanup: {str(e)}")