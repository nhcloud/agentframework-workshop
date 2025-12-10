"""
Response formatting service for processing and formatting agent responses.

This service handles response formatting and synthesis,
similar to the .NET ResponseFormatterService.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .agent_service_new import AgentService
from models.chat_models import GroupChatResponse, GroupChatMessage


logger = logging.getLogger(__name__)


class ResponseFormatterService:
    """
    Service for formatting and synthesizing agent responses.
    
    This service provides functionality to:
    - Format individual agent responses
    - Synthesize multi-agent responses into user-friendly formats
    - Handle different response format preferences
    """
    
    def __init__(self, agent_service: AgentService):
        """
        Initialize the response formatter service.
        
        Args:
            agent_service: The agent service for response synthesis
        """
        self.agent_service = agent_service
        logger.info("ResponseFormatterService initialized")
    
    async def format_single_response(self, response: Dict[str, Any], format_type: str = "user_friendly") -> Dict[str, Any]:
        """
        Format a single agent response.
        
        Args:
            response: The agent response to format
            format_type: The desired format type
            
        Returns:
            Formatted response
        """
        try:
            if format_type == "detailed":
                # Detailed format includes all response fields plus metadata
                return {
                    "content": response.get("content", ""),
                    "agent": response.get("agent", "unknown"),
                    "session_id": response.get("session_id"),
                    "timestamp": response.get("timestamp"),
                    "processing_time_ms": response.get("processing_time_ms", 0),
                    "usage": response.get("usage", {}),
                    "format": "detailed",
                    "formatted_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "response_type": "single_agent",
                        "agent_count": 1
                    }
                }
            else:
                # User-friendly format (default)
                return {
                    "content": response.get("content", ""),
                    "agent": response.get("agent", "unknown"),
                    "session_id": response.get("session_id"),
                    "timestamp": response.get("timestamp"),
                    "format": "user_friendly",
                    "formatted_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to format single response: {str(e)}")
            return response
    
    async def format_group_chat_response(self, group_response, format_type: str = "user_friendly") -> Dict[str, Any]:
        """
        Format a group chat response based on the requested format.
        
        Args:
            group_response: The group chat response (GroupChatResponse object or dict)
            format_type: The desired format type ('user_friendly' or 'detailed')
            
        Returns:
            Formatted response
        """
        try:
            # Handle both dict and GroupChatResponse object
            if isinstance(group_response, dict):
                return await self._format_dict_response(group_response, format_type)
            
            if format_type == "detailed":
                return await self._format_detailed_response(group_response)
            else:
                return await self._format_user_friendly_response(group_response)
                
        except Exception as e:
            logger.error(f"Failed to format group chat response: {str(e)}")
            return self._create_error_response(str(e))
    
    async def _format_dict_response(self, group_response: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """
        Format a dict-based group response.
        
        Args:
            group_response: Dict containing response data
            format_type: The desired format type
            
        Returns:
            Formatted response
        """
        try:
            messages = group_response.get("messages", [])
            metadata = group_response.get("metadata", {})
            session_id = group_response.get("session_id", "")
            
            # Filter agent messages (exclude user)
            agent_messages = [m for m in messages if m.get("agent") != "user"]
            
            if format_type == "detailed":
                return {
                    "format": "detailed",
                    "conversation_id": session_id,
                    "total_turns": group_response.get("total_turns", len(agent_messages)),
                    "active_participants": metadata.get("participating_agents", []),
                    "responses": [
                        {
                            "agent": m.get("agent"),
                            "content": m.get("content"),
                            "metadata": {"turn": m.get("turn", i+1)}
                        }
                        for i, m in enumerate(agent_messages)
                    ],
                    "summary": group_response.get("summary"),
                    "metadata": {
                        "group_chat_type": metadata.get("workflow_type", "parallel"),
                        "agent_count": metadata.get("agent_count", len(agent_messages)),
                        "response_type": "detailed"
                    },
                    "formatted_at": datetime.utcnow().isoformat()
                }
            else:
                # User-friendly format
                content = group_response.get("summary") or ""
                if not content and agent_messages:
                    # Use the last agent message if no summary
                    content = agent_messages[-1].get("content", "")
                
                return {
                    "content": content,
                    "agent": metadata.get("contributing_agents", ["assistant"])[0] if metadata.get("contributing_agents") else "assistant",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "format": "user_friendly",
                    "formatted_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "agent_count": metadata.get("agent_count", 1),
                        "total_turns": group_response.get("total_turns", 1),
                        "is_group_chat": metadata.get("is_group_chat", False),
                        "contributing_agents": metadata.get("contributing_agents", [])
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to format dict response: {str(e)}")
            return self._create_error_response(str(e))
    
    async def _format_detailed_response(self, group_response: GroupChatResponse) -> Dict[str, Any]:
        """
        Format response with detailed conversation information.
        
        Args:
            group_response: The group chat response
            
        Returns:
            Detailed formatted response
        """
        try:
            # Filter out user messages for agent responses
            agent_messages = [msg for msg in group_response.messages if msg.agent != "user"]
            
            formatted_messages = []
            for message in agent_messages:
                formatted_message = {
                    "content": message.content,
                    "agent": message.agent,
                    "turn": message.turn,
                    "timestamp": message.timestamp.isoformat() if isinstance(message.timestamp, datetime) else message.timestamp,
                    "message_id": message.message_id,
                    "metadata": message.metadata or {}
                }
                formatted_messages.append(formatted_message)
            
            return {
                "format": "detailed",
                "session_id": group_response.session_id,
                "messages": formatted_messages,
                "summary": {
                    "total_turns": group_response.total_turns,
                    "participating_agents": group_response.participating_agents,
                    "terminated_agents": group_response.terminated_agents,
                    "total_processing_time": group_response.total_processing_time,
                    "message_count": len(agent_messages)
                },
                "metadata": group_response.metadata,
                "formatted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to format detailed response: {str(e)}")
            return self._create_error_response(str(e))
    
    async def _format_user_friendly_response(self, group_response: GroupChatResponse) -> Dict[str, Any]:
        """
        Format response in a user-friendly synthesized format.
        
        Args:
            group_response: The group chat response
            
        Returns:
            User-friendly formatted response
        """
        try:
            # Filter out user messages
            agent_messages = [msg for msg in group_response.messages if msg.agent != "user"]
            
            if not agent_messages:
                return {
                    "content": "No agent responses received.",
                    "format": "user_friendly",
                    "session_id": group_response.session_id,
                    "agents_consulted": group_response.participating_agents,
                    "formatted_at": datetime.utcnow().isoformat()
                }
            
            # If only one agent responded, return its response directly
            if len(set(msg.agent for msg in agent_messages)) == 1:
                latest_message = agent_messages[-1]
                return {
                    "content": latest_message.content,
                    "format": "user_friendly",
                    "session_id": group_response.session_id,
                    "primary_agent": latest_message.agent,
                    "agents_consulted": group_response.participating_agents,
                    "formatted_at": datetime.utcnow().isoformat()
                }
            
            # Synthesize multiple agent responses
            synthesized_content = await self._synthesize_responses(agent_messages)
            
            return {
                "content": synthesized_content,
                "format": "user_friendly",
                "session_id": group_response.session_id,
                "agents_consulted": group_response.participating_agents,
                "response_count": len(agent_messages),
                "processing_time": group_response.total_processing_time,
                "formatted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to format user-friendly response: {str(e)}")
            return self._create_error_response(str(e))
    
    async def _synthesize_responses(self, agent_messages: List[GroupChatMessage]) -> str:
        """
        Synthesize multiple agent responses into a coherent response.
        
        Args:
            agent_messages: List of agent messages to synthesize
            
        Returns:
            Synthesized response content
        """
        try:
            # Group messages by agent
            agent_responses = {}
            for message in agent_messages:
                if message.agent not in agent_responses:
                    agent_responses[message.agent] = []
                agent_responses[message.agent].append(message.content)
            
            # If we have a generic agent, use it to synthesize the responses
            try:
                generic_agent = await self.agent_service.get_agent("generic_agent")
                if generic_agent:
                    # Prepare synthesis prompt
                    synthesis_prompt = self._create_synthesis_prompt(agent_responses)
                    synthesis_response = await generic_agent.run(synthesis_prompt)
                    
                    if hasattr(synthesis_response, 'text') and synthesis_response.text:
                        return synthesis_response.text
            except Exception as e:
                logger.warning(f"Failed to use generic agent for synthesis: {str(e)}")
            
            # Fallback: Simple concatenation with agent attribution
            synthesized_parts = []
            
            for agent_name, responses in agent_responses.items():
                # Get the most recent response from each agent
                latest_response = responses[-1] if responses else ""
                if latest_response:
                    # Clean up the response and add agent attribution
                    clean_response = latest_response.strip()
                    if clean_response:
                        agent_display_name = self._get_agent_display_name(agent_name)
                        synthesized_parts.append(f"**{agent_display_name}:**\n{clean_response}")
            
            if not synthesized_parts:
                return "I apologize, but I wasn't able to generate a proper response from the available agents."
            
            return "\n\n".join(synthesized_parts)
            
        except Exception as e:
            logger.error(f"Failed to synthesize responses: {str(e)}")
            # Return simple concatenation as last resort
            return "\n\n".join([msg.content for msg in agent_messages if msg.content])
    
    def _create_synthesis_prompt(self, agent_responses: Dict[str, List[str]]) -> str:
        """
        Create a prompt for synthesizing agent responses.
        
        Args:
            agent_responses: Dictionary of agent names to their responses
            
        Returns:
            Synthesis prompt
        """
        prompt_parts = [
            "Please synthesize the following responses from multiple specialized agents into a single, coherent, and helpful response for the user:",
            ""
        ]
        
        for agent_name, responses in agent_responses.items():
            agent_display_name = self._get_agent_display_name(agent_name)
            latest_response = responses[-1] if responses else ""
            if latest_response:
                prompt_parts.append(f"**{agent_display_name} Response:**")
                prompt_parts.append(latest_response)
                prompt_parts.append("")
        
        prompt_parts.extend([
            "Please create a unified response that:",
            "1. Combines the key information from all agents",
            "2. Removes any redundancy or conflicting information", 
            "3. Maintains a natural, conversational tone",
            "4. Provides a complete answer to the user's original query",
            "5. Gives proper credit to the specialized knowledge when relevant",
            "",
            "Synthesized Response:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_agent_display_name(self, agent_name: str) -> str:
        """
        Get a user-friendly display name for an agent.
        
        Args:
            agent_name: The internal agent name
            
        Returns:
            User-friendly display name
        """
        display_names = {
            "generic_agent": "General Assistant",
            "people_lookup": "People Finder",
            "knowledge_finder": "Knowledge Search"
        }
        
        return display_names.get(agent_name, agent_name.replace("_", " ").title())
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            error_message: The error message
            
        Returns:
            Error response dictionary
        """
        return {
            "content": f"I apologize, but I encountered an error while processing your request: {error_message}",
            "format": "error",
            "error": error_message,
            "formatted_at": datetime.utcnow().isoformat()
        }