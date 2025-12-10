"""
Agent service for managing agent instances and operations.

This service handles agent creation, management, and execution,
similar to the .NET AgentService with caching and factory patterns.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime

from agents import create_agent, AVAILABLE_AGENTS
from models.chat_models import AgentInfo


logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing agent instances and operations.
    
    Matches .NET AgentService structure with:
    - Agent caching to prevent multiple initializations
    - Lazy initialization with async support
    - Factory pattern for agent creation
    - Azure AI Foundry agent support
    - Memory management
    """
    
    def __init__(self):
        """Initialize the agent service with caching."""
        # Main agent cache (similar to .NET _agents)
        self._agents: Dict[str, Any] = {}
        
        # Azure AI Foundry agent cache (similar to .NET _foundryAgentCache)
        self._foundry_agent_cache: Dict[str, Any] = {}
        
        # Lock for foundry agent cache (similar to .NET _foundryAgentCacheLock)
        self._foundry_agent_cache_lock = asyncio.Lock()
        
        # Agent factories (similar to .NET _agentFactories)
        self._agent_factories: Dict[str, Callable[[], Awaitable[Any]]] = {
            "generic_agent": self._create_standard_agent_async,
            "ms_foundry_people_agent": self._create_foundry_agent_async,
            "people_lookup": self._create_foundry_agent_async,
            "knowledge_finder": self._create_foundry_agent_async,
            "bedrock_agent": self._create_standard_agent_async,
            "gemini_agent": self._create_standard_agent_async,
            "openai_agent": self._create_standard_agent_async,
        }
        
        logger.info("AgentService initialized using Microsoft Agent Framework")
    
    async def _create_standard_agent_async(self, agent_name: str, enable_memory: bool = False) -> Any:
        """
        Create a standard agent (non-Foundry) with optional memory support.
        
        Args:
            agent_name: The name of the agent to create
            enable_memory: Whether to enable long-running memory
            
        Returns:
            The initialized agent instance
        """
        logger.debug(f"Creating agent with memory setting: {enable_memory}")
        
        # Create agent instance
        agent = create_agent(agent_name)
        
        # Initialize the agent (async for Azure AI agents, sync for others)
        if hasattr(agent, 'initialize') and callable(agent.initialize):
            if agent_name in ['people_lookup', 'knowledge_finder']:
                await agent.initialize()  # Async initialize for Azure AI agents
            else:
                agent.initialize()  # Sync initialize for generic, bedrock, and gemini agents
        
        # Validate required attributes
        if not hasattr(agent, 'agent_type'):
            logger.error(f"Agent {agent_name} missing required agent_type attribute")
            raise AttributeError(f"Agent {agent_name} is missing agent_type attribute")
        
        if not hasattr(agent, 'agent'):
            logger.error(f"Agent {agent_name} missing required agent attribute")
            raise AttributeError(f"Agent {agent_name} is missing agent attribute")
        
        if agent.agent is None:
            logger.error(f"Agent {agent_name} has agent attribute but it is None")
            raise ValueError(f"Agent {agent_name} agent attribute is None - initialization may have failed")
        
        logger.info(f"✓ Created agent: {agent_name} (type: {agent.agent_type})")
        return agent
    
    async def _create_foundry_agent_async(self, agent_name: str) -> Any:
        """
        Create Azure AI Foundry agent with caching (similar to .NET CreateAzureFoundryAgentAsync).
        
        Args:
            agent_name: The agent name (ms_foundry_people_agent, people_lookup, knowledge_finder)
            
        Returns:
            The initialized Azure AI Foundry agent or None if not configured
        """
        # Normalize agent name
        if agent_name == "ms_foundry_people_agent":
            agent_name = "people_lookup"
        
        # Check cache first to prevent multiple initializations
        cache_key = f"foundry_{agent_name}"
        
        if cache_key in self._foundry_agent_cache:
            logger.debug(f"Returning cached Azure AI Foundry agent: {agent_name}")
            return self._foundry_agent_cache[cache_key]
        
        async with self._foundry_agent_cache_lock:
            # Double-check after acquiring lock
            if cache_key in self._foundry_agent_cache:
                logger.debug(f"Returning cached Azure AI Foundry agent after lock: {agent_name}")
                return self._foundry_agent_cache[cache_key]
            
            logger.info(f"Creating new Azure AI Foundry agent: {agent_name}")
            
            try:
                # Create agent instance
                agent = create_agent(agent_name)
                
                # Initialize the agent
                await agent.initialize()
                
                # Validate required attributes
                if not hasattr(agent, 'agent_type'):
                    raise AttributeError(f"Agent {agent_name} is missing agent_type attribute")
                
                if not hasattr(agent, 'agent'):
                    raise AttributeError(f"Agent {agent_name} is missing agent attribute")
                
                if agent.agent is None:
                    raise ValueError(f"Agent {agent_name} agent attribute is None")
                
                # Cache the agent to prevent future reinitializations
                self._foundry_agent_cache[cache_key] = agent
                
                logger.info(f"Created and cached Azure AI Foundry agent: {agent.name}")
                return agent
                
            except Exception as ex:
                logger.error(f"Failed to create Azure AI Foundry agent for type {agent_name}: {str(ex)}")
                return None
    
    async def get_available_agents_async(self) -> List[AgentInfo]:
        """
        Get list of all available agents (async version to match .NET).
        
        Returns:
            List of available agent information
        """
        try:
            agents = []
            
            # Always add the generic agent (similar to .NET)
            try:
                generic_agent = await self._create_standard_agent_async("generic_agent")
                agents.append(AgentInfo(
                    name=generic_agent.name,
                    id=generic_agent.name,  # Match .NET: Id = Name
                    description="A versatile general-purpose assistant using Microsoft Agent Framework with Azure OpenAI",
                    agent_type="Azure OpenAI",
                    enabled=True,
                    capabilities=["General conversation", "Problem solving", "Task assistance", "Information provision"]
                ))
            except Exception as ex:
                logger.error(f"Failed to create generic agent info: {str(ex)}")
            
            # Add People Lookup agent (try Foundry first, fallback to standard)
            await self._add_agent_info(agents, "people_lookup", 
                                     ["People search", "Contact discovery", "Team coordination", "Role identification"])
            
            # Add Knowledge Finder agent
            await self._add_agent_info(agents, "knowledge_finder",
                                     ["Document search", "Knowledge base queries", "Policy lookup", "Information synthesis"])
            
            # Add Bedrock agent (AWS)
            try:
                bedrock_agent = await self._create_standard_agent_async("bedrock_agent")
                agents.append(AgentInfo(
                    name=bedrock_agent.name,
                    id=bedrock_agent.name,
                    description="AWS Bedrock agent with Amazon's foundation models using Microsoft Agent Framework",
                    agent_type="AWS Bedrock",
                    enabled=True,
                    capabilities=["hr_policies", "benefits_explanation", "workplace_guidance"]
                ))
                logger.info(f"Added AWS Bedrock agent: {bedrock_agent.name}")
            except Exception as ex:
                logger.error(f"Failed to create AWS Bedrock agent info: {str(ex)}")
            
            # Add Gemini agent (Google)
            try:
                gemini_agent = await self._create_standard_agent_async("gemini_agent")
                agents.append(AgentInfo(
                    name=gemini_agent.name,
                    id=gemini_agent.name,
                    description="Google Gemini agent with Google's AI models using Microsoft Agent Framework",
                    agent_type="Google Gemini",
                    enabled=True,
                    capabilities=["general_conversation", "coding_help", "analysis"]
                ))
                logger.info(f"Added Google Gemini agent: {gemini_agent.name}")
            except Exception as ex:
                logger.error(f"Failed to create Google Gemini agent info: {str(ex)}")
            
            logger.info(f"Returning {len(agents)} available agents")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to get available agents: {str(e)}")
            return []
    
    async def _add_agent_info(self, agents: List[AgentInfo], agent_type: str, capabilities: List[str]):
        """
        Add agent info with Foundry fallback (similar to .NET AddAgentInfo).
        
        Args:
            agents: List to append agent info to
            agent_type: Type of agent to add
            capabilities: List of agent capabilities
        """
        # Try Azure AI Foundry first if agent supports it
        if agent_type in ['people_lookup', 'knowledge_finder']:
            try:
                foundry_agent = await self._create_foundry_agent_async(agent_type)
                if foundry_agent is not None:
                    agents.append(AgentInfo(
                        name=foundry_agent.name,
                        id=foundry_agent.name,
                        description=f"Specialized Azure AI Foundry agent using Microsoft Agent Framework",
                        agent_type="Azure AI Foundry",
                        enabled=True,
                        capabilities=capabilities
                    ))
                    logger.info(f"Added Azure AI Foundry agent: {foundry_agent.name}")
                    return  # Successfully added Foundry agent, don't add standard version
            except Exception as ex:
                logger.warning(f"Failed to create Azure AI Foundry agent {agent_type}, falling back to standard: {str(ex)}")
        
        # Add standard Azure OpenAI agent as fallback
        try:
            standard_agent = await self._create_standard_agent_async(agent_type)
            agents.append(AgentInfo(
                name=standard_agent.name,
                id=standard_agent.name,
                description=f"Specialized agent using Microsoft Agent Framework",
                agent_type="Azure OpenAI",
                enabled=True,
                capabilities=capabilities
            ))
            logger.info(f"Added Azure OpenAI agent: {standard_agent.name}")
        except Exception as ex:
            logger.error(f"Failed to create standard agent {agent_type}: {str(ex)}")
    
    def get_available_agents(self) -> List[AgentInfo]:
        """
        Get list of all available agents (sync wrapper for compatibility).
        
        Returns:
            List of available agent information
        """
        # For backward compatibility, create a simple sync version
        try:
            agents = []
            for agent_config in AVAILABLE_AGENTS:
                agent_info = AgentInfo(
                    name=agent_config["name"],
                    id=agent_config["name"],
                    description=agent_config["description"],
                    agent_type=agent_config["type"],
                    enabled=True
                )
                agents.append(agent_info)
            
            logger.debug(f"Retrieved {len(agents)} available agents")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to get available agents: {str(e)}")
            return []
    
    async def get_agent_async(self, agent_name: str, enable_memory: bool = False):
        """
        Get an agent instance by name with memory support (matches .NET GetAgentAsync).
        
        Args:
            agent_name: The name of the agent to retrieve
            enable_memory: Whether to enable long-running memory
            
        Returns:
            The agent instance or None if not found
        """
        normalized_name = agent_name.lower()
        
        logger.info(f"Retrieving agent: {agent_name} with memory: {enable_memory}")
        
        # Determine agent type from name
        agent_type = self._determine_agent_type(normalized_name)
        
        logger.debug(f"Determined agent type: {agent_type} for agent name: {agent_name}")
        
        # Check cache first (but respect memory setting changes)
        cache_key = f"{agent_name}_{enable_memory}"
        if cache_key in self._agents:
            cached_agent = self._agents[cache_key]
            if hasattr(cached_agent, 'agent_type') and hasattr(cached_agent, 'agent') and cached_agent.agent is not None:
                logger.debug(f"Returning cached agent: {agent_name}")
                return cached_agent
            else:
                logger.warning(f"Removing invalid cached agent {agent_name}")
                del self._agents[cache_key]
        
        # Handle different agent types
        if agent_type == "ms_foundry_agent":
            agent = await self._get_microsoft_foundry_agent(normalized_name)
        elif agent_type in ["azure_openai_agent", "bedrock_agent", "gemini_agent", "openai_agent"]:
            agent = await self._create_standard_agent_async(agent_name, enable_memory)
        else:
            logger.warning(f"Unknown agent type '{agent_type}' for agent '{agent_name}'")
            return None
        
        # Cache the agent
        if agent is not None:
            self._agents[cache_key] = agent
            logger.info(f"✓ Created and cached agent: {agent_name} (type: {agent.agent_type})")
        
        return agent
    
    async def get_agent(self, agent_name: str):
        """
        Get an agent instance by name (backward compatible version).
        
        Args:
            agent_name: The name of the agent to retrieve
            
        Returns:
            The agent instance or None if not found
        """
        return await self.get_agent_async(agent_name, enable_memory=False)
    
    def _determine_agent_type(self, normalized_agent_name: str) -> str:
        """
        Map agent names to their types (similar to .NET DetermineAgentType).
        
        Args:
            normalized_agent_name: Lowercase agent name
            
        Returns:
            Agent type string
        """
        # Map agent names to their types
        if normalized_agent_name.startswith("foundry_") or normalized_agent_name == "ms_foundry_people_agent":
            return "ms_foundry_agent"
        
        mapping = {
            "azure_openai_agent": "azure_openai_agent",
            "generic_agent": "azure_openai_agent",
            "generic": "azure_openai_agent",
            "bedrock_agent": "bedrock_agent",
            "openai_agent": "openai_agent",
            "gemini_agent": "gemini_agent",
            "people_lookup": "ms_foundry_agent",
            "knowledge_finder": "ms_foundry_agent",
        }
        
        return mapping.get(normalized_agent_name, normalized_agent_name)
    
    async def _get_microsoft_foundry_agent(self, normalized_name: str):
        """
        Get Microsoft Foundry agent with fallback (similar to .NET GetMicrosoftFoundryAgent).
        
        Args:
            normalized_name: Normalized agent name
            
        Returns:
            Agent instance or None
        """
        # Try to create Azure AI Foundry agent
        try:
            foundry_agent = await self._create_foundry_agent_async(normalized_name)
            if foundry_agent is not None:
                logger.info(f"Using Azure AI Foundry agent for {normalized_name}")
                return foundry_agent
        except Exception as ex:
            logger.warning(f"Failed to create Azure AI Foundry agent, using standard version: {str(ex)}")
        
        # Fallback to standard agent
        return await self._create_standard_agent_async(normalized_name)
    
    async def chat_with_agent_async(self, agent_name: str, message: str, 
                                   conversation_history: Optional[List] = None,
                                   enable_memory: bool = False) -> Dict[str, Any]:
        """
        Execute a chat conversation with a specific agent (matches .NET ChatWithAgentAsync).
        
        Args:
            agent_name: The name of the agent to chat with
            message: The user message
            conversation_history: Optional conversation history
            enable_memory: Whether to enable memory
            
        Returns:
            The agent's response in a structured format
        """
        logger.debug(f"Chat with {agent_name}: memory={enable_memory}")
        
        agent = await self.get_agent_async(agent_name, enable_memory)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found or could not be created")
        
        try:
            logger.info(f"Starting chat with agent {agent_name} for message: {message}")
            
            # Prepare context
            context = {"conversation_history": conversation_history} if conversation_history else None
            
            # Execute the agent (now async with Agent Framework)
            response = await agent.run(message, context)
            
            # Format the response
            metadata = {
                "agent_name": agent.name,
                "framework": "Microsoft Agent Framework",
                "memory_enabled": enable_memory
            }
            
            # Only add agent_id if it exists (Azure AI agents have it, GenericAgent doesn't)
            if hasattr(agent, 'agent_id'):
                metadata["agent_id"] = agent.agent_id
            
            result = {
                "content": response,
                "agent": agent_name,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            
            logger.info(f"Chat completed with agent {agent_name}, response length: {len(response) if response else 0}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to chat with agent {agent_name}: {str(e)}")
            raise
    
    async def chat_with_agent(self, agent_name: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a chat conversation with a specific agent (backward compatible).
        
        Args:
            agent_name: The name of the agent to chat with
            message: The user message
            context: Optional context including conversation_id
            
        Returns:
            The agent's response in a structured format
        """
        conversation_history = context.get("conversation_history") if context else None
        enable_memory = context.get("enable_memory", False) if context else False
        
        return await self.chat_with_agent_async(agent_name, message, conversation_history, enable_memory)
    
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
            # Check if agent is cached
            is_cached = any(agent_name in key for key in self._agents.keys())
            is_foundry_cached = any(agent_name in key for key in self._foundry_agent_cache.keys())
            
            agent_config = next((config for config in AVAILABLE_AGENTS if config["name"] == agent_name), None)
            
            if not agent_config:
                return {"status": "not_found", "agent": agent_name}
            
            status = {
                "agent": agent_name,
                "status": "available",
                "cached": is_cached or is_foundry_cached,
                "type": agent_config["type"],
                "description": agent_config["description"],
                "framework": "Microsoft Agent Framework"
            }
            
            # Get initialization status if cached
            if is_cached:
                # Find cached agent instance
                for key, agent in self._agents.items():
                    if agent_name in key:
                        status["initialized"] = getattr(agent, '_initialized', False)
                        break
            
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
                    if hasattr(agent, 'cleanup') and callable(agent.cleanup):
                        base_name = agent_name.split('_')[0] if '_' in agent_name else agent_name
                        if base_name in ['people_lookup', 'knowledge_finder']:
                            await agent.cleanup()  # Async cleanup for Azure AI agents
                        else:
                            agent.cleanup()  # Sync cleanup for generic agent
                except Exception as e:
                    logger.error(f"Error cleaning up agent {agent_name}: {str(e)}")
            
            # Clean up foundry agents
            for agent_name, agent in self._foundry_agent_cache.items():
                try:
                    if hasattr(agent, 'cleanup') and callable(agent.cleanup):
                        await agent.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up foundry agent {agent_name}: {str(e)}")
            
            self._agents.clear()
            self._foundry_agent_cache.clear()
            logger.info("AgentService cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during AgentService cleanup: {str(e)}")