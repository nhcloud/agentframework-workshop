"""
Group chat service for multi-agent orchestration.

This service handles multi-agent conversations using the Microsoft Agent Framework,
similar to the .NET GroupChatService.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from agent_framework import AgentThread, ChatMessage

from .agent_service import AgentService
from .session_manager import SessionManager
from models.chat_models import GroupChatRequest, GroupChatResponse, GroupChatMessage


logger = logging.getLogger(__name__)


class GroupChatService:
    """
    Service for managing multi-agent group conversations.
    
    This service provides functionality to:
    - Orchestrate conversations between multiple agents
    - Manage turn-based agent interactions
    - Handle agent thread creation and management
    - Format and respond with group chat results
    """
    
    def __init__(self, agent_service: AgentService, session_manager: SessionManager):
        """
        Initialize the group chat service.
        
        Args:
            agent_service: The agent service for managing agents
            session_manager: The session manager for conversation history
        """
        self.agent_service = agent_service
        self.session_manager = session_manager
        logger.info("GroupChatService initialized")
    
    async def start_group_chat(self, request: GroupChatRequest) -> GroupChatResponse:
        """
        Start a group chat with multiple agents.
        
        Args:
            request: The group chat request containing agents and message
            
        Returns:
            The group chat response with all agent interactions
        """
        try:
            session_id = request.session_id or await self.session_manager.create_session()
            messages = []
            terminated_agents = set()
            
            # Add the initial user message
            user_message = GroupChatMessage(
                content=request.message,
                agent="user",
                timestamp=datetime.utcnow().isoformat(),
                turn=0,
                message_id=str(uuid4())
            )
            messages.append(user_message)
            await self.session_manager.add_message_to_session(session_id, user_message)
            
            current_turn = 1
            start_time = datetime.utcnow()
            
            logger.info(f"Starting group chat with {len(request.agents)} agents, max turns: {request.max_turns}")
            
            # Process agents in sequence for each turn
            for turn in range(1, request.max_turns + 1):
                for agent_name in request.agents:
                    # Skip agents that have terminated
                    if agent_name in terminated_agents:
                        logger.info(f"Agent {agent_name} has terminated, skipping")
                        continue
                    
                    agent_start_time = datetime.utcnow()
                    
                    try:
                        # Get the agent
                        agent = await self.agent_service.get_agent(agent_name)
                        if not agent:
                            logger.warning(f"Agent {agent_name} not found, skipping")
                            continue
                        
                        # Build context for the agent
                        agent_context = self._build_agent_context(messages, agent_name, request.message)
                        
                        # Get agent response with timeout
                        try:
                            response_task = agent.run(request.message)
                            response = await asyncio.wait_for(response_task, timeout=60.0)  # 1 minute timeout
                            
                            # Extract response content
                            response_content = response.text if hasattr(response, 'text') else str(response)
                            
                            # Check if agent terminated
                            is_terminated = self._is_agent_terminated(response_content)
                            if is_terminated:
                                terminated_agents.add(agent_name)
                                logger.info(f"Agent {agent_name} terminated from conversation")
                            
                            agent_message = GroupChatMessage(
                                content=response_content,
                                agent=agent_name,
                                timestamp=datetime.utcnow().isoformat(),
                                turn=current_turn,
                                message_id=str(uuid4()),
                                metadata={
                                    "agent_type": getattr(agent, 'agent_type', agent_name),  # Fallback to agent_name if agent_type missing
                                    "processing_time": (datetime.utcnow() - agent_start_time).total_seconds(),
                                    "terminated": is_terminated
                                }
                            )
                            
                            messages.append(agent_message)
                            await self.session_manager.add_message_to_session(session_id, agent_message)
                            
                            logger.debug(f"Agent {agent_name} responded in turn {current_turn}")
                            
                        except asyncio.TimeoutError:
                            logger.error(f"Agent {agent_name} timed out in turn {current_turn}")
                            # Create timeout message
                            timeout_message = GroupChatMessage(
                                content=f"Agent {agent_name} did not respond within the timeout period.",
                                agent=agent_name,
                                timestamp=datetime.utcnow(),
                                turn=current_turn,
                                message_id=str(uuid4()),
                                metadata={
                                    "error": "timeout",
                                    "processing_time": 60.0
                                }
                            )
                            messages.append(timeout_message)
                            terminated_agents.add(agent_name)
                    
                    except Exception as e:
                        logger.error(f"Error with agent {agent_name} in turn {current_turn}: {str(e)}")
                        # Create error message
                        error_message = GroupChatMessage(
                            content=f"Error occurred with agent {agent_name}: {str(e)}",
                            agent=agent_name,
                            timestamp=datetime.utcnow().isoformat(),
                            turn=current_turn,
                            message_id=str(uuid4()),
                            metadata={
                                "error": str(e),
                                "processing_time": (datetime.utcnow() - agent_start_time).total_seconds()
                            }
                        )
                        messages.append(error_message)
                        terminated_agents.add(agent_name)
                
                current_turn += 1
                
                # Check if all agents have terminated
                if len(terminated_agents) >= len(request.agents):
                    logger.info("All agents have terminated, ending group chat")
                    break
            
            total_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create group chat response
            response = GroupChatResponse(
                messages=messages,
                session_id=session_id,
                total_turns=current_turn - 1,
                participating_agents=request.agents,
                terminated_agents=list(terminated_agents),
                total_processing_time=total_time,
                metadata={
                    "max_turns": request.max_turns,
                    "format": request.format,
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Completed group chat with {len(messages)} messages in {total_time:.2f} seconds")
            return response
            
        except Exception as e:
            logger.error(f"Failed to start group chat: {str(e)}")
            raise
    
    def _build_agent_context(self, messages: List[GroupChatMessage], agent_name: str, original_message: str) -> str:
        """
        Build context for an agent based on conversation history.
        
        Args:
            messages: List of messages in the conversation
            agent_name: Name of the current agent
            original_message: The original user message
            
        Returns:
            Context string for the agent
        """
        try:
            context_parts = [f"Original user message: {original_message}"]
            
            # Add recent conversation history (last 5 messages)
            recent_messages = messages[-5:] if len(messages) > 5 else messages
            
            if len(recent_messages) > 1:  # More than just the user message
                context_parts.append("Recent conversation:")
                for message in recent_messages[1:]:  # Skip the first user message
                    if message.agent != agent_name:  # Don't include own messages
                        context_parts.append(f"- {message.agent}: {message.content[:200]}...")
            
            context = "\n".join(context_parts)
            return context
            
        except Exception as e:
            logger.error(f"Failed to build agent context: {str(e)}")
            return original_message
    
    def _is_agent_terminated(self, response_content: str) -> bool:
        """
        Check if an agent has indicated termination.
        
        Args:
            response_content: The agent's response content
            
        Returns:
            True if the agent has terminated, False otherwise
        """
        try:
            # Look for termination indicators in the response
            termination_indicators = [
                "TERMINATE",
                "CONVERSATION_COMPLETE",
                "END_CONVERSATION",
                "I'm done",
                "conversation is complete",
                "no further assistance needed"
            ]
            
            response_lower = response_content.lower()
            return any(indicator.lower() in response_lower for indicator in termination_indicators)
            
        except Exception as e:
            logger.error(f"Error checking agent termination: {str(e)}")
            return False
    
    async def get_group_chat_templates(self) -> List[Dict[str, Any]]:
        """
        Get available group chat templates.
        
        Returns:
            List of available templates
        """
        try:
            # Define comprehensive templates matching .NET version
            templates = [
                {
                    "name": "general_inquiry",
                    "display_name": "General Inquiry",
                    "description": "General multi-agent inquiry with people lookup and knowledge search",
                    "agents": ["people_lookup", "knowledge_finder"],
                    "max_turns": 3,
                    "format": "user_friendly",
                    "use_cases": ["Employee questions", "Information lookup", "General assistance"],
                    "config": {
                        "response_synthesis": True,
                        "turn_management": "sequential",
                        "timeout_per_agent": 60
                    }
                },
                {
                    "name": "comprehensive_research",
                    "display_name": "Comprehensive Research",
                    "description": "Comprehensive research using all available agents",
                    "agents": ["generic_agent", "people_lookup", "knowledge_finder"],
                    "max_turns": 2,
                    "format": "detailed",
                    "use_cases": ["Complex research", "Multi-perspective analysis", "Detailed investigations"],
                    "config": {
                        "response_synthesis": False,
                        "turn_management": "sequential",
                        "timeout_per_agent": 90
                    }
                },
                {
                    "name": "people_focused",
                    "display_name": "People-Focused Inquiry",
                    "description": "People-focused inquiry with general assistance",
                    "agents": ["people_lookup", "generic_agent"],
                    "max_turns": 2,
                    "format": "user_friendly",
                    "use_cases": ["HR inquiries", "Team information", "Contact lookup"],
                    "config": {
                        "response_synthesis": True,
                        "turn_management": "sequential",
                        "timeout_per_agent": 45
                    }
                },
                {
                    "name": "knowledge_deep_dive",
                    "display_name": "Knowledge Deep Dive",
                    "description": "Deep knowledge search with expert analysis",
                    "agents": ["knowledge_finder", "generic_agent"],
                    "max_turns": 3,
                    "format": "user_friendly",
                    "use_cases": ["Policy questions", "Procedure lookup", "Documentation search"],
                    "config": {
                        "response_synthesis": True,
                        "turn_management": "sequential",  
                        "timeout_per_agent": 75
                    }
                }
            ]
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get group chat templates: {str(e)}")
            return []
    
    async def create_from_template(self, template_name: str, message: str, session_id: Optional[str] = None) -> GroupChatResponse:
        """
        Create a group chat from a template.
        
        Args:
            template_name: Name of the template to use
            message: The user message
            session_id: Optional session ID
            
        Returns:
            The group chat response
        """
        try:
            templates = await self.get_group_chat_templates()
            template = next((t for t in templates if t["name"] == template_name), None)
            
            if not template:
                raise ValueError(f"Template {template_name} not found")
            
            request = GroupChatRequest(
                message=message,
                agents=template["agents"],
                session_id=session_id,
                max_turns=template["max_turns"],
                format=template["format"]
            )
            
            return await self.start_group_chat(request)
            
        except Exception as e:
            logger.error(f"Failed to create group chat from template {template_name}: {str(e)}")
            raise