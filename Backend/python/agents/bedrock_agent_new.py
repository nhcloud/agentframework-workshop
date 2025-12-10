"""
AWS Bedrock Agent implementation.

Matches .NET BedrockHRAgent pattern using AWS Bedrock Converse API.
Uses the same patterns as the .NET implementation including:
- Bedrock Runtime client
- Converse API for chat completions
- Instructions service integration
"""

import os
import logging
from typing import Optional, List, Dict, Any

from .base_agent_new import BaseAgent, GroupChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class BedrockHRAgent(BaseAgent):
    """
    AWS Bedrock HR Agent (matches .NET BedrockHRAgent).
    
    Uses AWS Bedrock for HR and workplace policy assistance.
    """
    
    def __init__(
        self,
        name: str = "bedrock_agent",
        description: str = "HR and workplace policy assistant powered by AWS Bedrock",
        instructions: str = "You are an HR and workplace policy assistant.",
        model_id: Optional[str] = None,
        enable_long_running_memory: bool = False
    ):
        """
        Initialize the Bedrock HR agent (matches .NET constructor pattern).
        
        Args:
            name: Agent name
            description: Agent description
            instructions: System instructions
            model_id: AWS Bedrock model ID
            enable_long_running_memory: Whether to enable long-running memory
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory
        )
        
        self._model_id = model_id or os.getenv("AWS_BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
        self._region = os.getenv("AWS_REGION", "us-east-1")
        
        # Bedrock client
        self._bedrock_client = None
        
        logger.info(f"BedrockHRAgent '{name}' created with model: {self._model_id}")
    
    async def _do_initialize_async(self) -> None:
        """Initialize the AWS Bedrock client."""
        try:
            import boto3
            
            self._bedrock_client = boto3.client(
                "bedrock-runtime",
                region_name=self._region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            
            logger.info(f"AWS Bedrock client initialized for region: {self._region}, model: {self._model_id}")
            
        except ImportError:
            logger.error("boto3 package not installed. Install with: pip install boto3")
            raise
        except Exception as ex:
            logger.error(f"Failed to initialize AWS Bedrock client: {str(ex)}")
            raise
    
    async def respond_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response using AWS Bedrock (matches .NET RespondAsync pattern).
        
        Args:
            message: User message
            conversation_history: Optional conversation history
            context: Optional additional context
            
        Returns:
            Agent's response string
        """
        # Ensure client is initialized
        if self._bedrock_client is None:
            await self.initialize_async()
        
        if self._bedrock_client is None:
            raise RuntimeError("AWS Bedrock client not initialized")
        
        try:
            from datetime import datetime
            import json
            
            start_time = datetime.utcnow()
            
            # Build conversation messages for Bedrock Converse API
            conversation = []
            
            # Add conversation history
            if conversation_history:
                for history_msg in sorted(conversation_history, key=lambda m: m.timestamp):
                    role = "user" if history_msg.agent == "user" else "assistant"
                    conversation.append({
                        "role": role,
                        "content": [{"text": history_msg.content}]
                    })
            
            # Add current user message with context
            enhanced_message = message
            if context:
                enhanced_message = f"{message}\n\nAdditional Context: {context}"
            
            conversation.append({
                "role": "user",
                "content": [{"text": enhanced_message}]
            })
            
            # Build system prompt
            system_prompt = [{"text": self._instructions}]
            
            # Call Bedrock Converse API
            response = self._bedrock_client.converse(
                modelId=self._model_id,
                messages=conversation,
                system=system_prompt,
                inferenceConfig={
                    "maxTokens": 4096,
                    "temperature": 0.7
                }
            )
            
            # Extract response text
            result = ""
            if "output" in response and "message" in response["output"]:
                output_message = response["output"]["message"]
                if "content" in output_message:
                    for content_block in output_message["content"]:
                        if "text" in content_block:
                            result += content_block["text"]
            
            if not result:
                result = "I apologize, but I couldn't generate a response."
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Agent {self._name} responded in {duration:.0f}ms")
            
            return result
            
        except Exception as ex:
            logger.error(f"AWS Bedrock chat error: {str(ex)}")
            return f"I encountered an error while processing your request: {str(ex)}"
    
    @classmethod
    def create_with_instructions_service(
        cls,
        instructions_service,
        enable_long_running_memory: bool = False
    ) -> "BedrockHRAgent":
        """
        Factory method to create agent with instructions service.
        
        Args:
            instructions_service: AgentInstructionsService instance
            enable_long_running_memory: Whether to enable memory
            
        Returns:
            Configured BedrockHRAgent instance
        """
        name = "bedrock_agent"
        instructions = instructions_service.get_agent_instructions(name)
        description = instructions_service.get_agent_description(name)
        
        return cls(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory
        )
