"""
Google Gemini Chat Client for Microsoft Agent Framework integration.

This module provides a custom chat client implementation that integrates
Google Gemini with the Microsoft Agent Framework.
"""

import json
import uuid
import logging
from typing import Any, AsyncIterable, MutableSequence, Dict, List, Optional
from collections.abc import AsyncIterable as AsyncIterableABC

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse, GenerationConfig
from google.api_core import exceptions as google_exceptions

from agent_framework import (
    BaseChatClient, 
    ChatMessage, 
    ChatOptions, 
    ChatResponse, 
    ChatResponseUpdate,
    Role,
    TextContent,
    use_chat_middleware,
    use_function_invocation
)

from core.config import settings

logger = logging.getLogger(__name__)


@use_function_invocation
@use_chat_middleware
class GoogleGeminiChatClient(BaseChatClient):
    """
    Google Gemini Chat Client implementation for Microsoft Agent Framework.
    
    This client integrates Google Gemini with the Agent Framework, allowing
    agents to use Google's Gemini models through the unified interface.
    """
    
    OTEL_PROVIDER_NAME = "GoogleGeminiChatClient"
    
    def __init__(
        self, 
        model_id: str = "gemini-pro",
        api_key: str = None,
        **kwargs
    ):
        """
        Initialize Google Gemini chat client.
        
        Args:
            model_id: The Gemini model ID to use (gemini-pro, gemini-pro-vision, etc.)
            api_key: Google API key (from env if not provided)
        """
        super().__init__(**kwargs)
        
        self.model_id = model_id
        self.api_key = api_key or settings.GOOGLE_API_KEY
        
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")
        
        # Initialize Gemini
        self._init_gemini()
        
        logger.info(f"Initialized Google Gemini client with model: {self.model_id}")
    
    def _init_gemini(self):
        """Initialize the Gemini model."""
        try:
            # Configure the API key
            genai.configure(api_key=self.api_key)
            
            # Create the model
            self.model = genai.GenerativeModel(self.model_id)
            
            logger.info(f"Google Gemini model initialized: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Gemini: {str(e)}")
            raise
    
    def _convert_messages_to_gemini(self, messages: MutableSequence[ChatMessage]) -> List[Dict[str, str]]:
        """Convert Agent Framework messages to Gemini format."""
        gemini_messages = []
        
        for msg in messages:
            # Gemini uses "user" and "model" roles
            role = "user" if msg.role == Role.USER else "model"
            
            # Extract text content
            text_content = ""
            if hasattr(msg, 'text') and msg.text:
                text_content = msg.text
            elif hasattr(msg, 'contents'):
                for content in msg.contents:
                    if isinstance(content, TextContent) or (hasattr(content, 'text') and content.text):
                        text_content += str(content.text or content)
            else:
                text_content = str(msg)
            
            if text_content.strip():
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": text_content.strip()}]
                })
        
        return gemini_messages
    
    def _create_generation_config(self, chat_options: ChatOptions) -> GenerationConfig:
        """Create generation config from chat options."""
        config_params = {}
        
        if chat_options.temperature is not None:
            config_params["temperature"] = chat_options.temperature
        
        if chat_options.max_tokens is not None:
            config_params["max_output_tokens"] = chat_options.max_tokens
        
        if chat_options.top_p is not None:
            config_params["top_p"] = chat_options.top_p
        
        return GenerationConfig(**config_params) if config_params else None
    
    async def _inner_get_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        chat_options: ChatOptions,
        **kwargs: Any,
    ) -> ChatResponse:
        """Get a non-streaming response from Google Gemini."""
        try:
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages_to_gemini(messages)
            
            if not gemini_messages:
                raise ValueError("No valid messages to send to Gemini")
            
            # Create generation config
            generation_config = self._create_generation_config(chat_options)
            
            # For single message interaction, use generate_content
            if len(gemini_messages) == 1 and gemini_messages[0]["role"] == "user":
                content = gemini_messages[0]["parts"][0]["text"]
                
                response = self.model.generate_content(
                    content,
                    generation_config=generation_config
                )
            else:
                # For multi-turn conversation, use chat
                chat_session = self.model.start_chat(
                    history=gemini_messages[:-1] if len(gemini_messages) > 1 else []
                )
                
                last_message = gemini_messages[-1]["parts"][0]["text"]
                response = chat_session.send_message(
                    last_message,
                    generation_config=generation_config
                )
            
            # Extract response text
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    response_text = candidate.content.parts[0].text
            
            if not response_text:
                response_text = "No response generated"
            
            # Create Agent Framework response
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                text=response_text
            )
            
            return ChatResponse(
                messages=[response_message],
                response_id=f"gemini-{uuid.uuid4()}",
                model_id=self.model_id
            )
            
        except google_exceptions.GoogleAPIError as e:
            error_msg = f"Google Gemini API error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Error calling Google Gemini: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def _inner_get_streaming_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        chat_options: ChatOptions,
        **kwargs: Any,
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Get a streaming response from Google Gemini."""
        try:
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages_to_gemini(messages)
            
            if not gemini_messages:
                raise ValueError("No valid messages to send to Gemini")
            
            # Create generation config
            generation_config = self._create_generation_config(chat_options)
            
            # For single message interaction, use generate_content with streaming
            if len(gemini_messages) == 1 and gemini_messages[0]["role"] == "user":
                content = gemini_messages[0]["parts"][0]["text"]
                
                response_stream = self.model.generate_content(
                    content,
                    generation_config=generation_config,
                    stream=True
                )
            else:
                # For multi-turn conversation, use chat with streaming
                chat_session = self.model.start_chat(
                    history=gemini_messages[:-1] if len(gemini_messages) > 1 else []
                )
                
                last_message = gemini_messages[-1]["parts"][0]["text"]
                response_stream = chat_session.send_message(
                    last_message,
                    generation_config=generation_config,
                    stream=True
                )
            
            # Process streaming response
            for chunk in response_stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield ChatResponseUpdate(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text=chunk.text)]
                    )
                elif hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                yield ChatResponseUpdate(
                                    role=Role.ASSISTANT,
                                    contents=[TextContent(text=part.text)]
                                )
                    
        except google_exceptions.GoogleAPIError as e:
            error_msg = f"Google Gemini streaming API error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Error in Google Gemini streaming: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def service_url(self) -> str:
        """Return the service URL for Google Gemini."""
        return "https://generativelanguage.googleapis.com"