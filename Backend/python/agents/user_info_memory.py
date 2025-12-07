"""
UserInfoMemory - Long-running memory provider for Microsoft Agent Framework (Python)

This module provides a memory system that extracts and remembers user information
(name, persona) across conversations, matching the .NET implementation.
"""

import json
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from agent_framework import AIContextProvider, InvokingContext, InvokedContext, AIContext
from microsoft.extensions.ai import IChatClient, ChatRole, ChatOptions


@dataclass
class UserInfo:
    """Stores user information extracted from conversations."""
    user_name: Optional[str] = None
    user_persona: Optional[str] = None
    has_asked_for_name: bool = False
    has_asked_for_persona: bool = False


class UserInfoMemory(AIContextProvider):
    """
    AI Context Provider that extracts and remembers user information.
    
    This provider:
    - Extracts user name and persona from messages
    - Stores information across conversation turns
    - Provides personalized context to the agent
    - Serializes/deserializes state for persistence
    """
    
    def __init__(self, chat_client: IChatClient, user_info: Optional[UserInfo] = None, 
                 serialized_state: Optional[Dict[str, Any]] = None):
        """
        Initialize UserInfoMemory provider.
        
        Args:
            chat_client: The chat client for extraction queries
            user_info: Optional pre-populated user info
            serialized_state: Optional serialized state to restore from
        """
        self._chat_client = chat_client
        self._has_asked_for_name = False
        self._has_asked_for_persona = False
        
        if serialized_state:
            self.user_info = UserInfo(**serialized_state) if isinstance(serialized_state, dict) else UserInfo()
            # Restore the "asked" flags from serialized state
            self._has_asked_for_name = bool(self.user_info.user_name) or self.user_info.has_asked_for_name
            self._has_asked_for_persona = bool(self.user_info.user_persona) or self.user_info.has_asked_for_persona
        else:
            self.user_info = user_info or UserInfo()
    
    async def invoked_async(self, context: InvokedContext, cancellation_token: Optional[Any] = None) -> None:
        """
        Called after the agent processes a request to extract user information.
        
        Args:
            context: The invoked context with request/response messages
            cancellation_token: Optional cancellation token
        """
        # Only try to extract user info if we don't have it already and there are user messages
        if (not self.user_info.user_name or not self.user_info.user_persona):
            user_messages = [msg for msg in context.request_messages if msg.role == ChatRole.User]
            
            if user_messages:
                try:
                    # Get the last user message to check for name/persona
                    last_user_message = user_messages[-1]
                    message_text = last_user_message.text or ""
                    
                    # Only extract if the message seems to contain personal information
                    if self._could_contain_user_info(message_text):
                        # Use structured output to extract user info
                        extraction_prompt = [
                            {
                                "role": "system",
                                "content": "Extract ONLY the user's name and persona/age from the message if explicitly provided. Return nulls if not clearly stated. Examples: 'My name is John' ? user_name='John', 'I'm a developer' ? user_persona='developer', 'I'm 25' ? user_persona='25 years old'"
                            },
                            {
                                "role": "user",
                                "content": message_text
                            }
                        ]
                        
                        # Simple extraction using pattern matching (fallback if no structured output available)
                        extracted_info = self._extract_user_info_pattern(message_text)
                        
                        # Update if we got new information
                        if extracted_info.get("user_name"):
                            self.user_info.user_name = extracted_info["user_name"]
                        
                        if extracted_info.get("user_persona"):
                            self.user_info.user_persona = extracted_info["user_persona"]
                            
                except Exception:
                    # If extraction fails, just continue without user info
                    # Don't block the conversation
                    pass
    
    async def invoking_async(self, context: InvokingContext, cancellation_token: Optional[Any] = None) -> AIContext:
        """
        Called before the agent processes a request to provide context.
        
        Args:
            context: The invoking context
            cancellation_token: Optional cancellation token
            
        Returns:
            AIContext with instructions for the agent
        """
        instructions = []
        
        # Provide information we have, and gently ask for missing info (but don't block)
        if self.user_info.user_name:
            instructions.append(f"The user's name is {self.user_info.user_name}.")
        elif not self._has_asked_for_name:
            instructions.append("If appropriate and natural in the conversation, you may ask the user for their name. But DO NOT block answering their questions.")
            self._has_asked_for_name = True
            self.user_info.has_asked_for_name = True
        
        if self.user_info.user_persona:
            instructions.append(f"The user's persona/background: {self.user_info.user_persona}.")
        elif not self._has_asked_for_persona and self.user_info.user_name:
            instructions.append("If it feels natural, you may ask about their role or background. But DO NOT block answering their questions.")
            self._has_asked_for_persona = True
            self.user_info.has_asked_for_persona = True
        
        # If we have user info, encourage personalized responses
        if self.user_info.user_name or self.user_info.user_persona:
            instructions.append("Use this information to personalize your responses when appropriate.")
        
        return AIContext(
            instructions="\n".join(instructions) if instructions else None
        )
    
    def serialize(self) -> Dict[str, Any]:
        """
        Serialize the user info state for persistence.
        
        Returns:
            Dictionary representation of user info
        """
        return asdict(self.user_info)
    
    @staticmethod
    def _could_contain_user_info(message: str) -> bool:
        """
        Check if a message might contain user information to avoid unnecessary extraction calls.
        
        Args:
            message: The message text to check
            
        Returns:
            True if the message likely contains user info
        """
        lower_message = message.lower()
        
        # Check for common patterns that indicate user info
        return any([
            "name" in lower_message,
            "i'm " in lower_message,
            "i m " in lower_message,
            "i am " in lower_message,
            "persona" in lower_message,
            "call me" in lower_message,
        ])
    
    @staticmethod
    def _extract_user_info_pattern(message: str) -> Dict[str, Optional[str]]:
        """
        Extract user information using pattern matching (fallback method).
        
        Args:
            message: The message text
            
        Returns:
            Dictionary with extracted user_name and user_persona
        """
        result = {"user_name": None, "user_persona": None}
        
        # Name extraction patterns
        name_patterns = [
            r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]+)",
            r"name['']?s\s+([A-Z][a-z]+)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                result["user_name"] = match.group(1).strip()
                break
        
        # Persona extraction patterns
        persona_patterns = [
            r"i(?:'m| am)\s+a\s+([a-z\s]+?)(?:\s+and|\s+at|\.|$)",
            r"work(?:ing)?\s+as\s+a\s+([a-z\s]+?)(?:\s+and|\s+at|\.|$)",
            r"i(?:'m| am)\s+(\d+)\s+years?\s+old",
        ]
        
        persona_parts = []
        for pattern in persona_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                persona_parts.append(match.group(1).strip())
        
        if persona_parts:
            result["user_persona"] = ", ".join(persona_parts)
        
        return result


# Helper function to create UserInfoMemory from serialized state
def create_user_info_memory(chat_client: IChatClient, serialized_state: Optional[str] = None) -> UserInfoMemory:
    """
    Factory function to create UserInfoMemory with optional serialized state.
    
    Args:
        chat_client: The chat client for extraction queries
        serialized_state: Optional JSON string with serialized state
        
    Returns:
        UserInfoMemory instance
    """
    state_dict = None
    if serialized_state:
        try:
            state_dict = json.loads(serialized_state)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return UserInfoMemory(chat_client, serialized_state=state_dict)
