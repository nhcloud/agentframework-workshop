"""
Agents router for handling agent-related API endpoints.

This router provides agent management functionality, similar to the .NET AgentsController.
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from models.chat_models import AgentInfo, ErrorResponse


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=Dict[str, Any])
async def get_agents(app_request: Request) -> Dict[str, Any]:
    """
    Get all available agents.
    Returns agents with provider information and counts.
    """
    try:
        agent_service = app_request.app.state.agent_service
        agents = await agent_service.get_available_agents_async()
        
        agent_list = []
        for agent in agents:
            agent_info = {
                "name": agent.name,
                "type": _get_agent_type(agent.name),
                "available": True,
                "capabilities": _get_agent_capabilities(agent.name),
                "provider": _get_provider_type(agent.type, agent.name)
            }
            agent_list.append(agent_info)
        
        logger.info(f"Retrieved {len(agent_list)} available agents")
        
        return {
            "agents": agent_list,
            "total": len(agent_list),
            "available": len([a for a in agent_list if a["available"]])
        }
        
    except Exception as ex:
        logger.error(f"Error getting agents: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")


def _get_agent_type(agent_name: str) -> str:
    """Get agent type based on name."""
    type_map = {
        "generic_agent": "generic",
        "people_lookup": "people_lookup", 
        "knowledge_finder": "knowledge_finder",
        "bedrock_agent": "bedrock",
        "gemini_agent": "gemini"
    }
    return type_map.get(agent_name, agent_name.replace("foundry_", ""))


def _get_provider_type(agent_type: str, agent_name: str) -> str:
    """Get provider type for agent."""
    if agent_name.startswith("foundry_") or agent_type == "Azure AI Foundry":
        return "azure_foundry"
    elif agent_name == "bedrock_agent" or agent_type == "bedrock":
        return "aws_bedrock"
    elif agent_name == "gemini_agent" or agent_type == "gemini":
        return "google_gemini"
    elif agent_type in ["people_lookup", "knowledge_finder"]:
        return "azure_ai_foundry"
    return "azure_openai"


def _get_agent_capabilities(agent_name: str) -> List[str]:
    """Get capabilities list for agent."""
    capabilities_map = {
        "generic_agent": [
            "General question answering",
            "Analysis and problem-solving",
            "Writing assistance",
            "Research support"
        ],
        "people_lookup": [
            "Employee directory search",
            "Contact information lookup",
            "Organizational hierarchy",
            "Team identification"
        ],
        "knowledge_finder": [
            "Document search",
            "Knowledge base queries",
            "Policy lookup",
            "Information synthesis"
        ],
        "bedrock_agent": [
            "AWS Bedrock powered responses",
            "Amazon foundation models",
            "General question answering",
            "Advanced AI capabilities"
        ],
        "gemini_agent": [
            "Google Gemini powered responses",
            "Advanced language understanding",
            "Creative content generation",
            "Multi-modal capabilities"
        ]
    }
    return capabilities_map.get(agent_name, ["General assistance"])


@router.get("/{agent_name}", response_model=Dict[str, Any])
async def get_agent_info(agent_name: str, app_request: Request) -> Dict[str, Any]:
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_name: The name of the agent to retrieve information for
        
    Returns:
        Detailed agent information including status and capabilities
    """
    try:
        agent_service = app_request.app.state.agent_service
        
        # Try to get the actual agent instance
        try:
            agent = await agent_service.get_agent_async(agent_name)
            if agent:
                agent_info = {
                    "name": agent.name,
                    "description": agent.description,
                    "type": "Agent",
                    "status": "available",
                    "instructions": agent.instructions[:200] + "..." if len(agent.instructions) > 200 else agent.instructions,
                    "metadata": {}
                }
                return agent_info
        except Exception as ex:
            logger.warning(f"Could not get agent details for {agent_name}: {str(ex)}")
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error getting agent info for {agent_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve information for agent '{agent_name}'")


@router.get("/{agent_name}/auth", response_model=Dict[str, Any])
async def get_agent_auth_status(agent_name: str, app_request: Request) -> Dict[str, Any]:
    """Expose authentication path for an agent (MI vs DAC)."""
    try:
        agent_service = app_request.app.state.agent_service
        agent = await agent_service.get_agent_async(agent_name)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        if hasattr(agent, "get_auth_status"):
            return agent.get_auth_status()

        return {
            "agent": agent_name,
            "credential_source": "unknown",
            "initialized": getattr(agent, "_agents_client", None) is not None
        }

    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error getting auth status for agent {agent_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to get auth status for agent '{agent_name}'")


@router.post("/{agent_name}/initialize")
async def initialize_agent(agent_name: str, app_request: Request) -> Dict[str, Any]:
    """
    Initialize a specific agent.
    
    This endpoint can be used to pre-initialize agents for better performance
    on first use.
    
    Args:
        agent_name: The name of the agent to initialize
        
    Returns:
        Initialization result
    """
    try:
        agent_service = app_request.app.state.agent_service
        
        # Get and initialize the agent
        agent = await agent_service.get_agent_async(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        return {
            "agent": agent_name,
            "status": "initialized",
            "message": f"Agent '{agent_name}' has been successfully initialized",
            "details": {
                "name": agent.name,
                "description": agent.description
            }
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error initializing agent {agent_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize agent '{agent_name}': {str(ex)}")


@router.get("/{agent_name}/status")
async def get_agent_status(agent_name: str, app_request: Request) -> Dict[str, Any]:
    """
    Get the current status of a specific agent.
    
    Args:
        agent_name: The name of the agent to check
        
    Returns:
        Agent status information
    """
    try:
        agent_service = app_request.app.state.agent_service
        
        # Try to get the agent
        agent = await agent_service.get_agent_async(agent_name)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        return {
            "agent": agent_name,
            "status": "available",
            "name": agent.name,
            "description": agent.description
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error getting agent status for {agent_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status for agent '{agent_name}'")


@router.post("/{agent_name}/chat")
async def chat_with_agent(agent_name: str, request: Dict[str, Any], app_request: Request) -> Dict[str, Any]:
    """
    Chat directly with a specific agent.
    
    This endpoint allows direct communication with a single agent,
    bypassing the general chat endpoint's agent selection logic.
    
    Args:
        agent_name: The name of the agent to chat with
        request: Chat request containing the message and optional parameters
        
    Returns:
        Agent response
    """
    try:
        # Validate request
        if "message" not in request or not request["message"].strip():
            raise HTTPException(status_code=400, detail="Message is required")
        
        agent_service = app_request.app.state.agent_service
        session_manager = app_request.app.state.session_manager
        
        # Get conversation history if session_id provided
        conversation_history = []
        session_id = request.get("session_id")
        if session_id:
            try:
                conversation_history = await session_manager.get_session_history(session_id)
            except Exception as ex:
                logger.warning(f"Could not retrieve session history: {str(ex)}")
        else:
            session_id = await session_manager.create_session()
        
        # Execute chat with agent (async)
        chat_request = {
            "message": request["message"],
            "session_id": session_id
        }
        response = await agent_service.chat_with_agent_async(
            agent_name, chat_request, conversation_history
        )
        
        # Add session ID to response
        response["session_id"] = session_id
        
        return response
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error chatting with agent {agent_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to chat with agent '{agent_name}': {str(ex)}")


@router.get("/{agent_name}/capabilities")
async def get_agent_capabilities(agent_name: str, app_request: Request) -> Dict[str, Any]:
    """
    Get the capabilities and features of a specific agent.
    
    Args:
        agent_name: The name of the agent
        
    Returns:
        Agent capabilities information
    """
    try:
        agent_service = app_request.app.state.agent_service
        
        # Check if agent exists
        agent = await agent_service.get_agent_async(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        # Define capabilities based on agent type
        capabilities_map = {
            "generic_agent": {
                "primary_functions": [
                    "General question answering",
                    "Analysis and problem-solving", 
                    "Writing and communication assistance",
                    "Research and information gathering"
                ],
                "specializations": ["General purpose", "Versatile assistance"],
                "input_formats": ["Text"],
                "output_formats": ["Text", "Structured responses"],
                "limitations": ["No access to external systems", "No real-time data"]
            },
            "people_lookup": {
                "primary_functions": [
                    "Employee directory search",
                    "Contact information lookup",
                    "Organizational hierarchy queries",
                    "Team member identification"
                ],
                "specializations": ["People search", "Organizational data"],
                "input_formats": ["Text queries", "Names", "Departments"],
                "output_formats": ["Contact details", "Organizational charts", "Employee profiles"],
                "limitations": ["Privacy policy constraints", "Data availability dependent"]
            },
            "knowledge_finder": {
                "primary_functions": [
                    "Document search",
                    "Knowledge base queries",
                    "Policy and procedure lookup",
                    "Information synthesis"
                ],
                "specializations": ["Document retrieval", "Knowledge management"],
                "input_formats": ["Text queries", "Keywords", "Document references"],
                "output_formats": ["Document summaries", "Relevant excerpts", "Source references"],
                "limitations": ["Available document scope", "Index currency"]
            }
        }
        
        base_capabilities = {
            "agent": agent_name,
            "type": "Agent",
            "description": agent.description if agent else "",
            "status": "available",
            "capabilities": capabilities_map.get(agent_name, {
                "primary_functions": ["General assistance"],
                "specializations": ["As configured"],
                "input_formats": ["Text"], 
                "output_formats": ["Text"],
                "limitations": ["Configuration dependent"]
            }),
            "integration_features": [
                "Microsoft Agent Framework integration",
                "Azure OpenAI powered",
                "Session management",
                "Multi-turn conversations"
            ]
        }
        
        return base_capabilities
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error getting agent capabilities for {agent_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities for agent '{agent_name}'")