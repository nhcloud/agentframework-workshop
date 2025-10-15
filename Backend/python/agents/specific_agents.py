"""
Specific agent implementations for the Microsoft Agent Framework application.

This module contains specialized agents that use the official Microsoft Agent Framework
and provides specific functionality for different use cases.
"""

import os
import logging
from typing import Optional, List, Any, Dict

from agent_framework import ChatAgent, ChatMessage, AgentRunResponse, HostedFileSearchTool, HostedVectorStoreContent
from agent_framework.azure import AzureOpenAIChatClient, AzureAIAgentClient
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential

# Import custom chat clients
from clients.aws_bedrock_client import AWSBedrockChatClient
from clients.aws_bedrock_agent_client import AWSBedrockAgentClient
from clients.google_gemini_client import GoogleGeminiChatClient
from core.config import settings

logger = logging.getLogger(__name__)


class GenericAgent:
    """
    A generic, versatile agent for general-purpose tasks using Microsoft Agent Framework
    with Azure OpenAI chat completion.
    """
    
    def __init__(self, name: str = "generic_agent"):
        self.name = name or "GenericAgent"
        self.agent = None
        self._initialized = False
        self.agent_type = "generic"  # Add agent_type for group chat service
        logger.info(f"Initializing {self.name} using Microsoft Agent Framework")
    
    def initialize(self):
        """Initialize the Agent Framework agent with Azure OpenAI client."""
        try:
            if not settings.AZURE_OPENAI_ENDPOINT:
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
            if not settings.AZURE_OPENAI_API_KEY:
                raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
            if not settings.AZURE_OPENAI_DEPLOYMENT_NAME:
                raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is required")
            
            # Create Azure OpenAI chat client using Agent Framework
            chat_client = AzureOpenAIChatClient(
                deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION or "2024-02-01"
            )
            
            # Create agent using the chat client's create_agent method
            self.agent = chat_client.create_agent(
                name=self.name,
                instructions="You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions."
            )
            
            self._initialized = True
            logger.info(f"Initialized {self.name} with Microsoft Agent Framework and Azure OpenAI")
            
        except Exception as e:
            logger.error(f"Failed to initialize GenericAgent: {str(e)}")
            raise
    
    async def run(self, message: str, context: Optional[dict] = None) -> str:
        """
        Execute the agent with a message using Microsoft Agent Framework.
        
        Args:
            message: The user message to process
            context: Optional context (not used for generic agent)
            
        Returns:
            The agent's response as a string
        """
        try:
            if not self.agent:
                self.initialize()
            
            # Use Agent Framework's run method
            response = await self.agent.run(message)
            
            # Extract text content from the response
            if hasattr(response, 'content') and response.content:
                result = response.content
            elif isinstance(response, str):
                result = response
            else:
                result = str(response)
                
            logger.info(f"GenericAgent completed successfully using Agent Framework")
            return result or "I apologize, but I couldn't generate a response."
                
        except Exception as e:
            logger.error(f"Error running GenericAgent with Agent Framework: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self._initialized = False
            self.agent = None
        except Exception as e:
            logger.error(f"Error during GenericAgent cleanup: {str(e)}")
    
    def get_info(self) -> dict:
        """Get agent information."""
        return {
            "name": self.name,
            "type": "agent_framework_azure_openai",
            "initialized": self._initialized,
            "deployment": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            "framework": "Microsoft Agent Framework"
        }


class PeopleLookupAgent:
    """
    Specialized agent for finding people information within an organization.
    
    This agent connects to an existing Azure AI Foundry agent using Microsoft Agent Framework
    with employee knowledge bases and people search capabilities.
    """
    
    def __init__(self):
        self.name = "PeopleLookupAgent"
        self.agent_id = settings.PEOPLE_AGENT_ID
        self.agent = None
        self._initialized = False
        self.agent_type = "people_lookup"  # Add agent_type for group chat service
        
        if not self.agent_id:
            raise ValueError("PEOPLE_AGENT_ID environment variable is required")
        
        logger.info(f"Initializing PeopleLookupAgent with Agent Framework for Azure AI agent: {self.agent_id}")
    
    async def initialize(self):
        """Initialize using Agent Framework with Azure AI client."""
        try:
            if not settings.AZURE_AI_PROJECT_ENDPOINT:
                raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
            
            # Create credential and project client
            self.credential = AzureCliCredential()
            self.project_client = AIProjectClient(
                endpoint=settings.AZURE_AI_PROJECT_ENDPOINT,
                credential=self.credential
            )
            
            # Retrieve the existing agent from Azure AI Foundry with knowledge bases
            self.azure_ai_agent = await self.project_client.agents.get_agent(self.agent_id)
            logger.info(f"Retrieved existing agent: {self.azure_ai_agent.id} with knowledge bases")
            
            # Get vector stores from the existing agent's tool resources
            self.vector_store_ids = []
            if hasattr(self.azure_ai_agent, 'tool_resources') and self.azure_ai_agent.tool_resources:
                if hasattr(self.azure_ai_agent.tool_resources, 'file_search') and self.azure_ai_agent.tool_resources.file_search:
                    if hasattr(self.azure_ai_agent.tool_resources.file_search, 'vector_store_ids'):
                        self.vector_store_ids = self.azure_ai_agent.tool_resources.file_search.vector_store_ids or []
            
            logger.info(f"PeopleLookupAgent found {len(self.vector_store_ids)} vector stores: {self.vector_store_ids}")
            
            # Create Azure AI Agent client using Agent Framework (uses existing agent)
            self.azure_ai_client = AzureAIAgentClient(
                project_client=self.project_client,
                agent_id=self.agent_id
            )
            
            self._initialized = True
            logger.info(f"Initialized {self.name} with Microsoft Agent Framework and Azure AI Foundry")
            
        except Exception as e:
            logger.error(f"Failed to initialize PeopleLookupAgent: {str(e)}")
            raise
    
    async def run(self, message: str, context: Optional[dict] = None) -> str:
        """Execute the agent using Microsoft Agent Framework."""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Create file search tool with the agent's vector stores
            file_search_tool = None
            if self.vector_store_ids:
                try:
                    vector_store_contents = [HostedVectorStoreContent(vector_store_id=vs_id) for vs_id in self.vector_store_ids]
                    file_search_tool = HostedFileSearchTool(inputs=vector_store_contents)
                    logger.info(f"Created file search tool with {len(self.vector_store_ids)} vector stores")
                except Exception as e:
                    logger.error(f"Failed to create file search tool: {str(e)}")
                    file_search_tool = None
            else:
                logger.warning("No vector stores found, running without file search")
            
            # Use ChatAgent as context manager with file search capabilities
            async with ChatAgent(
                chat_client=self.azure_ai_client,
                instructions="You are a specialized agent for finding people information within the organization. Use your knowledge base and file search capabilities to provide accurate employee information.",
                tools=file_search_tool if file_search_tool else None
            ) as agent:
                response = await agent.run(message)
                
                if hasattr(response, 'content') and response.content:
                    result = response.content
                elif isinstance(response, str):
                    result = response
                else:
                    result = str(response)
                    
                logger.info(f"PeopleLookupAgent completed successfully")
                return result
            
        except Exception as e:
            logger.error(f"Error running PeopleLookupAgent: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'project_client') and self.project_client:
                await self.project_client.close()
            if hasattr(self, 'credential') and self.credential:
                await self.credential.close()
            self._initialized = False
        except Exception as e:
            logger.error(f"Error during PeopleLookupAgent cleanup: {str(e)}")
    
    def get_info(self) -> dict:
        """Get agent information."""
        return {
            "name": self.name,
            "agent_id": self.agent_id,
            "type": "agent_framework_azure_ai",
            "initialized": self._initialized,
            "framework": "Microsoft Agent Framework"
        }


class KnowledgeFinderAgent:
    """
    Specialized agent for searching and retrieving organizational knowledge.
    
    This agent connects to an existing Azure AI Foundry agent using Microsoft Agent Framework
    with organizational knowledge bases, documents, and policies.
    """
    
    def __init__(self):
        self.name = "KnowledgeFinderAgent"
        self.agent_id = settings.KNOWLEDGE_AGENT_ID
        self.agent = None
        self._initialized = False
        self.agent_type = "knowledge_finder"  # Add agent_type for group chat service
        
        if not self.agent_id:
            raise ValueError("KNOWLEDGE_AGENT_ID environment variable is required")
        
        logger.info(f"Initializing KnowledgeFinderAgent with Agent Framework for Azure AI agent: {self.agent_id}")
    
    async def initialize(self):
        """Initialize using Agent Framework with Azure AI client."""
        try:
            if not settings.AZURE_AI_PROJECT_ENDPOINT:
                raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
            
            # Create credential and project client
            self.credential = AzureCliCredential()
            self.project_client = AIProjectClient(
                endpoint=settings.AZURE_AI_PROJECT_ENDPOINT,
                credential=self.credential
            )
            
            # Retrieve the existing agent from Azure AI Foundry with knowledge bases
            self.azure_ai_agent = await self.project_client.agents.get_agent(self.agent_id)
            logger.info(f"Retrieved existing agent: {self.azure_ai_agent.id} with knowledge bases")
            
            # Get vector stores from the existing agent's tool resources
            self.vector_store_ids = []
            if hasattr(self.azure_ai_agent, 'tool_resources') and self.azure_ai_agent.tool_resources:
                if hasattr(self.azure_ai_agent.tool_resources, 'file_search') and self.azure_ai_agent.tool_resources.file_search:
                    if hasattr(self.azure_ai_agent.tool_resources.file_search, 'vector_store_ids'):
                        self.vector_store_ids = self.azure_ai_agent.tool_resources.file_search.vector_store_ids or []
            
            logger.info(f"KnowledgeFinderAgent found {len(self.vector_store_ids)} vector stores: {self.vector_store_ids}")
            
            # Create Azure AI Agent client using Agent Framework (uses existing agent)
            self.azure_ai_client = AzureAIAgentClient(
                project_client=self.project_client,
                agent_id=self.agent_id
            )
            
            self._initialized = True
            logger.info(f"Initialized {self.name} with Microsoft Agent Framework and Azure AI Foundry")
            
        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeFinderAgent: {str(e)}")
            raise
    
    async def run(self, message: str, context: Optional[dict] = None) -> str:
        """Execute the agent using Microsoft Agent Framework."""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Create file search tool with the agent's vector stores
            file_search_tool = None
            if self.vector_store_ids:
                try:
                    vector_store_contents = [HostedVectorStoreContent(vector_store_id=vs_id) for vs_id in self.vector_store_ids]
                    file_search_tool = HostedFileSearchTool(inputs=vector_store_contents)
                    logger.info(f"Created file search tool with {len(self.vector_store_ids)} vector stores")
                except Exception as e:
                    logger.error(f"Failed to create file search tool: {str(e)}")
                    file_search_tool = None
            else:
                logger.warning("No vector stores found, running without file search")
            
            # Use ChatAgent as context manager with file search capabilities
            async with ChatAgent(
                chat_client=self.azure_ai_client,
                instructions="You are a specialized agent for searching organizational knowledge. Use your knowledge base and file search capabilities to provide accurate information about policies, documents, and procedures.",
                tools=file_search_tool if file_search_tool else None
            ) as agent:
                response = await agent.run(message)
                
                if hasattr(response, 'content') and response.content:
                    result = response.content
                elif isinstance(response, str):
                    result = response
                else:
                    result = str(response)
                    
                logger.info(f"KnowledgeFinderAgent completed successfully")
                return result
            
        except Exception as e:
            logger.error(f"Error running KnowledgeFinderAgent: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'project_client') and self.project_client:
                await self.project_client.close()
            if hasattr(self, 'credential') and self.credential:
                await self.credential.close()
            self._initialized = False
        except Exception as e:
            logger.error(f"Error during KnowledgeFinderAgent cleanup: {str(e)}")
    
    def get_info(self) -> dict:
        """Get agent information."""
        return {
            "name": self.name,
            "agent_id": self.agent_id,
            "type": "agent_framework_azure_ai",
            "initialized": self._initialized,
            "framework": "Microsoft Agent Framework"
        }


class BedrockAgent:
    """
    AWS Bedrock agent using Microsoft Agent Framework.
    
    Supports two modes:
    1. Existing Agent Mode: Uses AWS_BEDROCK_AGENT_ID to connect to pre-configured Bedrock agents
    2. Direct Model Mode: Uses AWS_BEDROCK_MODEL_ID for direct model invocation
    
    This agent provides access to Amazon's foundation models through AWS Bedrock
    while maintaining compatibility with the Agent Framework.
    """
    
    def __init__(self, name: str = "bedrock_agent"):
        self.name = name or "BedrockAgent"
        self.agent = None
        self._initialized = False
        self.agent_type = "bedrock"  # Add agent_type for group chat service
        self.agent_id = settings.AWS_BEDROCK_AGENT_ID
        
        mode = "Existing Agent" if self.agent_id else "Direct Model"
        logger.info(f"Initializing {self.name} using AWS Bedrock with Agent Framework ({mode} mode)")
    
    def initialize(self):
        """Initialize the Agent Framework agent with AWS Bedrock client."""
        try:
            # Validate AWS configuration
            if not settings.AWS_ACCESS_KEY_ID:
                raise ValueError("AWS_ACCESS_KEY_ID environment variable is required")
            if not settings.AWS_SECRET_ACCESS_KEY:
                raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is required")
            
            # Choose between existing agent or direct model invocation
            if self.agent_id:
                # Existing Agent Mode: Use Bedrock Agent Runtime API (retrieval, not creation)
                logger.info(f"Using existing AWS Bedrock agent: {self.agent_id}")
                bedrock_client = AWSBedrockAgentClient(
                    agent_id=self.agent_id,
                    region_name=settings.AWS_REGION or "us-east-1",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                
                # For existing agents, we use ChatAgent with the client directly
                # The existing agent already has its instructions configured in AWS Bedrock
                self.agent = ChatAgent(
                    name=self.name,
                    chat_client=bedrock_client,
                    instructions="Existing AWS Bedrock agent - instructions managed in AWS Console"
                )
                
                logger.info(f"Initialized {self.name} with existing AWS Bedrock agent {self.agent_id}")
            else:
                # Direct Model Mode: Use direct model invocation
                logger.info(f"Using direct AWS Bedrock model: {settings.AWS_BEDROCK_MODEL_ID}")
                bedrock_client = AWSBedrockChatClient(
                    model_id=settings.AWS_BEDROCK_MODEL_ID or "amazon.nova-pro-v1:0",
                    region_name=settings.AWS_REGION or "us-east-1",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                
                # Create ChatAgent with the Bedrock client
                self.agent = ChatAgent(
                    name=self.name,
                    chat_client=bedrock_client,
                    instructions="You are a helpful AI assistant powered by AWS Bedrock. Provide clear, accurate, and helpful responses to user questions."
                )
                
                logger.info(f"Initialized {self.name} with direct AWS Bedrock model")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize BedrockAgent: {str(e)}")
            raise
    
    async def run(self, message: str, context: Optional[dict] = None) -> str:
        """
        Execute the agent with a message using Microsoft Agent Framework.
        
        Args:
            message: The user message to process
            context: Optional context (not used for bedrock agent)
            
        Returns:
            The agent's response as a string
        """
        try:
            if not self.agent:
                self.initialize()
            
            # Use Agent Framework's run method
            response = await self.agent.run(message)
            
            # Extract text content from the response
            if hasattr(response, 'content') and response.content:
                result = response.content
            elif isinstance(response, str):
                result = response
            else:
                result = str(response)
                
            logger.info(f"BedrockAgent completed successfully using Agent Framework")
            return result or "I apologize, but I couldn't generate a response."
                
        except Exception as e:
            logger.error(f"Error running BedrockAgent with Agent Framework: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self._initialized = False
            self.agent = None
        except Exception as e:
            logger.error(f"Error during BedrockAgent cleanup: {str(e)}")
    
    def get_info(self) -> dict:
        """Get agent information."""
        info = {
            "name": self.name,
            "type": "agent_framework_aws_bedrock",
            "initialized": self._initialized,
            "framework": "Microsoft Agent Framework"
        }
        
        if self.agent_id:
            info.update({
                "mode": "existing_agent",
                "agent_id": self.agent_id,
                "description": f"AWS Bedrock existing agent {self.agent_id}"
            })
        else:
            info.update({
                "mode": "direct_model",
                "model": settings.AWS_BEDROCK_MODEL_ID or "amazon.nova-pro-v1:0",
                "description": f"AWS Bedrock direct model invocation"
            })
        
        return info


class GeminiAgent:
    """
    Google Gemini agent using Microsoft Agent Framework with custom Gemini chat client.
    
    This agent provides access to Google's Gemini models while maintaining 
    compatibility with the Agent Framework.
    """
    
    def __init__(self, name: str = "gemini_agent"):
        self.name = name or "GeminiAgent"
        self.agent = None
        self._initialized = False
        self.agent_type = "gemini"  # Add agent_type for group chat service
        logger.info(f"Initializing {self.name} using Google Gemini with Agent Framework")
    
    def initialize(self):
        """Initialize the Agent Framework agent with Google Gemini client."""
        try:
            # Validate Google configuration
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY environment variable is required")
            
            # Create Google Gemini chat client using Agent Framework
            gemini_client = GoogleGeminiChatClient(
                model_id=settings.GOOGLE_GEMINI_MODEL_ID or "gemini-2.0-flash",
                api_key=settings.GOOGLE_API_KEY
            )
            
            # Create agent using the chat client's create_agent method
            self.agent = gemini_client.create_agent(
                name=self.name,
                instructions="You are a helpful AI assistant powered by Google Gemini. Provide clear, accurate, and helpful responses to user questions."
            )
            
            self._initialized = True
            logger.info(f"Initialized {self.name} with Microsoft Agent Framework and Google Gemini")
            
        except Exception as e:
            logger.error(f"Failed to initialize GeminiAgent: {str(e)}")
            raise
    
    async def run(self, message: str, context: Optional[dict] = None) -> str:
        """
        Execute the agent with a message using Microsoft Agent Framework.
        
        Args:
            message: The user message to process
            context: Optional context (not used for gemini agent)
            
        Returns:
            The agent's response as a string
        """
        try:
            if not self.agent:
                self.initialize()
            
            # Use Agent Framework's run method
            response = await self.agent.run(message)
            
            # Extract text content from the response
            if hasattr(response, 'content') and response.content:
                result = response.content
            elif isinstance(response, str):
                result = response
            else:
                result = str(response)
                
            logger.info(f"GeminiAgent completed successfully using Agent Framework")
            return result or "I apologize, but I couldn't generate a response."
                
        except Exception as e:
            logger.error(f"Error running GeminiAgent with Agent Framework: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self._initialized = False
            self.agent = None
        except Exception as e:
            logger.error(f"Error during GeminiAgent cleanup: {str(e)}")
    
    def get_info(self) -> dict:
        """Get agent information."""
        return {
            "name": self.name,
            "type": "agent_framework_google_gemini",
            "initialized": self._initialized,
            "model": settings.GOOGLE_GEMINI_MODEL_ID or "gemini-2.0-flash",
            "framework": "Microsoft Agent Framework"
        }


# Agent factory function
def create_agent(agent_name: str):
    """
    Factory function to create agents by name using Microsoft Agent Framework.
    
    Args:
        agent_name: The name of the agent to create
        
    Returns:
        An instance of the requested agent (GenericAgent, PeopleLookupAgent, or KnowledgeFinderAgent)
        
    Raises:
        ValueError: If the agent name is not recognized
    """
    if agent_name == "generic_agent":
        return GenericAgent()
    elif agent_name == "people_lookup":
        return PeopleLookupAgent()
    elif agent_name == "knowledge_finder":
        return KnowledgeFinderAgent()
    elif agent_name == "bedrock_agent":
        return BedrockAgent()
    elif agent_name == "gemini_agent":
        return GeminiAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_name}")


# Available agents list using Microsoft Agent Framework
AVAILABLE_AGENTS = [
    {
        "name": "generic_agent",
        "type": "generic",
        "description": "A versatile general-purpose assistant using Microsoft Agent Framework with Azure OpenAI",
        "class": GenericAgent,
        "framework": "Microsoft Agent Framework"
    },
    {
        "name": "people_lookup", 
        "type": "people_lookup",
        "description": "Specialized Azure AI Foundry agent with employee knowledge base using Microsoft Agent Framework",
        "class": PeopleLookupAgent,
        "framework": "Microsoft Agent Framework"
    },
    {
        "name": "knowledge_finder",
        "type": "knowledge_finder", 
        "description": "Specialized Azure AI Foundry agent with organizational knowledge base using Microsoft Agent Framework",
        "class": KnowledgeFinderAgent,
        "framework": "Microsoft Agent Framework"
    },
    {
        "name": "bedrock_agent",
        "type": "bedrock",
        "description": "AWS Bedrock agent with Amazon's foundation models using Microsoft Agent Framework",
        "class": BedrockAgent,
        "framework": "Microsoft Agent Framework"
    },
    {
        "name": "gemini_agent", 
        "type": "gemini",
        "description": "Google Gemini agent with Google's AI models using Microsoft Agent Framework",
        "class": GeminiAgent,
        "framework": "Microsoft Agent Framework"
    }
]