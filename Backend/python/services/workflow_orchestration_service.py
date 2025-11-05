"""
Workflow orchestration service using Microsoft Agent Framework.

This service builds and executes workflow graphs for multi-agent coordination,
using GroupChat-based orchestration with LLM-powered agent selection and synthesis.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

from agent_framework import GroupChatBuilder, Workflow, WorkflowOutputEvent
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.exceptions import ServiceResponseException

from models.chat_models import (
    GroupChatRequest,
    GroupChatResponse,
    GroupChatMessage
)
from .agent_service import AgentService
from .session_manager import SessionManager
from core.config import settings


logger = logging.getLogger(__name__)


class WorkflowOrchestrationService:
    """
    Service for orchestrating multi-agent workflows using Microsoft Agent Framework.
    
    This service uses GroupChat-based orchestration with:
    - LLM-powered agent selection: Manager decides which agents should respond
    - Relevance filtering: Only relevant agents execute (no keyword matching)
    - Response synthesis: LLM combines multiple agent responses coherently
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
        
        # Initialize Azure OpenAI chat client for manager and synthesis
        self.chat_client = AzureOpenAIChatClient(
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION or "2024-02-01"
        )
        
        logger.info(
            f"WorkflowOrchestrationService initialized with GroupChat orchestration "
            f"(Content Safety: {'enabled' if self.content_safety.enabled else 'disabled'})"
        )
    
    async def _synthesize_responses(
        self,
        results: List[Any],
        original_query: str
    ) -> str:
        """
        Synthesize multiple agent responses into a coherent, unified answer.
        
        Uses LLM to combine expert responses intelligently, removing redundancy
        and creating a helpful, focused answer.
        
        Args:
            results: List of agent execution results
            original_query: The original user query
            
        Returns:
            Synthesized response text
        """
        try:
            # Extract agent responses
            expert_responses = []
            for result in results:
                if hasattr(result, 'agent_run_response'):
                    agent_name = getattr(result, 'agent_name', 'Unknown')
                    response_text = result.agent_run_response.text
                    expert_responses.append(f"**{agent_name}**: {response_text}")
            
            if not expert_responses:
                return "No agent responses to synthesize."
            
            # If only one response, return it directly
            if len(expert_responses) == 1:
                return expert_responses[0].split(': ', 1)[1]  # Remove agent name prefix
            
            # Use Generic Agent to synthesize multiple responses
            generic_agent = await self.agent_service.get_agent("generic_agent")
            if not generic_agent:
                # Fallback: concatenate responses
                return "\n\n".join(expert_responses)
            
            synthesis_prompt = f"""You are a helpful assistant that creates coherent, unified answers from multiple expert responses.

Original Query: {original_query}

Expert Responses:
{chr(10).join(expert_responses)}

Your Task:
- Combine these expert responses into ONE coherent, helpful answer
- Remove any redundancy or irrelevant information
- Focus on directly answering the user's query
- Keep the response concise and well-organized
- If experts contradict, acknowledge both perspectives

Synthesized Response:"""

            synthesized = await generic_agent.run(synthesis_prompt)
            
            logger.info("Successfully synthesized agent responses")
            return synthesized
            
        except Exception as e:
            logger.error(f"Error synthesizing responses: {str(e)}")
            # Fallback: return all responses concatenated
            return "\n\n".join(expert_responses) if expert_responses else "Error synthesizing responses."
    
    async def _build_group_chat_workflow(
        self, 
        agent_names: List[str]
    ) -> Workflow:
        """
        Build a GroupChat-based workflow with LLM-powered agent selection and synthesis.
        
        Uses Microsoft Agent Framework's GroupChatBuilder pattern:
        - Prompt-based manager: LLM decides which agents should respond
        - Agent descriptions: Guide manager's selection decisions
        - Custom aggregator: Synthesizes responses into coherent answer
        
        Args:
            agent_names: List of agent names to include in the workflow
            
        Returns:
            Configured Workflow instance
        """
        logger.info(f"Building GroupChat workflow for agents: {agent_names}")
        
        # Get agent instances with their capabilities
        agents_dict = {}
        agent_descriptions = {
            "generic_agent": "General-purpose Azure OpenAI assistant for recommendations and general queries",
            "people_lookup": "Employee directory specialist - contact information, organizational details, employee data",
            "knowledge_finder": "Technical documentation specialist - Configuration PDFs (TorSetup, Storage Encryption, PIM, Mobile App Config)",
            "bedrock_agent": "Company policies and HR expert - workplace culture, HR rules, employee policies, benefits (AWS Bedrock)",
            "gemini_agent": "General-purpose Google Gemini assistant for general queries and recommendations"
        }
        
        for agent_name in agent_names:
            try:
                logger.info(f"Attempting to get agent: {agent_name}")
                wrapper_agent = await self.agent_service.get_agent(agent_name)
                if not wrapper_agent:
                    logger.warning(f"Agent {agent_name} not found, skipping")
                    continue
                
                # Get the underlying Agent Framework agent (ChatAgent)
                if hasattr(wrapper_agent, 'agent') and wrapper_agent.agent is not None:
                    # Use the underlying Agent Framework agent (implements AgentProtocol)
                    agents_dict[agent_name] = wrapper_agent.agent
                    logger.info(f"✓ Successfully added agent {agent_name} to workflow")
                else:
                    logger.error(f"✗ Agent {agent_name} has no initialized agent attribute or agent is None")
            except Exception as e:
                logger.error(f"✗ Failed to add agent {agent_name}: {str(e)}", exc_info=True)
        
        if not agents_dict:
            raise ValueError("No valid agents found for workflow")
        
        logger.info(f"📋 Final registered agents: {list(agents_dict.keys())}")
        logger.info(f"Total agents registered: {len(agents_dict)}/{len(agent_names)}")
        
        # Build GroupChat workflow with prompt-based manager
        manager_instructions = """You are an intelligent routing manager for a multi-agent system.

Your role:
1. Analyze the user's query carefully to identify what information is needed
2. Select ONLY the agent(s) whose expertise is DIRECTLY required to answer the query
3. After agents respond, synthesize their answers into a coherent final response

Agent Selection Rules:
- If query mentions a person's NAME or asks for CONTACT information → SELECT people_lookup
- If query asks about COMPANY POLICIES, HR RULES, WORKPLACE CULTURE → SELECT bedrock_agent
- If query asks about CONFIGURATION, TECHNICAL DOCS (PDFs like TorSetup, Storage Encryption) → SELECT knowledge_finder
- If query asks for GENERAL ASSISTANCE, RECOMMENDATIONS, or information not requiring specialized databases → SELECT generic_agent or gemini_agent
- If query has MULTIPLE needs (e.g., contact + recommendations) → SELECT multiple agents

Agent Capabilities:
- people_lookup: Searches employee directory for contact information, email, phone, office location, job titles, organizational structure
- bedrock_agent: Company policies expert - HR rules, workplace culture, employee policies, benefits, vacation policies (AWS Bedrock powered)
- knowledge_finder: Technical documentation specialist - Configuration PDFs, technical setup guides (TorSetup.pdf, Storage Encryption.pdf, Privileged Identity Management.pdf, Mobile App Configuration.pdf)
- generic_agent: General-purpose Azure OpenAI assistant for recommendations, general queries, casual conversation
- gemini_agent: General-purpose Google Gemini assistant, alternative to generic_agent for general queries

Examples:
- "Get Udai's contact" → people_lookup
- "What's the vacation policy?" → bedrock_agent (HR policies)
- "How do I configure Tor?" → knowledge_finder (technical docs)
- "What are the storage encryption requirements?" → knowledge_finder (technical docs)
- "Suggest places to visit in Seattle" → generic_agent or gemini_agent
- "Get Udai's contacts and suggest places near him" → people_lookup AND generic_agent
- "What's the dress code policy?" → bedrock_agent (workplace culture)

Important: 
- ALWAYS select people_lookup when a person's name is mentioned and contact/employee information is needed
- Only select agents that are actually registered in the workflow (check available participants)
- Do not attempt to select agents that are not in the participant list

After agents respond, provide a final synthesis that combines all relevant information."""

        # Build the workflow using GroupChatBuilder
        workflow = (
            GroupChatBuilder()
            .set_prompt_based_manager(
                chat_client=self.chat_client,
                instructions=manager_instructions
            )
            .participants(agents_dict)  # Pass dict of name -> agent
            .with_max_rounds(5)  # Allow multiple rounds: selection -> response -> synthesis
            .build()
        )
        
        logger.info(
            f"GroupChat workflow built with {len(agents_dict)} agents and LLM-based selection"
        )
        
        return workflow
    
    async def execute_workflow(
        self, 
        request: GroupChatRequest
    ) -> GroupChatResponse:
        """
        Execute a multi-agent workflow using GroupChat with LLM-based agent selection.
        
        Features:
        - LLM manager selects ONLY relevant agents (no keyword matching)
        - Only selected agents execute (no unnecessary responses)
        - Responses are synthesized into coherent answer
        
        Args:
            request: Group chat request with message and agent list
            
        Returns:
            GroupChatResponse with intelligently selected and synthesized results
        """
        try:
            # 🛡️ STEP 1: Check input safety BEFORE processing
            is_safe, error_message = await self.content_safety.check_input_safety(request.message)
            
            if not is_safe:
                logger.warning(f"Unsafe input blocked: {request.message[:100]}...")
                # Return error response without processing
                return GroupChatResponse(
                    messages=[],
                    summary=error_message,
                    session_id=request.session_id or str(uuid4()),
                    total_turns=0,
                    participating_agents=[],
                    terminated_agents=[],
                    total_processing_time=0.0,
                    metadata={
                        "blocked": True,
                        "reason": "content_safety_violation"
                    }
                )
            
            # Create or retrieve session
            session_id = request.session_id or await self.session_manager.create_session()
            
            # Add user message to session
            user_message = GroupChatMessage(
                content=request.message,
                agent="user",
                timestamp=datetime.utcnow().isoformat(),
                turn=0,
                message_id=str(uuid4())
            )
            await self.session_manager.add_message_to_session(session_id, user_message)
            
            start_time = datetime.utcnow()
            
            logger.info(
                f"Starting GroupChat workflow for session {session_id} "
                f"with {len(request.agents)} available agents (LLM will select relevant ones)"
            )
            
            # Build the GroupChat workflow with LLM-based agent selection
            workflow = await self._build_group_chat_workflow(request.agents)
            
            # Execute workflow and collect agent responses with retry logic
            agent_responses = []
            selected_agents = []
            
            # Retry logic for rate limiting
            max_retries = 3
            retry_delay = 10  # seconds
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    async for event in workflow.run_stream(request.message):
                        logger.debug(f"Workflow event: {type(event).__name__}")
                        
                        if isinstance(event, WorkflowOutputEvent):
                            # Collect agent response
                            if hasattr(event, 'data'):
                                # Get the executor ID (the agent name used in workflow registration)
                                agent_name = getattr(event, 'source_executor_id', 'unknown')
                                
                                # Extract content from ChatMessage or other response types
                                response_text = ""
                                if isinstance(event.data, str):
                                    response_text = event.data
                                elif hasattr(event.data, 'content'):
                                    # ChatMessage object
                                    response_text = event.data.content if isinstance(event.data.content, str) else str(event.data.content)
                                elif hasattr(event.data, 'text'):
                                    # ChatMessage object may have text attribute
                                    response_text = event.data.text if isinstance(event.data.text, str) else str(event.data.text)
                                else:
                                    response_text = str(event.data)
                                
                                # 🛡️ STEP 2: Filter agent output for safety
                                filtered_response = await self.content_safety.filter_output(response_text, agent_name)
                                
                                agent_responses.append({
                                    'agent': agent_name,
                                    'content': filtered_response,
                                    'timestamp': datetime.utcnow().isoformat()
                                })
                                selected_agents.append(agent_name)
                                logger.info(f"Agent '{agent_name}' selected and executed by manager with response: {filtered_response[:100]}...")
                    
                    # If we got here without exception, break the retry loop
                    break
                    
                except ServiceResponseException as e:
                    last_error = e
                    if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                        logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Workflow execution failed: {str(e)}")
                    raise
            
            if not agent_responses:
                logger.warning("No agents were selected by the manager - using fallback")
                # Fallback: use generic agent
                generic_agent = await self.agent_service.get_agent("generic_agent")
                if generic_agent:
                    fallback_response = await generic_agent.run(request.message)
                    agent_responses.append({
                        'agent': 'generic_agent',
                        'content': fallback_response,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    selected_agents.append('generic_agent')
            
            total_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Convert agent responses to GroupChatMessage objects
            messages = [user_message]
            turn = 1
            
            for resp in agent_responses:
                message = GroupChatMessage(
                    content=resp['content'],
                    agent=resp['agent'],
                    timestamp=resp['timestamp'],
                    turn=turn,
                    message_id=str(uuid4())
                )
                messages.append(message)
                await self.session_manager.add_message_to_session(session_id, message)
                turn += 1
            
            # Synthesize responses if multiple agents responded
            if len(agent_responses) > 1:
                logger.info(f"Synthesizing {len(agent_responses)} agent responses")
                
                # Create mock results for synthesis
                mock_results = []
                for resp in agent_responses:
                    class MockResult:
                        def __init__(self, agent_name, text):
                            self.agent_name = agent_name
                            self.agent_run_response = type('obj', (object,), {'text': text})()
                    
                    mock_results.append(MockResult(resp['agent'], resp['content']))
                
                synthesized_text = await self._synthesize_responses(
                    mock_results,
                    request.message
                )
                
                # Add synthesized message
                synthesized_message = GroupChatMessage(
                    content=synthesized_text,
                    agent="workflow_synthesizer",
                    timestamp=datetime.utcnow().isoformat(),
                    turn=turn,
                    message_id=str(uuid4()),
                    metadata={
                        "synthesized": True,
                        "source_agents": selected_agents,
                        "synthesis_method": "llm_based"
                    }
                )
                messages.append(synthesized_message)
                await self.session_manager.add_message_to_session(session_id, synthesized_message)
            
            # Create response
            response = GroupChatResponse(
                messages=messages,
                session_id=session_id,
                total_turns=1,
                participating_agents=selected_agents,  # Only agents that were selected
                terminated_agents=[],
                total_processing_time=total_time,
                metadata={
                    "workflow_type": "group_chat_llm_selection",
                    "max_turns": request.max_turns,
                    "format": request.format,
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "available_agents": request.agents,
                    "selected_agents": selected_agents,
                    "selection_method": "llm_based_manager",
                    "synthesized": len(agent_responses) > 1
                }
            )
            
            logger.info(
                f"GroupChat workflow completed: {len(selected_agents)} agent(s) selected "
                f"from {len(request.agents)} available, {len(messages)-1} total messages, "
                f"completed in {total_time:.2f}s"
            )
            
            return response
            
        except ServiceResponseException as e:
            error_str = str(e).lower()
            
            # Handle rate limiting
            if "rate limit" in error_str:
                error_message = (
                    "⚠️ Azure OpenAI rate limit exceeded. Too many agents selected simultaneously. "
                    "Please try:\n"
                    "1. Simplifying your query to target fewer agents\n"
                    "2. Waiting a few seconds before retrying\n"
                    "3. Breaking your request into smaller parts"
                )
                logger.error(f"Rate limit exceeded: {str(e)}")
                raise ServiceResponseException(error_message) from e
            
            # Handle content filtering (Azure OpenAI built-in)
            elif "content_filter" in error_str or "responsibleaipolicyviolation" in error_str:
                # Parse the content filter result for user-friendly message
                filtered_categories = []
                if "violence" in error_str and "filtered': true" in error_str:
                    filtered_categories.append("violence")
                if "hate" in error_str and "filtered': true" in error_str:
                    filtered_categories.append("hate speech")
                if "sexual" in error_str and "filtered': true" in error_str:
                    filtered_categories.append("sexual content")
                if "self_harm" in error_str or "selfharm" in error_str and "filtered': true" in error_str:
                    filtered_categories.append("self-harm")
                
                category_text = ", ".join(filtered_categories) if filtered_categories else "inappropriate content"
                
                error_message = (
                    f"🚫 Your request was blocked due to content safety policies.\n\n"
                    f"Reason: The content was flagged for {category_text}.\n\n"
                    f"Please rephrase your request in a respectful and appropriate manner.\n\n"
                    f"For more information, visit: https://go.microsoft.com/fwlink/?linkid=2198766"
                )
                logger.warning(f"Content filter triggered: {category_text} | Query: {request.message[:100]}...")
                raise ServiceResponseException(error_message) from e
            
            else:
                logger.error(f"Service error: {str(e)}", exc_info=True)
                raise
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            raise
