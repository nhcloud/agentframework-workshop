"""
Azure OpenAI Agent implementation.

Matches .NET AzureOpenAIAgent pattern using Azure OpenAI with optional memory support.
Uses the same patterns as the .NET implementation including:
- ChatClient integration
- UserInfoMemory for long-running memory
- Conversation history management
"""

import os
import logging
from typing import Optional, List, Dict, Any

from .base_agent_new import BaseAgent, GroupChatMessage, ChatRequest, ChatResponse
from .user_info_memory import UserInfoMemory

logger = logging.getLogger(__name__)


class AzureOpenAIAgent(BaseAgent):
    """
    Azure OpenAI Agent (matches .NET AzureOpenAIAgent).
    
    Uses Azure OpenAI for chat completions with optional memory support
    via UserInfoMemory for long-running conversations.
    """
    
    def __init__(
        self,
        name: str = "azure_openai_agent",
        description: str = "General-purpose AI assistant powered by Azure OpenAI",
        instructions: str = "You are a helpful AI assistant.",
        model_deployment: Optional[str] = None,
        endpoint: Optional[str] = None,
        enable_long_running_memory: bool = False
    ):
        """
        Initialize the Azure OpenAI agent (matches .NET constructor pattern).
        
        Args:
            name: Agent name
            description: Agent description
            instructions: System instructions
            model_deployment: Azure OpenAI deployment name
            endpoint: Azure OpenAI endpoint URL
            enable_long_running_memory: Whether to enable long-running memory
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory
        )
        
        self._model_deployment = model_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self._endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self._api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self._api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        
        # Memory support (matches .NET UserInfoMemory pattern)
        self._memory: Optional[UserInfoMemory] = None
        
        logger.info(f"AzureOpenAIAgent '{name}' created with deployment: {self._model_deployment}")
    
    async def _do_initialize_async(self) -> None:
        """
        Initialize the Azure OpenAI client (matches .NET InitializeAsync).
        """
        try:
            from openai import AsyncAzureOpenAI
            
            if not self._endpoint or not self._api_key:
                raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are required")
            
            # Create Azure OpenAI client
            self._chat_client = AsyncAzureOpenAI(
                azure_endpoint=self._endpoint,
                api_key=self._api_key,
                api_version=self._api_version
            )
            
            # If long-running memory is enabled, create UserInfoMemory
            if self._enable_long_running_memory:
                logger.info(f"Initializing Azure OpenAI agent {self._name} with long-running memory enabled")
                self._memory = UserInfoMemory()
            
            logger.info(
                f"Initialized Azure OpenAI agent {self._name} with model {self._model_deployment} "
                f"(Memory: {self._enable_long_running_memory})"
            )
            
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            raise
        except Exception as ex:
            logger.error(f"Failed to initialize Azure OpenAI agent {self._name}: {str(ex)}")
            raise
    
    async def respond_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response (matches .NET RespondAsync with memory support).
        
        Args:
            message: User message
            conversation_history: Optional conversation history
            context: Optional additional context
            
        Returns:
            Agent's response string
        """
        # Ensure agent is initialized
        if self._chat_client is None:
            await self.initialize_async()
        
        try:
            # If using memory support
            if self._enable_long_running_memory and self._memory is not None:
                return await self._respond_with_memory_async(message, conversation_history, context)
            
            # Standard response without memory
            return await self._respond_standard_async(message, conversation_history, context)
            
        except Exception as ex:
            logger.error(f"Error in {self._name} responding to message: {str(ex)}")
            return f"I encountered an error while processing your request: {str(ex)}"
    
    async def _respond_standard_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """Standard response without memory."""
        from datetime import datetime
        
        start_time = datetime.utcnow()
        
        # Build system prompt with context
        system_prompt = self._instructions
        if context:
            system_prompt += f"\n\nAdditional Context: {context}"
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for history_msg in sorted(conversation_history, key=lambda m: m.timestamp):
                role = "user" if history_msg.agent == "user" else "assistant"
                messages.append({"role": role, "content": history_msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Call Azure OpenAI
        response = await self._chat_client.chat.completions.create(
            model=self._model_deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        result = response.choices[0].message.content or "I apologize, but I couldn't generate a response."
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Agent {self._name} responded in {duration:.0f}ms")
        
        return result
    
    async def _respond_with_memory_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Response with long-running memory support (matches .NET RespondWithMemoryAsync).
        
        Args:
            message: User message
            conversation_history: Optional conversation history
            context: Optional additional context
            
        Returns:
            Agent's response string
        """
        from datetime import datetime
        
        logger.debug(f"Processing message with long-running memory for agent {self._name}")
        
        start_time = datetime.utcnow()
        
        # Get memory state key
        memory_state_key = self._get_memory_state_key(conversation_history)
        
        # Build system prompt with memory context
        system_prompt = self._instructions
        
        # Add memory context if available
        if self._memory:
            memory_context = self._memory.to_context_string(memory_state_key)
            if memory_context:
                system_prompt += f"\n\n{memory_context}"
        
        if context:
            system_prompt += f"\n\nAdditional Context: {context}"
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for history_msg in sorted(conversation_history, key=lambda m: m.timestamp):
                role = "user" if history_msg.agent == "user" else "assistant"
                messages.append({"role": role, "content": history_msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Call Azure OpenAI
        response = await self._chat_client.chat.completions.create(
            model=self._model_deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        result = response.choices[0].message.content or "I apologize, but I couldn't generate a response."
        
        # Extract and store any user information from the response
        if self._memory:
            await self._extract_and_store_user_info(memory_state_key, message, result)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000
        
        logger.debug(f"Response generated with memory context: {len(result)} characters in {duration:.0f}ms")
        
        return result
    
    async def _extract_and_store_user_info(
        self,
        state_key: str,
        user_message: str,
        assistant_response: str
    ) -> None:
        """
        Extract and store user information from conversation.
        
        Simple implementation - can be enhanced with NLP extraction.
        """
        if not self._memory:
            return
        
        # Simple heuristic: store if user mentions their name
        lower_message = user_message.lower()
        if "my name is" in lower_message or "i am" in lower_message:
            # Extract potential name (simplified)
            self._memory.store(state_key, "mentioned_identity", user_message)
        
        # Store conversation topic
        self._memory.store(state_key, "last_topic", user_message[:100])
    
    async def _get_chat_response(self, messages: List[Dict[str, str]]) -> str:
        """Get response from Azure OpenAI."""
        if self._chat_client is None:
            return "Agent not properly initialized."
        
        response = await self._chat_client.chat.completions.create(
            model=self._model_deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        return response.choices[0].message.content or "I apologize, but I couldn't generate a response."


class AzureOpenAIGenericAgent(AzureOpenAIAgent):
    """
    Generic Azure OpenAI Agent (matches .NET AzureOpenAIGenericAgent naming).
    
    Alias for AzureOpenAIAgent for backward compatibility.
    """
    
    def __init__(
        self,
        instructions_service=None,
        enable_long_running_memory: bool = False,
        **kwargs
    ):
        """Initialize with optional instructions service."""
        name = "azure_openai_agent"
        description = "General-purpose conversational agent powered by Azure OpenAI"
        instructions = "You are a helpful, knowledgeable, and versatile assistant powered by Azure OpenAI."
        
        # Get instructions from service if provided
        if instructions_service:
            instructions = instructions_service.get_agent_instructions(name)
            description = instructions_service.get_agent_description(name)
        
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory,
            **kwargs
        )
