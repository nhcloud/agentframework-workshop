"""
Workflow orchestration service for multi-agent coordination.

This service executes multiple agents in parallel and synthesizes their responses.
Simplified to work without external orchestration dependencies.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

from models.chat_models import (
    GroupChatRequest,
    GroupChatResponse,
    GroupChatMessage
)
from .agent_service_new import AgentService
from .session_manager import SessionManager


logger = logging.getLogger(__name__)


class WorkflowOrchestrationService:
    """
    Service for orchestrating multi-agent workflows.
    
    Uses parallel execution with response synthesis:
    - All requested agents execute concurrently
    - Responses are synthesized into a coherent answer
    """
    
    def __init__(
        self, 
        agent_service: AgentService,
        session_manager: SessionManager,
        content_safety_service=None
    ):
        """
        Initialize the workflow orchestration service.
        
        Args:
            agent_service: Service for managing agents
            session_manager: Service for managing conversation sessions
            content_safety_service: Optional content safety service for filtering
        """
        self.agent_service = agent_service
        self.session_manager = session_manager
        
        # Initialize content safety service
        if content_safety_service:
            self.content_safety = content_safety_service
        else:
            from .content_safety_service import ContentSafetyService
            self.content_safety = ContentSafetyService()
        
        logger.info(
            f"WorkflowOrchestrationService initialized with parallel execution "
            f"(Content Safety: {'enabled' if self.content_safety.enabled else 'disabled'})"
        )
    
    async def _execute_agent(
        self,
        agent_name: str,
        message: str,
        conversation_history: Optional[List] = None
    ) -> Dict[str, Any]:
        """Execute a single agent and return its response."""
        try:
            logger.info(f"Executing agent: {agent_name}")
            
            chat_request = {
                "message": message,
                "session_id": str(uuid4())
            }
            
            response = await self.agent_service.chat_with_agent_async(
                agent_name, chat_request, conversation_history
            )
            
            content = response.get("content", "")
            
            # Filter output for safety
            if self.content_safety.enabled:
                safety_result = await self.content_safety.analyze_text_async(content)
                if not self.content_safety.is_safe(safety_result):
                    content = self.content_safety.filter_output(content, safety_result)
            
            return {
                "agent": agent_name,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            }
            
        except Exception as ex:
            logger.error(f"Agent {agent_name} failed: {str(ex)}")
            return {
                "agent": agent_name,
                "content": f"Error: {str(ex)}",
                "timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "error": str(ex)
            }
    
    async def _synthesize_responses(
        self,
        agent_responses: List[Dict[str, Any]],
        original_query: str
    ) -> str:
        """
        Synthesize multiple agent responses into a coherent answer.
        """
        try:
            # Extract successful responses
            successful_responses = [r for r in agent_responses if r.get("success", False)]
            
            if not successful_responses:
                return "No agent responses to synthesize."
            
            # If only one response, return it directly
            if len(successful_responses) == 1:
                return successful_responses[0]["content"]
            
            # Format responses for synthesis
            expert_responses = []
            for resp in successful_responses:
                expert_responses.append(f"**{resp['agent']}**: {resp['content']}")
            
            # Try to use an agent to synthesize
            try:
                synthesis_prompt = f"""Combine these expert responses into ONE coherent, helpful answer.

Original Query: {original_query}

Expert Responses:
{chr(10).join(expert_responses)}

Create a unified response that:
- Combines key insights from all experts
- Removes redundancy
- Directly answers the user's query
- Is concise and well-organized

Synthesized Response:"""

                # Use the first available agent for synthesis
                chat_request = {
                    "message": synthesis_prompt,
                    "session_id": str(uuid4())
                }
                
                # Try azure_openai_agent first, then fall back to others
                for agent_name in ["azure_openai_agent", "openai_agent", "bedrock_agent"]:
                    try:
                        response = await self.agent_service.chat_with_agent_async(
                            agent_name, chat_request, []
                        )
                        return response.get("content", "\n\n".join(expert_responses))
                    except Exception:
                        continue
                
                # Fallback: concatenate responses
                return "\n\n---\n\n".join(expert_responses)
                
            except Exception as e:
                logger.warning(f"Synthesis failed, using concatenation: {str(e)}")
                return "\n\n---\n\n".join(expert_responses)
            
        except Exception as e:
            logger.error(f"Error synthesizing responses: {str(e)}")
            return "\n\n".join([r.get("content", "") for r in agent_responses])
    
    async def execute_workflow(
        self, 
        request: GroupChatRequest
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent workflow using parallel execution.
        
        Args:
            request: Group chat request with message and agent list
            
        Returns:
            Dictionary with workflow results
        """
        try:
            # Check input safety
            if self.content_safety.enabled:
                is_safe, error_message = await self.content_safety.check_input_safety(request.message)
                if not is_safe:
                    logger.warning(f"Unsafe input blocked: {request.message[:100]}...")
                    return {
                        "messages": [],
                        "summary": error_message,
                        "session_id": request.session_id or str(uuid4()),
                        "total_turns": 0,
                        "participating_agents": [],
                        "metadata": {
                            "blocked": True,
                            "reason": "content_safety_violation"
                        }
                    }
            
            # Create or retrieve session
            session_id = request.session_id or await self.session_manager.create_session()
            
            start_time = datetime.utcnow()
            
            logger.info(
                f"Starting parallel workflow for session {session_id} "
                f"with {len(request.agents)} agents"
            )
            
            # Add user message
            user_message = GroupChatMessage(
                content=request.message,
                agent="user",
                timestamp=datetime.utcnow().isoformat(),
                turn=0,
                message_id=str(uuid4())
            )
            await self.session_manager.add_message_to_session(session_id, user_message)
            
            # Execute all agents in parallel
            tasks = [
                self._execute_agent(agent_name, request.message)
                for agent_name in request.agents
            ]
            
            agent_responses = await asyncio.gather(*tasks)
            
            # Filter successful responses
            successful_responses = [r for r in agent_responses if r.get("success", False)]
            failed_agents = [r["agent"] for r in agent_responses if not r.get("success", False)]
            
            if failed_agents:
                logger.warning(f"Failed agents: {failed_agents}")
            
            total_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Build messages list
            messages = [
                {
                    "content": user_message.content,
                    "agent": user_message.agent,
                    "timestamp": user_message.timestamp,
                    "turn": 0,
                    "message_id": user_message.message_id
                }
            ]
            
            turn = 1
            for resp in successful_responses:
                msg = GroupChatMessage(
                    content=resp["content"],
                    agent=resp["agent"],
                    timestamp=resp["timestamp"],
                    turn=turn,
                    message_id=str(uuid4())
                )
                messages.append({
                    "content": msg.content,
                    "agent": msg.agent,
                    "timestamp": msg.timestamp,
                    "turn": turn,
                    "message_id": msg.message_id
                })
                await self.session_manager.add_message_to_session(session_id, msg)
                turn += 1
            
            # Synthesize if multiple responses
            synthesized_content = None
            if len(successful_responses) > 1:
                logger.info(f"Synthesizing {len(successful_responses)} agent responses")
                synthesized_content = await self._synthesize_responses(
                    successful_responses,
                    request.message
                )
                
                synth_msg = GroupChatMessage(
                    content=synthesized_content,
                    agent="workflow_synthesizer",
                    timestamp=datetime.utcnow().isoformat(),
                    turn=turn,
                    message_id=str(uuid4()),
                    metadata={
                        "synthesized": True,
                        "source_agents": [r["agent"] for r in successful_responses]
                    }
                )
                messages.append({
                    "content": synth_msg.content,
                    "agent": synth_msg.agent,
                    "timestamp": synth_msg.timestamp,
                    "turn": turn,
                    "message_id": synth_msg.message_id,
                    "metadata": synth_msg.metadata
                })
                await self.session_manager.add_message_to_session(session_id, synth_msg)
            elif len(successful_responses) == 1:
                synthesized_content = successful_responses[0]["content"]
            else:
                synthesized_content = "No agents were able to respond."
            
            participating_agents = [r["agent"] for r in successful_responses]
            
            response = {
                "messages": messages,
                "session_id": session_id,
                "total_turns": turn,
                "participating_agents": participating_agents,
                "terminated_agents": failed_agents,
                "total_processing_time": total_time,
                "summary": synthesized_content,
                "metadata": {
                    "workflow_type": "parallel_execution",
                    "max_turns": request.max_turns,
                    "format": request.format,
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "requested_agents": request.agents,
                    "successful_agents": participating_agents,
                    "failed_agents": failed_agents,
                    "synthesized": len(successful_responses) > 1,
                    "agent_count": len(participating_agents),
                    "is_group_chat": len(request.agents) > 1,
                    "contributing_agents": participating_agents
                }
            }
            
            logger.info(
                f"Parallel workflow completed: {len(participating_agents)}/{len(request.agents)} agents succeeded, "
                f"{len(messages)-1} total messages, completed in {total_time:.2f}s"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            raise
