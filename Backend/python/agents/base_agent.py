"""
Base agent implementation for the Microsoft Agent Framework application.

This module provides the base agent class following the working Azure AI Projects pattern
for connecting to existing Azure AI Foundry agents with knowledge bases.
"""

import os
import logging
import time
from typing import Dict, Any, Optional
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base agent class following the working Azure AI Projects pattern.
    
    This class works with pre-existing Azure AI Foundry agents that have
    knowledge bases already configured.
    """
    
    def __init__(self, agent_id: str, name: str = None):
        """
        Initialize the base agent with existing Azure AI Foundry agent ID.
        
        Args:
            agent_id: ID of existing Azure AI Foundry agent
            name: Optional name for the agent instance
        """
        self.agent_id = agent_id
        self.name = name or f"Agent-{agent_id[:8]}"
        self.client = None
        self._thread_cache = {}  # Cache threads like in working implementation
        self._agent_info = None
        
        logger.info(f"Initializing {self.name} with agent ID: {agent_id}")
    def initialize(self):
        """Initialize the agent client following the working pattern."""
        try:
            from core.config import settings
            
            project_endpoint = settings.AZURE_AI_PROJECT_ENDPOINT
            if not project_endpoint:
                raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
            
            logger.info(f"Connecting to project endpoint: {project_endpoint}")
            
            # Create the project client using the correct constructor
            project_client = AIProjectClient(
                endpoint=project_endpoint,
                credential=DefaultAzureCredential()
            )
            
            # Get the AI Agent Client
            self.client = project_client.agents
            
            # Verify the agent exists (synchronous call)
            self._agent_info = self.client.get_agent(agent_id=self.agent_id)
            logger.info(f"Connected to agent {self.agent_id}: {self._agent_info.name}")
            logger.info(f"Agent description: {getattr(self._agent_info, 'description', 'No description')}")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    def _get_or_create_thread(self, conversation_id: Optional[str] = None):
        """Get or create a conversation thread (synchronous)."""
        thread_key = conversation_id or "default"
        
        if thread_key in self._thread_cache:
            return self._thread_cache[thread_key]
        
        # Create new thread (synchronous)
        thread = self.client.threads.create()
        self._thread_cache[thread_key] = thread
        logger.debug(f"Created new thread {thread.id} for conversation {thread_key}")
        return thread
    
    def run(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute the agent with a message (synchronous).
        
        Args:
            message: The user message to process
            context: Optional context including conversation_id
            
        Returns:
            The agent's response as a string
        """
        try:
            if not self.client:
                self.initialize()
            
            conversation_id = context.get("conversation_id") if context else None
            thread = self._get_or_create_thread(conversation_id)
            
            # Add user message (synchronous)
            message_obj = self.client.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            logger.debug(f"Added message to thread {thread.id}: {message[:100]}...")
            
            # Create and wait for run (synchronous)
            run = self.client.runs.create(
                thread_id=thread.id,
                agent_id=self.agent_id  # Using agent_id parameter as in working implementation
            )
            logger.debug(f"Started run {run.id} for agent {self.agent_id}")
            
            # Wait for completion (synchronous polling)
            max_iterations = 60  # 60 seconds max
            iterations = 0
            
            while iterations < max_iterations:
                run_status = self.client.runs.get(thread_id=thread.id, run_id=run.id)
                
                if run_status.status not in ["queued", "in_progress", "cancelling"]:
                    logger.debug(f"Run {run.id} completed with status: {run_status.status}")
                    break
                    
                logger.debug(f"Run {run.id} status: {run_status.status}, waiting...")
                time.sleep(1)
                iterations += 1
            
            if run_status.status == "completed":
                # Get response (synchronous)
                messages = self.client.messages.list(thread_id=thread.id, order="desc", limit=10)
                
                # Find the most recent assistant message  
                for message in messages:
                    if message.role == "assistant":
                        if hasattr(message, 'content') and message.content:
                            content_parts = []
                            for content in message.content:
                                if hasattr(content, 'text') and content.text:
                                    content_parts.append(content.text.value)
                            
                            if content_parts:
                                response = "\n".join(content_parts)
                                logger.info(f"Agent {self.name} completed successfully")
                                return response
                
                return "No response generated by the agent"
                
            else:
                error_msg = f"Run failed with status: {run_status.status}"
                if hasattr(run_status, 'last_error') and run_status.last_error:
                    error_msg += f" - {run_status.last_error}"
                logger.error(error_msg)
                return f"Sorry, I encountered an error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error running agent {self.name}: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def cleanup(self):
        """Clean up resources like in working implementation."""
        try:
            self._thread_cache.clear()
            if self.client:
                # The client will be cleaned up by the project client
                pass
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "agent_id": self.agent_id,
            "initialized": self.client is not None,
            "agent_name": self._agent_info.name if self._agent_info else None,
            "cached_threads": len(self._thread_cache)
        }