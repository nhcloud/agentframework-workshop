"""
OpenAI Agent implementation (Direct OpenAI, not Azure).

Matches .NET OpenAIGenericAgent pattern using direct OpenAI API.
Uses the same patterns as the .NET implementation.
"""

import os
import logging
from typing import Optional, List, Dict, Any

from .base_agent_new import BaseAgent, GroupChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class OpenAIGenericAgent(BaseAgent):
    """
    Direct OpenAI Agent (matches .NET OpenAIGenericAgent).
    
    Uses direct OpenAI API (not Azure) for chat completions.
    Specializes in software development, architecture, and technical help.
    """
    
    def __init__(
        self,
        name: str = "openai_agent",
        description: str = "Direct OpenAI assistant for development and technical help",
        instructions: str = "You are a helpful assistant running on OpenAI's GPT-4.1 model.",
        model_id: Optional[str] = None,
        enable_long_running_memory: bool = False
    ):
        """
        Initialize the OpenAI agent (matches .NET constructor pattern).
        
        Args:
            name: Agent name
            description: Agent description
            instructions: System instructions
            model_id: OpenAI model ID
            enable_long_running_memory: Whether to enable long-running memory
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory
        )
        
        self._model_id = model_id or os.getenv("OPENAI_MODEL_ID", "gpt-4.1")
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        
        logger.info(f"OpenAIGenericAgent '{name}' created with model: {self._model_id}")
    
    async def _do_initialize_async(self) -> None:
        """Initialize the OpenAI client."""
        try:
            from openai import AsyncOpenAI
            
            if not self._api_key:
                raise ValueError("OPENAI_API_KEY is required")
            
            # Create direct OpenAI client (not Azure)
            self._chat_client = AsyncOpenAI(api_key=self._api_key)
            
            logger.info(f"OpenAI client initialized for model: {self._model_id}")
            
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            raise
        except Exception as ex:
            logger.error(f"Failed to initialize OpenAI client: {str(ex)}")
            raise
    
    async def respond_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response using OpenAI (matches .NET RespondAsync pattern).
        
        Args:
            message: User message
            conversation_history: Optional conversation history
            context: Optional additional context
            
        Returns:
            Agent's response string
        """
        # Ensure client is initialized
        if self._chat_client is None:
            await self.initialize_async()
        
        if self._chat_client is None:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
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
            
            # Call OpenAI API
            response = await self._chat_client.chat.completions.create(
                model=self._model_id,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            
            result = response.choices[0].message.content or "I apologize, but I couldn't generate a response."
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Agent {self._name} responded in {duration:.0f}ms")
            
            return result
            
        except Exception as ex:
            logger.error(f"OpenAI chat error: {str(ex)}")
            return f"I encountered an error while processing your request: {str(ex)}"
    
    @classmethod
    def create_with_instructions_service(
        cls,
        instructions_service,
        enable_long_running_memory: bool = False
    ) -> "OpenAIGenericAgent":
        """
        Factory method to create agent with instructions service.
        
        Args:
            instructions_service: AgentInstructionsService instance
            enable_long_running_memory: Whether to enable memory
            
        Returns:
            Configured OpenAIGenericAgent instance
        """
        name = "openai_agent"
        instructions = instructions_service.get_agent_instructions(name)
        description = instructions_service.get_agent_description(name)
        
        return cls(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory
        )

