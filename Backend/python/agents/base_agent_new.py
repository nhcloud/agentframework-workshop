"""
Base Agent classes for Microsoft Agent Framework.

Matches .NET BaseAgent.cs pattern with IAgent interface and BaseAgent abstract class.
Uses the same patterns as the .NET implementation including:
- ChatClient integration
- ActivitySource for observability
- Memory state management
- Token estimation
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GroupChatMessage:
    """Message in a group chat conversation (matches .NET GroupChatMessage)."""
    message_id: str
    agent: str
    content: str
    timestamp: datetime
    
    @classmethod
    def create(cls, agent: str, content: str) -> "GroupChatMessage":
        return cls(
            message_id=str(uuid.uuid4()),
            agent=agent,
            content=content,
            timestamp=datetime.utcnow()
        )


@dataclass
class ChatRequest:
    """Chat request model (matches .NET ChatRequest)."""
    message: str
    session_id: Optional[str] = None
    context: Optional[str] = None
    enable_memory: Optional[bool] = False
    agent_ids: Optional[List[str]] = None


@dataclass
class UsageInfo:
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResponse:
    """Chat response model (matches .NET ChatResponse)."""
    content: str
    agent: str
    session_id: str
    timestamp: datetime
    usage: Optional[UsageInfo] = None
    processing_time_ms: int = 0


class IAgent(ABC):
    """
    Interface for all agents (matches .NET IAgent interface).
    
    All agents must implement this interface to ensure consistent behavior
    across different LLM providers.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the agent's name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the agent's description."""
        pass
    
    @property
    @abstractmethod
    def instructions(self) -> str:
        """Get the agent's system instructions."""
        pass
    
    @property
    @abstractmethod
    def enable_long_running_memory(self) -> bool:
        """Check if long-running memory is enabled."""
        pass
    
    @abstractmethod
    async def initialize_async(self) -> None:
        """Initialize the agent (async)."""
        pass
    
    @abstractmethod
    async def respond_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response to a message.
        
        Args:
            message: User's input message
            conversation_history: Optional conversation history
            context: Optional additional context
            
        Returns:
            Agent's response string
        """
        pass
    
    @abstractmethod
    async def chat_async(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat request.
        
        Args:
            request: Chat request with message and options
            
        Returns:
            ChatResponse with content and metadata
        """
        pass
    
    @abstractmethod
    async def chat_with_history_async(
        self,
        request: ChatRequest,
        conversation_history: Optional[List[GroupChatMessage]] = None
    ) -> ChatResponse:
        """
        Process a chat with message history.
        
        Args:
            request: Chat request
            conversation_history: Optional conversation history
            
        Returns:
            ChatResponse with content and metadata
        """
        pass


class BaseAgent(IAgent):
    """
    Abstract base class for all agents (matches .NET BaseAgent).
    
    Provides common functionality for:
    - Chat client management
    - Thread/session management
    - Message history tracking
    - Token estimation
    - Observability (logging, tracing)
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        instructions: str,
        enable_long_running_memory: bool = False
    ):
        """
        Initialize the base agent (matches .NET BaseAgent constructor).
        
        Args:
            name: Agent name
            description: Agent description
            instructions: System instructions for the agent
            enable_long_running_memory: Whether to persist memory across sessions
        """
        self._name = name
        self._description = description
        self._instructions = instructions
        self._enable_long_running_memory = enable_long_running_memory
        
        # Chat client (matches .NET _chatClient)
        self._chat_client = None
        
        # AI Agent for memory support (matches .NET _aiAgent)
        self._ai_agent = None
        
        # User memory state (matches .NET _userMemoryState)
        self._user_memory_state: Dict[str, Any] = {}
        
        # Thread/session cache (matches .NET _threadCache)
        self._thread_cache: Dict[str, Any] = {}
        
        # Initialization state
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
        logger.debug(f"BaseAgent created: {name}")
    
    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the agent's description."""
        return self._description
    
    @property
    def instructions(self) -> str:
        """Get the agent's system instructions."""
        return self._instructions
    
    @property
    def enable_long_running_memory(self) -> bool:
        """Check if long-running memory is enabled."""
        return self._enable_long_running_memory
    
    @enable_long_running_memory.setter
    def enable_long_running_memory(self, value: bool) -> None:
        """Set long-running memory flag."""
        self._enable_long_running_memory = value
    
    async def initialize_async(self) -> None:
        """
        Initialize the agent (thread-safe, matches .NET InitializeAsync).
        
        Override in subclasses to add custom initialization logic.
        """
        async with self._init_lock:
            if self._initialized:
                return
            
            try:
                logger.debug(f"Base initialization for agent {self._name}")
                await self._do_initialize_async()
                self._initialized = True
                logger.info(f"Agent '{self._name}' initialized")
            except Exception as ex:
                logger.error(f"Failed to initialize agent {self._name}: {str(ex)}")
                raise
    
    async def _do_initialize_async(self) -> None:
        """
        Internal initialization logic.
        
        Override in subclasses for custom initialization.
        """
        pass
    
    def _set_chat_client(self, chat_client) -> None:
        """Set the chat client (matches .NET SetChatClient)."""
        self._chat_client = chat_client
    
    async def respond_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response to a message (matches .NET RespondAsync).
        
        Args:
            message: User message
            conversation_history: Optional conversation history
            context: Optional additional context
            
        Returns:
            Agent's response string
        """
        if self._chat_client is None:
            await self.initialize_async()
        
        try:
            start_time = datetime.utcnow()
            
            # Create instructions with context
            system_prompt = self._instructions
            if context:
                system_prompt += f"\n\nAdditional Context: {context}"
            
            # Build messages for chat completion
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for history_msg in sorted(conversation_history, key=lambda m: m.timestamp):
                    role = "user" if history_msg.agent == "user" else "assistant"
                    messages.append({"role": role, "content": history_msg.content})
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Get response from chat client
            response = await self._get_chat_response(messages)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Agent {self._name} responded in {duration:.0f}ms")
            
            return response
            
        except Exception as ex:
            logger.error(f"Error in {self._name} responding to message: {str(ex)}")
            return f"I encountered an error while processing your request: {str(ex)}"
    
    async def _get_chat_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Get response from chat client. Override in subclasses.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Response string
        """
        if self._chat_client is None:
            return "Agent not properly initialized."
        
        # Default implementation - override in subclasses
        return "Agent not properly initialized."
    
    async def chat_async(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat request (matches .NET ChatAsync).
        
        Args:
            request: Chat request
            
        Returns:
            ChatResponse with content and metadata
        """
        return await self.chat_with_history_async(request, None)
    
    async def chat_with_history_async(
        self,
        request: ChatRequest,
        conversation_history: Optional[List[GroupChatMessage]] = None
    ) -> ChatResponse:
        """
        Process a chat with history (matches .NET ChatWithHistoryAsync).
        
        Args:
            request: Chat request
            conversation_history: Optional conversation history
            
        Returns:
            ChatResponse with content and metadata
        """
        session_id = request.session_id or str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            content = await self.respond_async(
                request.message,
                conversation_history,
                request.context
            )
            
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return ChatResponse(
                content=content,
                agent=self._name,
                session_id=session_id,
                timestamp=end_time,
                usage=UsageInfo(
                    prompt_tokens=self._estimate_tokens(request.message),
                    completion_tokens=self._estimate_tokens(content),
                    total_tokens=self._estimate_tokens(request.message) + self._estimate_tokens(content)
                ),
                processing_time_ms=processing_time_ms
            )
            
        except Exception as ex:
            logger.error(f"Error in {self._name} chat: {str(ex)}")
            raise
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (matches .NET EstimateTokens).
        
        Simple estimation: roughly 4 characters per token.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return max(1, len(text) // 4)
    
    def _get_memory_state_key(
        self,
        conversation_history: Optional[List[GroupChatMessage]]
    ) -> str:
        """
        Get memory state key for conversation (matches .NET GetMemoryStateKey).
        
        Args:
            conversation_history: Conversation history
            
        Returns:
            Memory state key string
        """
        if conversation_history and len(conversation_history) > 0:
            return f"memory_{conversation_history[0].message_id}"
        return "memory_default"
    
    def get_or_create_thread(
        self,
        conversation_history: Optional[List[GroupChatMessage]] = None
    ) -> str:
        """
        Get or create thread for conversation (matches .NET GetOrCreateThread pattern).
        
        Args:
            conversation_history: Optional conversation history
            
        Returns:
            Thread key string
        """
        thread_key = "default"
        if conversation_history and len(conversation_history) > 0:
            thread_key = f"conv_{conversation_history[0].message_id}"
        
        if thread_key not in self._thread_cache:
            self._thread_cache[thread_key] = str(uuid.uuid4())
            logger.debug(f"Created new thread for key: {thread_key}")
        
        return self._thread_cache[thread_key]
