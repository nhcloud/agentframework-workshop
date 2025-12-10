"""
Microsoft Foundry Agent implementation.

Matches .NET AzureAIFoundryAgent pattern using Azure AI Foundry/PersistentAgentsClient.
Uses the same patterns as the .NET implementation including:
- AgentsClient for agent management (azure.ai.agents package)
- Thread caching for conversations
- Async agent execution

Based on official Microsoft Agent Framework Python documentation:
https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/azure-ai-foundry-agent

Requires: pip install azure-ai-agents azure-identity
"""

import os
import logging
from typing import Optional, List, Dict, Any

from .base_agent_new import BaseAgent, GroupChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class AzureAIFoundryAgent(BaseAgent):
    """
    Azure AI Foundry Agent (matches .NET AzureAIFoundryAgent).
    
    Uses Azure AI Foundry AgentsClient for connecting to
    pre-configured agents in Azure AI Foundry.
    
    Based on the official Microsoft Agent Framework pattern using:
    - azure.ai.agents.aio.AgentsClient for async operations
    - agents_client.threads.create() for thread management
    - agents_client.messages.create() for message handling
    - agents_client.runs.create_and_poll() for run execution
    """
    
    def __init__(
        self,
        name: str = "ms_foundry_people_agent",
        agent_id: Optional[str] = None,
        project_endpoint: Optional[str] = None,
        description: str = "People lookup agent powered by Azure AI Foundry",
        instructions: str = "You are a helpful assistant for finding information about people.",
        model_deployment: Optional[str] = None,
        enable_long_running_memory: bool = False,
        managed_identity_client_id: Optional[str] = None,
    ):
        """
        Initialize the Azure AI Foundry agent (matches .NET constructor pattern).
        
        Args:
            name: Agent name
            agent_id: Azure AI Foundry agent ID
            project_endpoint: Azure AI Foundry project endpoint
            description: Agent description
            instructions: System instructions
            model_deployment: Model deployment name
            enable_long_running_memory: Whether to enable long-running memory
            managed_identity_client_id: Optional managed identity client ID for Azure authentication
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            enable_long_running_memory=enable_long_running_memory
        )
        
        self._agent_id = agent_id or os.getenv("MS_FOUNDRY_AGENT_ID", "")
        self._project_endpoint = project_endpoint or os.getenv("MS_FOUNDRY_PROJECT_ENDPOINT", "")
        self._model_deployment = model_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self._managed_identity_client_id = managed_identity_client_id or os.getenv("MANAGED_IDENTITY_CLIENT_ID", "")
        
        # Azure AI Agents client (matches .NET _azureAgentClient / PersistentAgentsClient)
        self._agents_client = None
        
        # Credential for async context management
        self._credential = None

        # Track how we authenticated (for diagnostics/health)
        self._credential_source = "uninitialized"
        
        # Foundry agent instance (matches .NET _foundryAgent)
        self._foundry_agent = None
        
        # Thread cache (matches .NET _threadCache)
        self._thread_cache: Dict[str, Any] = {}
        
        logger.info(f"AzureAIFoundryAgent '{name}' created with agent ID: {self._agent_id}")
    
    async def _do_initialize_async(self) -> None:
        """Initialize the Foundry client (mirrors the .NET flow)."""
        try:
            from azure.ai.agents.aio import AgentsClient

            self._validate_required_config()

            logger.info(
                "Initializing Azure AI Foundry agent %s for endpoint: %s",
                self._agent_id,
                self._project_endpoint,
            )

            # Create credential with a Managed Identity first strategy (like .NET),
            # but allow a graceful fallback to DefaultAzureCredential so local dev can work.
            self._credential = await self._create_credential()

            # Create the service client using the chosen credential.
            self._agents_client = AgentsClient(
                endpoint=self._project_endpoint,
                credential=self._credential,
            )

            # Store minimal agent reference (ID is sufficient for runs/messages)
            self._foundry_agent = {"id": self._agent_id}

            logger.info("Initialized Azure AI Foundry agent %s", self._agent_id)

        except ImportError as ie:
            logger.error("Required package not installed: %s", str(ie))
            logger.error("Install with: pip install azure-ai-agents azure-identity")
            raise
        except Exception as ex:
            logger.error("Failed to initialize Azure AI Foundry agent %s: %s", self._name, str(ex))
            raise

    def _validate_required_config(self) -> None:
        if not self._project_endpoint:
            raise ValueError("MS_FOUNDRY_PROJECT_ENDPOINT is required")
        if not self._agent_id:
            raise ValueError("MS_FOUNDRY_AGENT_ID is required")

    async def _create_credential(self):
        """Create credential with local-dev-first strategy.

        Order (reversed from before to prioritize local dev):
        1) Try DefaultAzureCredential first (works locally via az login / SP envs).
        2) If that fails AND MANAGED_IDENTITY_CLIENT_ID is set, fall back to
           ManagedIdentityCredential (works in Azure with IMDS).
        """
        from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential

        # Always try DefaultAzureCredential first – it chains CLI, SP, etc.
        logger.info("Trying DefaultAzureCredential first (az login / service principal)")
        try:
            cred = DefaultAzureCredential(
                managed_identity_client_id=self._managed_identity_client_id or None,
                exclude_interactive_browser_credential=True,
            )
            self._credential_source = "default_credential"
            return cred
        except Exception as dac_ex:
            logger.warning(
                "DefaultAzureCredential instantiation failed: %s. "
                "Will try ManagedIdentityCredential if configured.",
                dac_ex,
            )

        # Fallback to explicit ManagedIdentityCredential (Azure-only)
        if self._managed_identity_client_id:
            logger.info(
                "Falling back to ManagedIdentityCredential with client ID: %s",
                self._managed_identity_client_id,
            )
            self._credential_source = "managed_identity_fallback"
            return ManagedIdentityCredential(client_id=self._managed_identity_client_id)

        # Re-raise if nothing worked
        raise RuntimeError(
            "No valid Azure credential available. "
            "Run 'az login' or set service-principal env vars for local dev, "
            "or ensure Managed Identity is available in Azure."
        )

    def get_auth_status(self) -> Dict[str, Any]:
        """Expose auth status for diagnostics (similar to .NET health logging)."""
        return {
            "agent": self._name,
            "project_endpoint": self._project_endpoint,
            "agent_id": self._agent_id,
            "credential_source": self._credential_source,
            "managed_identity_client_id": self._managed_identity_client_id or None,
            "initialized": self._agents_client is not None,
        }
    
    async def respond_async(
        self,
        message: str,
        conversation_history: Optional[List[GroupChatMessage]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response using Azure AI Foundry (matches .NET RespondAsync).
        
        Uses the AgentsClient API pattern from azure.ai.agents:
        1. Get or create a thread via threads.create()
        2. Add user message via messages.create()
        3. Run the agent via runs.create_and_poll()
        4. Retrieve messages via messages.list()
        """
        if self._agents_client is None:
            await self.initialize_async()
        if self._agents_client is None:
            raise RuntimeError("Azure AI Foundry agent not properly initialized")
        
        try:
            logger.info(f"Processing message with Azure AI Foundry agent {self._agent_id}")
            
            thread_key = self._get_thread_key(conversation_history)
            thread_id = await self._get_or_create_thread(thread_key)
            
            enhanced_message = message if not context else f"{message}\n\nAdditional Context: {context}"
            
            # Add user message to the thread
            await self._create_message(thread_id, enhanced_message)
            
            # Create and poll the run to completion
            await self._create_and_process_run(thread_id)
            
            # Get the messages from the thread
            response_text = await self._get_assistant_response(thread_id)
            
            logger.info(
                f"Azure AI Foundry agent {self._agent_id} generated response: "
                f"{len(response_text)} characters"
            )
            return response_text
            
        except Exception as ex:
            logger.error(f"Error processing with Azure AI Foundry agent {self._agent_id}: {str(ex)}")
            raise
    
    def _get_thread_key(self, conversation_history: Optional[List[GroupChatMessage]]) -> str:
        """Get thread key from conversation history."""
        if conversation_history and len(conversation_history) > 0:
            return f"conv_{conversation_history[0].message_id}"
        return "default"
    
    async def _get_or_create_thread(self, thread_key: str) -> str:
        """
        Get or create thread for conversation (matches .NET GetOrCreateThread).
        
        Uses AgentsClient.threads.create() to create new threads.
        """
        if thread_key not in self._thread_cache:
            # Create a new thread using the AgentsClient
            thread = await self._agents_client.threads.create()
            thread_id = thread.id
            if not thread_id:
                raise RuntimeError("Failed to obtain thread id from threads.create() result")
            self._thread_cache[thread_key] = thread_id
            logger.debug(f"Created new thread {thread_id} for key: {thread_key}")
        
        return self._thread_cache[thread_key]

    async def _create_message(self, thread_id: str, content: str):
        """
        Add a message to the thread using AgentsClient.messages.create().
        """
        await self._agents_client.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )
        logger.debug(f"Added user message to thread {thread_id}")

    async def _create_and_process_run(self, thread_id: str):
        """
        Create a run and poll until completion using AgentsClient.runs.create_and_process().

        The SDK provides:
        - runs.create() – starts the run, returns immediately
        - runs.create_and_process() – creates and polls to terminal state (convenience)
        """
        import asyncio

        try:
            logger.debug("Creating run for thread %s with agent %s", thread_id, self._agent_id)

            # Prefer create_and_process if available (SDK >=1.0.0b1)
            if hasattr(self._agents_client.runs, "create_and_process"):
                run = await self._agents_client.runs.create_and_process(
                    thread_id=thread_id,
                    agent_id=self._agent_id,
                    polling_interval=1,
                )
            else:
                # Fallback: create + manual poll
                run = await self._agents_client.runs.create(
                    thread_id=thread_id,
                    agent_id=self._agent_id,
                )
                while run.status in ("queued", "in_progress", "requires_action"):
                    await asyncio.sleep(1)
                    run = await self._agents_client.runs.get(
                        thread_id=thread_id,
                        run_id=run.id,
                    )

            status = getattr(run, "status", "unknown")
            logger.debug("Run completed with status: %s", status)

            if status in ("failed", "cancelled", "expired"):
                error_msg = f"Run ended with status: {status}"
                if getattr(run, "last_error", None):
                    error_msg += f" - Error: {run.last_error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            return run

        except Exception as ex:
            logger.error("Error creating or processing run for thread %s: %s", thread_id, str(ex))
            raise

    async def _get_assistant_response(self, thread_id: str) -> str:
        """
        Get the latest assistant response from the thread using AgentsClient.messages.list().
        """
        try:
            # messages.list() returns an AsyncItemPaged – do NOT await it directly.
            messages_paged = self._agents_client.messages.list(thread_id=thread_id)

            logger.debug("Retrieving messages from thread %s", thread_id)

            # Iterate async to collect messages
            async for msg in messages_paged:
                if msg.role == "assistant":
                    content_list = getattr(msg, "content", [])
                    for content in content_list:
                        if hasattr(content, "text"):
                            if hasattr(content.text, "value"):
                                return content.text.value
                            elif isinstance(content.text, str):
                                return content.text
                        elif isinstance(content, str):
                            return content

            logger.warning("No assistant response found in thread %s", thread_id)
            return "I apologize, but I couldn't generate a response from the Azure AI Foundry agent."

        except Exception as ex:
            logger.error("Error retrieving assistant response from thread %s: %s", thread_id, str(ex))
            raise
    
    async def cleanup_async(self) -> None:
        """
        Cleanup resources (matches .NET DisposeAsync pattern).
        
        Deletes threads using AgentsClient.threads.delete().
        """
        if self._agents_client and self._foundry_agent:
            for thread_key, thread_id in self._thread_cache.items():
                try:
                    await self._agents_client.threads.delete(thread_id)
                    logger.debug(f"Cleaned up thread: {thread_id}")
                except Exception as ex:
                    logger.warning(f"Failed to cleanup thread {thread_id}: {str(ex)}")
        
        # Close the agents client if needed
        if self._agents_client:
            try:
                await self._agents_client.close()
            except Exception as ex:
                logger.warning(f"Failed to close agents client: {str(ex)}")
        
        # Close the credential if needed
        if self._credential:
            try:
                await self._credential.close()
            except Exception as ex:
                logger.warning(f"Failed to close credential: {str(ex)}")
        
        self._thread_cache.clear()


class MicrosoftFoundryPeopleAgent(AzureAIFoundryAgent):
    """
    Microsoft Foundry People Agent (matches .NET MicrosoftFoundryPeopleAgent).
    
    Specialized agent for people lookup using Azure AI Foundry.
    """
    
    def __init__(
        self,
        instructions_service=None,
        **kwargs
    ):
        """Initialize with optional instructions service."""
        name = "ms_foundry_people_agent"
        description = "Specialized agent for finding people information using Microsoft Foundry"
        instructions = (
            "You are a People Lookup Agent expert at finding information about people, contacts, and team members. "
            "Base answers on verified directory information. When you cannot confirm details, clearly state that "
            "no record was found and suggest contacting HR/IT. Never invent names, titles, roles, or contact details."
        )
        
        # Get instructions from service if provided
        if instructions_service:
            instructions = instructions_service.get_agent_instructions(name)
            description = instructions_service.get_agent_description(name)
        
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            **kwargs
        )
