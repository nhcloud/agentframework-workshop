"""
Chat models for the Agent Framework application.

This module contains Pydantic models that represent the data structures
used throughout the application, similar to the .NET ChatModels.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="The user message")
    session_id: Optional[str] = Field(default=None, description="Optional session ID for conversation continuity")
    agents: Optional[List[str]] = Field(default=None, description="List of agent names to use")
    max_turns: Optional[int] = Field(default=3, description="Maximum number of turns for group chat")
    format: Optional[str] = Field(default="user_friendly", description="Response format preference")
    enable_memory: Optional[bool] = Field(default=None, description="Enable long-running memory for personalized responses")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    content: str = Field(..., description="The response content")
    agent: Optional[str] = Field(default=None, description="The responding agent name")
    session_id: str = Field(..., description="The session ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional response metadata")
    format: str = Field(default="user_friendly", description="The response format")


class GroupChatMessage(BaseModel):
    """Model for individual messages in a group chat."""
    content: str = Field(..., description="The message content")
    agent: str = Field(..., description="The agent that sent the message")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Message timestamp")
    turn: int = Field(..., description="The turn number in the conversation")
    message_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique message identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional message metadata")


class GroupChatRequest(BaseModel):
    """Request model for group chat."""
    message: str = Field(..., description="The user message")
    agents: List[str] = Field(..., description="List of agent names to participate")
    session_id: Optional[str] = Field(default=None, description="Optional session ID")
    max_turns: int = Field(default=3, description="Maximum number of turns per agent")
    format: str = Field(default="user_friendly", description="Response format preference")


class GroupChatResponse(BaseModel):
    """Response model for group chat."""
    messages: List[GroupChatMessage] = Field(..., description="All messages in the group chat")
    session_id: str = Field(..., description="The session ID")
    total_turns: int = Field(..., description="Total number of turns executed")
    participating_agents: List[str] = Field(..., description="List of participating agent names")
    terminated_agents: List[str] = Field(default_factory=list, description="List of agents that terminated early")
    total_processing_time: float = Field(..., description="Total processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional response metadata")


class AgentInfo(BaseModel):
    """Model for agent information."""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    type: str = Field(..., description="Agent type (generic, specialized, etc.)")
    enabled: bool = Field(default=True, description="Whether the agent is enabled")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional agent metadata")


class AgentResponse(BaseModel):
    """Model for individual agent responses."""
    content: str = Field(..., description="Response content")
    agent: str = Field(..., description="Agent name")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional response metadata")


class SessionInfo(BaseModel):
    """Model for session information."""
    session_id: str = Field(..., description="Session identifier")
    created_at: str = Field(..., description="Session creation timestamp")
    last_accessed: str = Field(..., description="Last access timestamp")
    message_count: int = Field(..., description="Number of messages in the session")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional session metadata")


class TemplateRequest(BaseModel):
    """Request model for template-based chat."""
    template_name: str = Field(..., description="Name of the template to use")
    message: str = Field(..., description="The user message")
    session_id: Optional[str] = Field(default=None, description="Optional session ID")


class CreateFromTemplateRequest(BaseModel):
    """Request model for creating chat from template."""
    template_name: str = Field(..., description="Name of the template to use")
    session_id: Optional[str] = Field(default=None, description="Optional session ID")


class ErrorResponse(BaseModel):
    """Model for error responses."""
    detail: str = Field(..., description="Error detail message")
    error_type: Optional[str] = Field(default=None, description="Type of error")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier for tracking")


class HealthResponse(BaseModel):
    """Model for health check responses."""
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Health check timestamp")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional health details")