"""
Agents package - Refactored to match .NET architecture exactly.

This module exports all agent classes following the .NET BaseAgent pattern
matching the exact agents from the .NET implementation.

Agent Types (matching .NET):
- BaseAgent: Abstract base class (matches .NET BaseAgent)
- IAgent: Interface (matches .NET IAgent)
- AzureOpenAIAgent: Azure OpenAI integration (matches .NET AzureOpenAIAgent)
- AzureAIFoundryAgent: Azure AI Foundry (matches .NET AzureAIFoundryAgent)
- MicrosoftFoundryPeopleAgent: People lookup agent
- BedrockHRAgent: AWS Bedrock HR agent (matches .NET BedrockHRAgent)
- OpenAIGenericAgent: Direct OpenAI agent (matches .NET OpenAIGenericAgent)
"""

from .base_agent_new import (
    BaseAgent,
    IAgent,
    GroupChatMessage,
    ChatRequest,
    ChatResponse,
    UsageInfo
)
from .azure_openai_agent import AzureOpenAIAgent, AzureOpenAIGenericAgent
from .ms_foundry_agent import AzureAIFoundryAgent, MicrosoftFoundryPeopleAgent
from .bedrock_agent_new import BedrockHRAgent
from .openai_agent import OpenAIGenericAgent
from .user_info_memory import UserInfoMemory

__all__ = [
    # Base classes
    'IAgent',
    'BaseAgent',
    'GroupChatMessage',
    'ChatRequest',
    'ChatResponse',
    'UsageInfo',
    
    # Azure OpenAI agents
    'AzureOpenAIAgent',
    'AzureOpenAIGenericAgent',
    
    # Azure AI Foundry agents
    'AzureAIFoundryAgent',
    'MicrosoftFoundryPeopleAgent',
    
    # AWS Bedrock agents
    'BedrockHRAgent',
    
    # Direct OpenAI agents
    'OpenAIGenericAgent',
    
    # Memory
    'UserInfoMemory',
]
