"""
AWS Bedrock Chat Client for Microsoft Agent Framework integration.

This module provides a custom chat client implementation that integrates
AWS Bedrock with the Microsoft Agent Framework.
"""

import json
import uuid
import logging
from typing import Any, AsyncIterable, MutableSequence, Dict, List
from collections.abc import AsyncIterable as AsyncIterableABC

import boto3
from botocore.exceptions import ClientError, BotoCoreError

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

# Handle both relative and absolute imports
try:
    from ..core.config import settings
except ImportError:
    from core.config import settings

logger = logging.getLogger(__name__)


@use_function_invocation
@use_chat_middleware
class AWSBedrockChatClient(BaseChatClient):
    """
    AWS Bedrock Chat Client implementation for Microsoft Agent Framework.
    
    This client integrates AWS Bedrock with the Agent Framework, allowing
    agents to use Amazon's foundation models through the unified interface.
    """
    
    OTEL_PROVIDER_NAME = "AWSBedrockChatClient"
    
    def __init__(
        self, 
        model_id: str = "amazon.nova-pro-v1:0",
        region_name: str = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        **kwargs
    ):
        """
        Initialize AWS Bedrock chat client.
        
        Args:
            model_id: The Bedrock model ID to use
            region_name: AWS region (defaults to us-east-1)
            aws_access_key_id: AWS access key (from env if not provided)
            aws_secret_access_key: AWS secret key (from env if not provided)
        """
        super().__init__(**kwargs)
        
        self.model_id = model_id
        self.region_name = region_name or settings.AWS_REGION or "us-east-1"
        
        # Initialize Bedrock client
        self._init_bedrock_client(aws_access_key_id, aws_secret_access_key)
        
        logger.info(f"Initialized AWS Bedrock client with model: {self.model_id}")
    
    def _init_bedrock_client(self, access_key: str = None, secret_key: str = None):
        """Initialize the Bedrock runtime client."""
        try:
            # Use provided credentials or fall back to environment/IAM
            session_kwargs = {}
            
            if access_key and secret_key:
                session_kwargs.update({
                    'aws_access_key_id': access_key,
                    'aws_secret_access_key': secret_key
                })
            elif settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                session_kwargs.update({
                    'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                    'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY
                })
            
            session_kwargs['region_name'] = self.region_name
            
            # Create Bedrock runtime client
            self.bedrock_client = boto3.client('bedrock-runtime', **session_kwargs)
            
            logger.info(f"AWS Bedrock client initialized for region: {self.region_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock client: {str(e)}")
            raise
    
    def _convert_messages_to_bedrock(self, messages: MutableSequence[ChatMessage]) -> List[Dict[str, Any]]:
        """Convert Agent Framework messages to Bedrock format."""
        bedrock_messages = []
        
        for msg in messages:
            role = "user" if msg.role == Role.USER else "assistant"
            
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
                bedrock_messages.append({
                    "role": role,
                    "content": text_content.strip()
                })
        
        return bedrock_messages
    
    def _create_bedrock_payload(self, messages: List[Dict[str, Any]], chat_options: ChatOptions) -> Dict[str, Any]:
        """Create the payload for Bedrock API call."""
        # Check if using Claude or Nova model
        if "claude" in self.model_id.lower():
            # Claude models use different format
            payload = {
                "messages": messages,
                "max_tokens": chat_options.max_tokens or 4096,
                "temperature": chat_options.temperature or 0.7,
                "anthropic_version": "bedrock-2023-05-31"
            }
            
            # Add other parameters if specified
            if chat_options.top_p is not None:
                payload["top_p"] = chat_options.top_p
        else:
            # Nova models use inferenceConfig format
            payload = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": chat_options.max_tokens or 4096,
                    "temperature": chat_options.temperature or 0.7,
                }
            }
            
            # Add other parameters if specified
            if chat_options.top_p is not None:
                payload["inferenceConfig"]["topP"] = chat_options.top_p
        
        return payload
    
    async def _inner_get_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        chat_options: ChatOptions,
        **kwargs: Any,
    ) -> ChatResponse:
        """Get a non-streaming response from AWS Bedrock."""
        try:
            # Convert messages to Bedrock format
            bedrock_messages = self._convert_messages_to_bedrock(messages)
            
            if not bedrock_messages:
                raise ValueError("No valid messages to send to Bedrock")
            
            # Create payload
            payload = self._create_bedrock_payload(bedrock_messages, chat_options)
            
            # Call Bedrock API
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text from response (different format for Claude vs Nova)
            if "claude" in self.model_id.lower():
                # Claude response format
                if 'content' in response_body and isinstance(response_body['content'], list):
                    response_text = response_body['content'][0].get('text', 'No response generated')
                else:
                    response_text = "No response generated"
            else:
                # Nova response format
                if 'output' in response_body and 'message' in response_body['output']:
                    message_content = response_body['output']['message']['content']
                    if isinstance(message_content, list) and len(message_content) > 0:
                        response_text = message_content[0].get('text', '')
                    else:
                        response_text = str(message_content)
                else:
                    response_text = "No response generated"
            
            # Create Agent Framework response
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                text=response_text
            )
            
            return ChatResponse(
                messages=[response_message],
                response_id=f"bedrock-{uuid.uuid4()}",
                model_id=self.model_id
            )
            
        except ClientError as e:
            error_msg = f"AWS Bedrock API error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Error calling AWS Bedrock: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def _inner_get_streaming_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        chat_options: ChatOptions,
        **kwargs: Any,
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Get a streaming response from AWS Bedrock."""
        try:
            # Convert messages to Bedrock format
            bedrock_messages = self._convert_messages_to_bedrock(messages)
            
            if not bedrock_messages:
                raise ValueError("No valid messages to send to Bedrock")
            
            # Create payload
            payload = self._create_bedrock_payload(bedrock_messages, chat_options)
            
            # Call Bedrock streaming API
            response = self.bedrock_client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json"
            )
            
            # Process streaming response (different format for Claude vs Nova)
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'].decode())
                
                if "claude" in self.model_id.lower():
                    # Claude streaming format
                    if 'delta' in chunk and 'text' in chunk['delta']:
                        text_chunk = chunk['delta']['text']
                        yield ChatResponseUpdate(
                            role=Role.ASSISTANT,
                            contents=[TextContent(text=text_chunk)]
                        )
                    elif 'message' in chunk and chunk.get('type') == 'message_stop':
                        break
                else:
                    # Nova streaming format
                    if 'contentBlockDelta' in chunk:
                        delta = chunk['contentBlockDelta']
                        if 'delta' in delta and 'text' in delta['delta']:
                            text_chunk = delta['delta']['text']
                            
                            yield ChatResponseUpdate(
                                role=Role.ASSISTANT,
                                contents=[TextContent(text=text_chunk)]
                            )
                    
                    # Handle completion
                    elif 'messageStop' in chunk:
                        break
                    
        except ClientError as e:
            error_msg = f"AWS Bedrock streaming API error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Error in AWS Bedrock streaming: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def service_url(self) -> str:
        """Return the service URL for AWS Bedrock."""
        return f"https://bedrock-runtime.{self.region_name}.amazonaws.com"