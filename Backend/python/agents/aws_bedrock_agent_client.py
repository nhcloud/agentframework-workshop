"""
AWS Bedrock Agent Runtime Client for Microsoft Agent Framework

This module provides integration with existing AWS Bedrock Agents using the
AWS Bedrock Agent Runtime API. This is different from the direct model invocation
approach and is designed for use with pre-existing Bedrock agents.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import boto3
from agent_framework import BaseChatClient, ChatMessage
from agent_framework.exceptions import ServiceException

logger = logging.getLogger(__name__)


class AWSBedrockAgentClient(BaseChatClient):
    """
    AWS Bedrock Agent Runtime client for Microsoft Agent Framework.
    
    This client integrates with existing AWS Bedrock agents using the 
    AWS Bedrock Agent Runtime API rather than direct model invocation.
    
    Used for agents that have been pre-configured in AWS Bedrock console
    with specific knowledge bases, action groups, and tools.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_alias_id: str = "TSTALIASID",  # Default test alias
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None
    ):
        """
        Initialize the AWS Bedrock Agent client.
        
        Args:
            agent_id: The AWS Bedrock Agent ID
            agent_alias_id: The agent alias ID (defaults to test alias)
            region_name: AWS region name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: Optional AWS session token
        """
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.region_name = region_name
        
        # Initialize boto3 client
        session_kwargs = {
            'region_name': region_name
        }
        
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            })
            
        if aws_session_token:
            session_kwargs['aws_session_token'] = aws_session_token
        
        try:
            self.session = boto3.Session(**session_kwargs)
            self.client = self.session.client('bedrock-agent-runtime')
            logger.info(f"Initialized AWS Bedrock Agent client for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock Agent client: {str(e)}")
            raise ServiceException(f"Failed to initialize AWS Bedrock Agent client: {str(e)}")
    
    async def get_response(
        self,
        messages: List[ChatMessage],
        **kwargs: Any
    ) -> ChatMessage:
        """
        Get response from AWS Bedrock Agent using Agent Runtime API.
        
        Args:
            messages: List of chat messages
            **kwargs: Additional parameters
            
        Returns:
            ChatMessage with agent response
        """
        try:
            # Get the last user message for the agent
            user_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'role') and msg.role and msg.role.lower() == 'user':
                    user_message = msg.content if hasattr(msg, 'content') else str(msg)
                    break
            
            if not user_message:
                user_message = str(messages[-1]) if messages else "Hello"
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Invoke the Bedrock agent
            response = await self._invoke_agent(user_message, session_id)
            
            # Extract response text
            response_text = self._extract_response_text(response)
            
            # Return as ChatMessage
            return ChatMessage(
                role="assistant",
                content=response_text
            )
            
        except Exception as e:
            logger.error(f"Error getting response from AWS Bedrock Agent: {str(e)}")
            raise ServiceException(f"AWS Bedrock Agent error: {str(e)}")
    
    async def get_response_stream(
        self,
        messages: List[ChatMessage],
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Get streaming response from AWS Bedrock Agent.
        
        Args:
            messages: List of chat messages
            **kwargs: Additional parameters
            
        Yields:
            Response chunks as strings
        """
        try:
            # Get the last user message
            user_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'role') and msg.role and msg.role.lower() == 'user':
                    user_message = msg.content if hasattr(msg, 'content') else str(msg)
                    break
            
            if not user_message:
                user_message = str(messages[-1]) if messages else "Hello"
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Invoke the agent with streaming
            async for chunk in self._invoke_agent_stream(user_message, session_id):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error getting streaming response from AWS Bedrock Agent: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def _invoke_agent(self, message: str, session_id: str) -> Dict[str, Any]:
        """Invoke the Bedrock agent with a message."""
        try:
            loop = asyncio.get_event_loop()
            
            # Run the synchronous boto3 call in a thread pool
            response = await loop.run_in_executor(
                None,
                lambda: self.client.invoke_agent(
                    agentId=self.agent_id,
                    agentAliasId=self.agent_alias_id,
                    sessionId=session_id,
                    inputText=message
                )
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to invoke Bedrock agent: {str(e)}")
            raise ServiceException(f"Failed to invoke Bedrock agent: {str(e)}")
    
    async def _invoke_agent_stream(self, message: str, session_id: str) -> AsyncGenerator[str, None]:
        """Invoke the Bedrock agent with streaming response."""
        try:
            loop = asyncio.get_event_loop()
            
            # Run the synchronous boto3 call in a thread pool
            response = await loop.run_in_executor(
                None,
                lambda: self.client.invoke_agent(
                    agentId=self.agent_id,
                    agentAliasId=self.agent_alias_id,
                    sessionId=session_id,
                    inputText=message
                )
            )
            
            # Process the completion event stream
            if 'completion' in response:
                for event in response['completion']:
                    if 'chunk' in event:
                        chunk = event['chunk']
                        if 'bytes' in chunk:
                            chunk_data = json.loads(chunk['bytes'].decode('utf-8'))
                            if 'attribution' in chunk_data and 'textResponsePart' in chunk_data['attribution']:
                                text = chunk_data['attribution']['textResponsePart'].get('text', '')
                                if text:
                                    yield text
                            elif 'textResponsePart' in chunk_data:
                                text = chunk_data['textResponsePart'].get('text', '')
                                if text:
                                    yield text
                                    
        except Exception as e:
            logger.error(f"Failed to invoke Bedrock agent stream: {str(e)}")
            yield f"Error: {str(e)}"
    
    def _extract_response_text(self, response: Dict[str, Any]) -> str:
        """Extract response text from Bedrock agent response."""
        try:
            # Extract text from completion event stream
            text_parts = []
            
            if 'completion' in response:
                for event in response['completion']:
                    if 'chunk' in event:
                        chunk = event['chunk']
                        if 'bytes' in chunk:
                            chunk_data = json.loads(chunk['bytes'].decode('utf-8'))
                            
                            # Handle different response formats
                            if 'attribution' in chunk_data and 'textResponsePart' in chunk_data['attribution']:
                                text = chunk_data['attribution']['textResponsePart'].get('text', '')
                                if text:
                                    text_parts.append(text)
                            elif 'textResponsePart' in chunk_data:
                                text = chunk_data['textResponsePart'].get('text', '')
                                if text:
                                    text_parts.append(text)
                            elif 'text' in chunk_data:
                                text_parts.append(chunk_data['text'])
            
            response_text = ''.join(text_parts)
            
            if not response_text:
                response_text = "I apologize, but I couldn't generate a response."
            
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to extract response text: {str(e)}")
            return f"Error extracting response: {str(e)}"
    
    def create_agent(self, name: str = None, instructions: str = None, **kwargs) -> 'BedrockAgentWrapper':
        """
        Create an agent wrapper for Agent Framework compatibility.
        
        Args:
            name: Agent name (optional, for display purposes)
            instructions: Instructions (optional, existing agent already configured)
            **kwargs: Additional parameters
            
        Returns:
            BedrockAgentWrapper instance
        """
        return BedrockAgentWrapper(
            client=self,
            name=name or f"BedrockAgent-{self.agent_id}",
            instructions=instructions
        )


class BedrockAgentWrapper:
    """
    Wrapper class to provide Agent Framework compatibility for Bedrock agents.
    """
    
    def __init__(self, client: AWSBedrockAgentClient, name: str, instructions: str = None):
        self.client = client
        self.name = name
        self.instructions = instructions
        
    async def run(self, message: str, **kwargs) -> Any:
        """
        Run the agent with a message.
        
        Args:
            message: Input message
            **kwargs: Additional parameters
            
        Returns:
            Response object with content attribute
        """
        # Convert string message to ChatMessage
        chat_message = ChatMessage(role="user", content=message)
        
        # Get response from client
        response = await self.client.get_response([chat_message], **kwargs)
        
        # Return response with content attribute
        class AgentResponse:
            def __init__(self, content: str):
                self.content = content
                
            def __str__(self):
                return self.content
        
        return AgentResponse(response.content)