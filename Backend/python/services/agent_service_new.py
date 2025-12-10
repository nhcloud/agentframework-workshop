"""
Agent Service for managing agent instances and operations.

Matches .NET AgentService.cs pattern with:
- Factory pattern for agent creation
- Agent caching to prevent multiple initializations
- Separate caching for Foundry agents
- Instructions service integration
- Memory management support
"""

import logging
import asyncio
import os
from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime

from services.agent_instructions_service import AgentInstructionsService
from models.chat_models import AgentInfo

logger = logging.getLogger(__name__)


class IAgentService:
    """
    Interface for Agent Service (matches .NET IAgentService).
    """
    
    async def get_available_agents_async(self) -> List[AgentInfo]:
        """Get list of available agents."""
        raise NotImplementedError
    
    async def get_agent_async(self, agent_name: str, enable_memory: bool = False):
        """Get an agent instance by name."""
        raise NotImplementedError
    
    async def chat_with_agent_async(
        self,
        agent_name: str,
        request: Dict[str, Any],
        conversation_history: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Execute a chat with a specific agent."""
        raise NotImplementedError
    
    async def create_azure_foundry_agent_async(self, agent_type: str):
        """Create an Azure AI Foundry agent."""
        raise NotImplementedError


class AgentService(IAgentService):
    """
    Service for managing agent instances and operations.
    
    Matches .NET AgentService structure with:
    - Factory pattern for agent creation (matches _agentFactories)
    - Agent caching to prevent multiple initializations
    - Separate caching for Foundry agents (matches _foundryAgentCache)
    - SemaphoreSlim for thread-safe Foundry agent creation
    - Instructions service for configuration
    """
    
    def __init__(self):
        """Initialize the agent service (matches .NET constructor)."""
        # Instructions service (matches .NET AgentInstructionsService)
        self._instructions_service = AgentInstructionsService()
        
        # Agent factories (matches .NET _agentFactories Dictionary)
        self._agent_factories: Dict[str, Callable[..., Awaitable[Any]]] = {
            "ms_foundry_people_agent": lambda enable_memory=False: self._create_standard_agent_async(
                "MicrosoftFoundryPeopleAgent", enable_memory
            ),
            "azure_openai_agent": lambda enable_memory=False: self._create_standard_agent_async(
                "AzureOpenAIGenericAgent", enable_memory
            ),
            "bedrock_agent": lambda enable_memory=False: self._create_standard_agent_async(
                "BedrockHRAgent", enable_memory
            ),
            "openai_agent": lambda enable_memory=False: self._create_standard_agent_async(
                "OpenAIGenericAgent", enable_memory
            ),
        }
        
        # Foundry agent cache (matches .NET _foundryAgentCache)
        self._foundry_agent_cache: Dict[str, Any] = {}
        
        # Lock for foundry agent cache (matches .NET _foundryAgentCacheLock SemaphoreSlim)
        self._foundry_agent_cache_lock = asyncio.Lock()
        
        # Standard agent cache
        self._agent_cache: Dict[str, Any] = {}
        
        logger.info("AgentService initialized (matching .NET AgentService pattern)")
    
    async def _create_standard_agent_async(
        self,
        agent_type: str,
        enable_memory: bool = False
    ):
        """
        Create a standard agent with instructions service (matches .NET CreateStandardAgentAsync<T>).
        
        Args:
            agent_type: Type of agent to create
            enable_memory: Whether to enable long-running memory
            
        Returns:
            Initialized agent instance
        """
        logger.debug(f"Creating agent with memory setting: {enable_memory}")
        
        # Import agent classes
        from agents.azure_openai_agent import AzureOpenAIAgent, AzureOpenAIGenericAgent
        from agents.ms_foundry_agent import MicrosoftFoundryPeopleAgent
        from agents.bedrock_agent_new import BedrockHRAgent
        from agents.openai_agent import OpenAIGenericAgent
        
        # Create agent based on type
        if agent_type == "AzureOpenAIGenericAgent":
            name = "azure_openai_agent"
            instructions = self._instructions_service.get_agent_instructions(name)
            description = self._instructions_service.get_agent_description(name)
            
            agent = AzureOpenAIAgent(
                name=name,
                description=description,
                instructions=instructions,
                enable_long_running_memory=enable_memory
            )
            
        elif agent_type == "MicrosoftFoundryPeopleAgent":
            name = "ms_foundry_people_agent"
            instructions = self._instructions_service.get_agent_instructions(name)
            description = self._instructions_service.get_agent_description(name)
            
            agent = MicrosoftFoundryPeopleAgent(
                instructions_service=self._instructions_service
            )
            
        elif agent_type == "BedrockHRAgent":
            name = "bedrock_agent"
            instructions = self._instructions_service.get_agent_instructions(name)
            description = self._instructions_service.get_agent_description(name)
            
            agent = BedrockHRAgent(
                name=name,
                description=description,
                instructions=instructions,
                enable_long_running_memory=enable_memory
            )
            
        elif agent_type == "OpenAIGenericAgent":
            name = "openai_agent"
            instructions = self._instructions_service.get_agent_instructions(name)
            description = self._instructions_service.get_agent_description(name)
            
            agent = OpenAIGenericAgent(
                name=name,
                description=description,
                instructions=instructions,
                enable_long_running_memory=enable_memory
            )
            
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Initialize agent
        await agent.initialize_async()
        
        return agent
    
    async def create_azure_foundry_agent_async(self, agent_type: str):
        """
        Create Azure AI Foundry agent with caching (matches .NET CreateAzureFoundryAgentAsync).
        
        Uses double-checked locking pattern like .NET implementation.
        
        Args:
            agent_type: Type of Foundry agent to create
            
        Returns:
            Initialized Foundry agent or None
        """
        # Check configuration
        project_endpoint = os.getenv("MS_FOUNDRY_PROJECT_ENDPOINT")
        agent_id = os.getenv("MS_FOUNDRY_AGENT_ID")
        
        if not project_endpoint:
            logger.warning("Azure AI Foundry not configured, cannot create foundry agent")
            return None
        
        # Check cache first (matches .NET pattern)
        cache_key = f"foundry_{agent_type}"
        if cache_key in self._foundry_agent_cache:
            logger.debug(f"Returning cached Azure AI Foundry agent: {agent_type}")
            return self._foundry_agent_cache[cache_key]
        
        # Acquire lock (matches .NET _foundryAgentCacheLock.WaitAsync())
        async with self._foundry_agent_cache_lock:
            # Double-check after acquiring lock
            if cache_key in self._foundry_agent_cache:
                logger.debug(f"Returning cached Azure AI Foundry agent after lock: {agent_type}")
                return self._foundry_agent_cache[cache_key]
            
            logger.info(f"Creating new Azure AI Foundry agent: {agent_type}")
            
            try:
                from agents.ms_foundry_agent import AzureAIFoundryAgent
                
                # Get agent configuration (matches .NET switch expression)
                if agent_type.lower() == "ms_foundry_people_agent":
                    name = "ms_foundry_people_agent"
                    description = "Azure AI Foundry People Lookup Agent with enterprise directory access"
                    instructions = self._instructions_service.get_agent_instructions(name)
                else:
                    raise ValueError(f"Azure AI Foundry agent type '{agent_type}' not supported")
                
                if not agent_id:
                    raise RuntimeError(f"Agent ID not configured for {agent_type} in Azure AI Foundry")
                
                # Create Foundry agent
                foundry_agent = AzureAIFoundryAgent(
                    name=name,
                    agent_id=agent_id,
                    project_endpoint=project_endpoint,
                    description=description,
                    instructions=instructions,
                    managed_identity_client_id=os.getenv("MANAGED_IDENTITY_CLIENT_ID")
                )
                
                await foundry_agent.initialize_async()
                
                # Cache the agent
                self._foundry_agent_cache[cache_key] = foundry_agent
                
                logger.info(f"Created and cached Azure AI Foundry agent: {name} with ID: {agent_id}")
                return foundry_agent
                
            except Exception as ex:
                logger.error(f"Failed to create Azure AI Foundry agent for type {agent_type}: {str(ex)}")
                return None
    
    async def get_available_agents_async(self) -> List[AgentInfo]:
        """
        Get list of available agents (matches .NET GetAvailableAgentsAsync).
        
        Returns:
            List of AgentInfo objects
        """
        agents = []
        
        # Check Azure AI Foundry configuration (matches .NET hasFoundryConfig check)
        has_foundry_config = (
            os.getenv("MS_FOUNDRY_PROJECT_ENDPOINT") and
            os.getenv("MS_FOUNDRY_AGENT_ID")
        )
        
        logger.info(f"Azure AI Foundry configured: {has_foundry_config}")
        
        # Azure OpenAI Agent (always add if configured)
        if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
            try:
                generic_agent = await self._agent_factories["azure_openai_agent"]()
                agents.append(AgentInfo(
                    name=generic_agent.name,
                    description=generic_agent.description,
                    type="Azure OpenAI",
                    enabled=True,
                    metadata={
                        "model": "Azure OpenAI GPT-4o",
                        "capabilities": ["General conversation", "Problem solving", "Task assistance"]
                    }
                ))
            except Exception as ex:
                logger.error(f"Failed to create generic agent info: {str(ex)}")
        
        # People Lookup agent (with Foundry fallback)
        await self._add_agent_info(
            agents,
            "ms_foundry_people_agent",
            has_foundry_config,
            ["People search", "Contact discovery", "Team coordination"]
        )
        
        # Bedrock agent (AWS)
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            try:
                bedrock_agent = await self._agent_factories["bedrock_agent"]()
                agents.append(AgentInfo(
                    name=bedrock_agent.name,
                    description=bedrock_agent.description,
                    type="AWS Bedrock",
                    enabled=True,
                    metadata={
                        "model": os.getenv("AWS_BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
                        "capabilities": ["hr_policies", "benefits_explanation", "workplace_guidance"]
                    }
                ))
                logger.info(f"Added AWS Bedrock agent: {bedrock_agent.name}")
            except Exception as ex:
                logger.error(f"Failed to create AWS Bedrock agent info: {str(ex)}")
        
        # OpenAI agent (Direct OpenAI, not Azure)
        if os.getenv("OPENAI_API_KEY"):
            try:
                openai_agent = await self._agent_factories["openai_agent"]()
                agents.append(AgentInfo(
                    name=openai_agent.name,
                    description=openai_agent.description,
                    type="OpenAI",
                    enabled=True,
                    metadata={
                        "model": os.getenv("OPENAI_MODEL_ID", "gpt-4.1"),
                        "capabilities": ["software_development", "architecture", "debugging", "technical_explanation"]
                    }
                ))
                logger.info(f"Added OpenAI agent: {openai_agent.name}")
            except Exception as ex:
                logger.error(f"Failed to create OpenAI agent info: {str(ex)}")
        
        logger.info(f"Returning {len(agents)} available agents")
        return agents
    
    async def _add_agent_info(
        self,
        agents: List[AgentInfo],
        agent_type: str,
        has_foundry_config: bool,
        capabilities: List[str]
    ) -> None:
        """
        Add agent info with Foundry fallback (matches .NET AddAgentInfo).
        
        Args:
            agents: List to add agent info to
            agent_type: Type of agent
            has_foundry_config: Whether Foundry is configured
            capabilities: Agent capabilities list
        """
        # Try Azure AI Foundry first if configured
        if has_foundry_config:
            try:
                foundry_agent = await self.create_azure_foundry_agent_async(agent_type)
                if foundry_agent:
                    agents.append(AgentInfo(
                        name=foundry_agent.name,
                        description=foundry_agent.description,
                        type="Azure AI Foundry",
                        enabled=True,
                        metadata={
                            "model": "Azure AI Foundry",
                            "capabilities": capabilities
                        }
                    ))
                    logger.info(f"Added Azure AI Foundry agent: {foundry_agent.name}")
                    return  # Successfully added Foundry agent
            except Exception as ex:
                logger.warning(f"Failed to create Azure AI Foundry agent {agent_type}, falling back to standard: {str(ex)}")
        
        # Add standard agent as fallback
        try:
            if agent_type in self._agent_factories:
                standard_agent = await self._agent_factories[agent_type]()
                agents.append(AgentInfo(
                    name=standard_agent.name,
                    description=standard_agent.description,
                    type="Azure OpenAI",
                    enabled=True,
                    metadata={
                        "model": "Azure OpenAI GPT-4o",
                        "capabilities": capabilities
                    }
                ))
                logger.info(f"Added Azure OpenAI agent: {standard_agent.name}")
        except Exception as ex:
            logger.error(f"Failed to create standard agent {agent_type}: {str(ex)}")
    
    async def get_agent_async(self, agent_name: str, enable_memory: bool = False):
        """
        Get an agent instance by name (matches .NET GetAgentAsync).
        
        Args:
            agent_name: Name of the agent
            enable_memory: Whether to enable long-running memory
            
        Returns:
            Agent instance or None
        """
        normalized_name = agent_name.lower()
        
        logger.info(f"Retrieving agent: {agent_name} with memory: {enable_memory}")
        
        # Determine agent type (matches .NET DetermineAgentType)
        agent_type = self._determine_agent_type(normalized_name)
        
        logger.debug(f"Determined agent type: {agent_type} for agent name: {agent_name}")
        
        # Handle different agent types (matches .NET switch statement)
        if agent_type == "ms_foundry_agent":
            return await self._get_microsoft_foundry_agent(normalized_name)
        elif agent_type == "azure_openai_agent":
            return await self._create_standard_agent_async("AzureOpenAIGenericAgent", enable_memory)
        elif agent_type == "bedrock_agent":
            return await self._create_standard_agent_async("BedrockHRAgent", enable_memory)
        elif agent_type == "openai_agent":
            return await self._create_standard_agent_async("OpenAIGenericAgent", enable_memory)
        else:
            logger.warning(f"Unknown agent type '{agent_type}' for agent '{agent_name}'")
            return None
    
    def _determine_agent_type(self, normalized_agent_name: str) -> str:
        """
        Determine agent type from name (matches .NET DetermineAgentType).
        
        Args:
            normalized_agent_name: Lowercase agent name
            
        Returns:
            Agent type string
        """
        # Map agent names to types (matches .NET switch expression)
        if normalized_agent_name.startswith("foundry_") or normalized_agent_name == "ms_foundry_people_agent":
            return "ms_foundry_agent"
        
        type_mapping = {
            "azure_openai_agent": "azure_openai_agent",
            "generic_agent": "azure_openai_agent",
            "generic": "azure_openai_agent",
            "bedrock_agent": "bedrock_agent",
            "openai_agent": "openai_agent",
        }
        
        return type_mapping.get(normalized_agent_name, normalized_agent_name)
    
    async def _get_microsoft_foundry_agent(self, normalized_name: str):
        """
        Get Microsoft Foundry agent (matches .NET GetMicrosoftFoundryAgent).
        
        Args:
            normalized_name: Normalized agent name
            
        Returns:
            Agent instance or standard fallback
        """
        # Check Foundry configuration
        has_foundry_config = (
            os.getenv("MS_FOUNDRY_PROJECT_ENDPOINT") and
            os.getenv("MS_FOUNDRY_AGENT_ID")
        )
        
        if not has_foundry_config:
            logger.warning("Azure AI Foundry not configured for Microsoft Foundry agent")
            return await self._create_standard_agent_async("MicrosoftFoundryPeopleAgent")
        
        try:
            foundry_agent = await self.create_azure_foundry_agent_async("ms_foundry_people_agent")
            if foundry_agent:
                logger.info(f"Using Azure AI Foundry agent for {normalized_name}")
                return foundry_agent
        except Exception as ex:
            logger.warning(f"Failed to create Azure AI Foundry agent, using standard version: {str(ex)}")
        
        # Fallback to standard agent
        return await self._create_standard_agent_async("MicrosoftFoundryPeopleAgent")
    
    async def chat_with_agent_async(
        self,
        agent_name: str,
        request: Dict[str, Any],
        conversation_history: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat with an agent (matches .NET ChatWithAgentAsync).
        
        Args:
            agent_name: Name of the agent
            request: Chat request dictionary
            conversation_history: Optional conversation history
            
        Returns:
            Response dictionary
        """
        # Determine memory setting (matches .NET logic)
        enable_memory = request.get("enable_memory", False)
        env_memory = os.getenv("ENABLE_LONG_RUNNING_MEMORY", "false").lower() == "true"
        enable_memory = enable_memory or env_memory
        
        logger.debug(
            f"Chat with {agent_name}: memory={enable_memory} "
            f"(from request: {request.get('enable_memory')}, env: {env_memory})"
        )
        
        agent = await self.get_agent_async(agent_name, enable_memory)
        if agent is None:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        try:
            logger.info(f"Starting chat with agent {agent_name} for message: {request.get('message', '')[:50]}...")
            
            # Build ChatRequest
            from agents.base_agent_new import ChatRequest, GroupChatMessage
            
            chat_request = ChatRequest(
                message=request.get("message", ""),
                session_id=request.get("session_id"),
                context=request.get("context"),
                enable_memory=enable_memory
            )
            
            # Convert conversation history if provided
            history = None
            if conversation_history:
                history = []
                for i, msg in enumerate(conversation_history):
                    # Handle both dict-based and GroupChatMessage instances
                    if hasattr(msg, "content"):
                        history.append(
                            GroupChatMessage(
                                message_id=getattr(msg, "message_id", str(i)),
                                agent=getattr(msg, "agent", "user"),
                                content=getattr(msg, "content", ""),
                                timestamp=getattr(msg, "timestamp", datetime.utcnow())
                            )
                        )
                    else:
                        history.append(
                            GroupChatMessage(
                                message_id=msg.get("message_id", str(i)),
                                agent=msg.get("agent", "user"),
                                content=msg.get("content", ""),
                                timestamp=msg.get("timestamp", datetime.utcnow())
                            )
                        )
            
            # Call agent
            response = await agent.chat_with_history_async(chat_request, history)
            
            logger.info(f"Chat completed with agent {agent_name}, response length: {len(response.content or '')}")
            
            return {
                "content": response.content,
                "agent": response.agent,
                "session_id": response.session_id,
                "timestamp": response.timestamp.isoformat(),
                "processing_time_ms": response.processing_time_ms,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                } if response.usage else None
            }
            
        except Exception as ex:
            logger.error(f"Error during chat with agent {agent_name}: {str(ex)}")
            raise
