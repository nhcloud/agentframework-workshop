"""
Chat router for handling chat-related API endpoints.

This router provides the main chat functionality, similar to the .NET ChatController.
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from models.chat_models import (
    ChatRequest, 
    ChatResponse, 
    GroupChatRequest,
    GroupChatResponse,
    TemplateRequest,
    CreateFromTemplateRequest,
    SessionInfo,
    ErrorResponse
)
from services.response_formatter_service import ResponseFormatterService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["chat"])


@router.post("/chat", response_model=Dict[str, Any])
async def chat(request: ChatRequest, app_request: Request) -> Dict[str, Any]:
    """
    Process a chat message - automatically handles both single and multiple agents.
    
    This endpoint automatically uses group chat when multiple agents are selected,
    similar to the .NET ChatController.
    """
    try:
        if not request.message or request.message.strip() == "":
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Get services from app state
        agent_service = app_request.app.state.agent_service
        session_manager = app_request.app.state.session_manager
        workflow_service = app_request.app.state.workflow_service
        
        # Initialize response formatter
        response_formatter = ResponseFormatterService(agent_service)
        
        # Generate session ID if not provided
        session_id = request.session_id or await session_manager.create_session()
        
        # Retrieve conversation history for the session
        conversation_history = []
        if request.session_id:
            try:
                conversation_history = await session_manager.get_session_history(request.session_id)
                logger.info(f"Retrieved {len(conversation_history)} messages from session {request.session_id}")
            except Exception as ex:
                logger.warning(f"Could not retrieve session history for {request.session_id}, starting fresh: {str(ex)}")
        
        # Auto-select agents if none specified
        if not request.agents or len(request.agents) == 0:
            logger.info("No agents specified, auto-selecting based on message content")
            
            available_agents = agent_service.get_available_agents()
            if available_agents:
                request.agents = [available_agents[0].name]
                logger.info(f"Auto-selected agent: {request.agents[0]}")
            else:
                raise HTTPException(status_code=503, detail="No agents available to process the request")
        
        # Check if multiple agents were specified
        if len(request.agents) > 1:
            # Route to workflow-based parallel execution for multiple agents
            max_turns = request.max_turns or (2 if len(request.agents) > 3 else 3)
            
            group_request = GroupChatRequest(
                message=request.message,
                agents=request.agents,
                session_id=session_id,
                max_turns=max_turns,
                format=request.format or "user_friendly"
            )
            
            # Use workflow service for parallel execution
            group_response = await workflow_service.execute_workflow(group_request)
            
            # Check requested format
            requested_format = (request.format or "user_friendly").lower()
            
            if requested_format == "detailed":
                # Return detailed format with all agent responses
                formatted_response = await response_formatter.format_group_chat_response(
                    group_response, "detailed"
                )
                return formatted_response
            else:
                # Synthesize into user-friendly response
                formatted_response = await response_formatter.format_group_chat_response(
                    group_response, "user_friendly"
                )
                return formatted_response
        
        else:
            # Single agent flow
            agent_name = request.agents[0]
            
            try:
                # Execute single agent chat using Agent Framework
                agent_response = await agent_service.chat_with_agent(
                    agent_name, request.message, conversation_history
                )
                
                # Add user message to session
                from models.chat_models import GroupChatMessage
                from datetime import datetime
                from uuid import uuid4
                
                user_message = GroupChatMessage(
                    content=request.message,
                    agent="user",
                    timestamp=datetime.utcnow().isoformat(),
                    turn=0,
                    message_id=str(uuid4())
                )
                await session_manager.add_message_to_session(session_id, user_message)
                
                # Add agent response to session
                agent_message = GroupChatMessage(
                    content=agent_response["content"],
                    agent=agent_name,
                    timestamp=datetime.utcnow().isoformat(),
                    turn=1,
                    message_id=str(uuid4()),
                    metadata=agent_response.get("metadata", {})
                )
                await session_manager.add_message_to_session(session_id, agent_message)
                
                # Format single response
                formatted_response = await response_formatter.format_single_response(
                    {
                        **agent_response,
                        "session_id": session_id
                    },
                    request.format or "user_friendly"
                )
                
                return formatted_response
                
            except Exception as ex:
                logger.error(f"Error executing single agent chat: {str(ex)}")
                raise HTTPException(status_code=500, detail=f"Error processing request with agent {agent_name}: {str(ex)}")
    
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Unexpected error in chat endpoint: {str(ex)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/templates", response_model=Dict[str, Any])
async def get_templates(app_request: Request) -> Dict[str, Any]:
    """Get available chat templates (supports both single and multi-agent configurations)."""
    try:
        group_chat_service = app_request.app.state.group_chat_service
        templates = await group_chat_service.get_group_chat_templates()
        return {"templates": templates}
    except Exception as ex:
        logger.error(f"Error getting templates: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")


@router.get("/templates/{template_name}", response_model=Dict[str, Any])
async def get_template_details(template_name: str, app_request: Request) -> Dict[str, Any]:
    """Get detailed information about a specific template."""
    try:
        group_chat_service = app_request.app.state.group_chat_service
        templates = await group_chat_service.get_group_chat_templates()
        
        template = next((t for t in templates if t["name"] == template_name), None)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        return template
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error getting template {template_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve template details")


@router.post("/from-template", response_model=Dict[str, Any])
async def create_chat_from_template(request: CreateFromTemplateRequest, app_request: Request) -> Dict[str, Any]:
    """Create chat session from template (supports both single and multi-agent)."""
    try:
        if not request.template_name or request.template_name.strip() == "":
            raise HTTPException(status_code=400, detail="Template name is required")
        
        group_chat_service = app_request.app.state.group_chat_service
        session_manager = app_request.app.state.session_manager
        
        # Get template details
        templates = await group_chat_service.get_group_chat_templates()
        template = next((t for t in templates if t["name"] == request.template_name), None)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{request.template_name}' not found")
        
        # Create new session if not provided
        session_id = request.session_id or await session_manager.create_session()
        
        return {
            "session_id": session_id,
            "template_name": request.template_name,
            "name": template.get("display_name", request.template_name),
            "description": template.get("description", ""),
            "participants": template.get("agents", []),
            "status": "created",
            "config": template.get("config", {})
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error creating chat from template {request.template_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to create chat from template")


@router.post("/chat-from-template", response_model=Dict[str, Any])
async def chat_from_template(request: TemplateRequest, app_request: Request) -> Dict[str, Any]:
    """Execute a chat using a predefined template."""
    try:
        if not request.message or request.message.strip() == "":
            raise HTTPException(status_code=400, detail="Message is required")
        
        if not request.template_name or request.template_name.strip() == "":
            raise HTTPException(status_code=400, detail="Template name is required")
        
        group_chat_service = app_request.app.state.group_chat_service
        agent_service = app_request.app.state.agent_service
        
        # Create chat from template
        group_response = await group_chat_service.create_from_template(
            request.template_name, request.message, request.session_id
        )
        
        # Format response
        response_formatter = ResponseFormatterService(agent_service)
        formatted_response = await response_formatter.format_group_chat_response(
            group_response, "user_friendly"
        )
        
        return formatted_response
        
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:
        logger.error(f"Error creating chat from template: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to create chat from template")


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(app_request: Request) -> List[SessionInfo]:
    """List all available chat sessions."""
    try:
        session_manager = app_request.app.state.session_manager
        sessions_data = await session_manager.list_sessions()
        
        sessions = []
        for session_data in sessions_data:
            session_info = SessionInfo(
                session_id=session_data["session_id"],
                created_at=session_data.get("created_at", ""),
                last_accessed=session_data.get("last_accessed", ""),  
                message_count=session_data.get("message_count", 0),
                metadata=session_data.get("metadata")
            )
            sessions.append(session_info)
        
        return sessions
        
    except Exception as ex:
        logger.error(f"Error listing sessions: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/sessions/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_history(session_id: str, app_request: Request) -> List[Dict[str, Any]]:
    """Get conversation history for a specific session."""
    try:
        session_manager = app_request.app.state.session_manager
        history = await session_manager.get_session_history(session_id)
        
        # Convert to dict format for JSON response
        formatted_history = []
        for message in history:
            message_dict = {
                "content": message.content,
                "agent": message.agent,
                "timestamp": message.timestamp.isoformat() if hasattr(message.timestamp, 'isoformat') else str(message.timestamp),
                "turn": message.turn,
                "message_id": message.message_id,
                "metadata": message.metadata or {}
            }
            formatted_history.append(message_dict)
        
        return formatted_history
        
    except Exception as ex:
        logger.error(f"Error getting session history: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session history")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, app_request: Request) -> Dict[str, Any]:
    """Delete a specific session and its history."""
    try:
        session_manager = app_request.app.state.session_manager
        success = await session_manager.delete_session(session_id)
        
        if success:
            return {"message": f"Session {session_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found or could not be deleted")
            
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error deleting session: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.post("/sessions/cleanup")
async def cleanup_expired_sessions(app_request: Request, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Cleanup expired sessions in the background."""
    try:
        session_manager = app_request.app.state.session_manager
        
        # Run cleanup in background
        background_tasks.add_task(session_manager.cleanup_expired_sessions)
        
        return {"message": "Session cleanup initiated"}
        
    except Exception as ex:
        logger.error(f"Error initiating session cleanup: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to initiate session cleanup")