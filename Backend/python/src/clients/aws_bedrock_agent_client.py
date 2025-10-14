"""
AWS Bedrock Agent Client for existing agent retrieval using Agent Runtime API.

This module provides a client for interacting with existing AWS Bedrock agents
using the bedrock-agent-runtime service, following Microsoft Agent Framework patterns.
"""

import json
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator, Sequence, Tuple
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
import asyncio

from agent_framework import (
    BaseChatClient,
    ChatMessage,
    ChatOptions,
    ChatResponse,
    ChatResponseUpdate,
    Role,
    TextContent,
)
from agent_framework.exceptions import ServiceException

logger = logging.getLogger(__name__)


class AWSBedrockAgentClient(BaseChatClient):
    """
    AWS Bedrock Agent client for interacting with existing agents using Agent Runtime API.
    This client retrieves existing agents rather than creating new ones.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_alias_id: str = "TSTALIASID",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        session_id: Optional[str] = None
    ):
        """
        Initialize AWS Bedrock Agent client for existing agent.
        
        Args:
            agent_id: The ID of the existing AWS Bedrock agent
            agent_alias_id: The alias ID for the agent (default: TSTALIASID)
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
            session_id: Optional session ID for conversation continuity
        """
        super().__init__()
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.session_id = session_id or f"bedrock-session-{uuid4()}"
        
        # Initialize boto3 session
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key
            })
        
        self.session = boto3.Session(**session_kwargs)
        self.client = self.session.client("bedrock-agent-runtime")
        
        logger.info(f"Initialized AWS Bedrock Agent client for agent: {agent_id}")
    
    def _extract_input_text(self, message: Any) -> str:
        """
        Extract textual content from a ChatMessage or similar structure.

        Args:
            message: Chat message or compatible structure provided by Agent Framework

        Returns:
            Extracted text content
        """
        if message is None:
            return ""

        # Direct text attribute on ChatMessage
        text_attr = getattr(message, "text", None)
        if text_attr:
            return str(text_attr).strip()

        segments: List[str] = []

        # Contents collection (Agent Framework specific)
        contents = getattr(message, "contents", None)
        if contents:
            for item in contents:
                if isinstance(item, TextContent) and getattr(item, "text", None):
                    segments.append(str(item.text))
                elif isinstance(item, dict):
                    for key in ("text", "input_text", "body"):
                        value = item.get(key)
                        if value:
                            segments.append(str(value))
                            break
                elif hasattr(item, "text") and getattr(item, "text", None):
                    segments.append(str(getattr(item, "text")))
                elif isinstance(item, str):
                    segments.append(item)

        # Additional properties sometimes hold the text payload
        if not segments:
            additional = getattr(message, "additional_properties", None)
            if isinstance(additional, dict):
                for key in ("text", "input_text", "body"):
                    value = additional.get(key)
                    if value:
                        segments.append(str(value))
                        break

        # Dictionary-like messages
        if not segments and isinstance(message, dict):
            for key in ("text", "input_text", "body"):
                value = message.get(key)
                if value:
                    segments.append(str(value))
                    break

        # Raw string fallback
        if not segments and isinstance(message, str):
            segments.append(message)

        combined = " ".join(part.strip() for part in segments if part is not None)
        return combined.strip()

    def _select_user_message(self, messages: Sequence[ChatMessage]) -> Optional[ChatMessage]:
        """Return the most recent user-facing message from the prepared list."""
        for msg in reversed(messages):
            if getattr(msg, "role", None) == Role.USER:
                return msg
        return messages[-1] if messages else None

    def _invoke_agent_sync(self, input_text: str, session_id: str) -> Tuple[Dict[str, Any], str, str, List[Dict[str, Any]]]:
        """Invoke the AWS Bedrock agent synchronously and collect response chunks."""
        response = self.client.invoke_agent(
            agentId=self.agent_id,
            agentAliasId=self.agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
        )

        collected_text_parts: List[str] = []
        raw_events: List[Dict[str, Any]] = []

        completion_events = response.get("completion", [])
        for event in completion_events:
            raw_events.append(event)
            chunk = event.get("chunk")
            if not chunk:
                continue
            bytes_payload = chunk.get("bytes")
            if not bytes_payload:
                continue
            if isinstance(bytes_payload, (bytes, bytearray)):
                collected_text_parts.append(bytes_payload.decode("utf-8"))

        response_text = "".join(collected_text_parts).strip()
        resolved_session_id = response.get("sessionId") or session_id

        return response, response_text, resolved_session_id, raw_events

    async def _inner_get_response(
        self,
        messages: List[ChatMessage],
        *,
        chat_options: ChatOptions,
        **kwargs,
    ) -> ChatResponse:
        """Return a ChatResponse compatible with the Agent Framework."""

        # Adopt thread-managed conversation id if provided
        session_id = chat_options.conversation_id or self.session_id or f"bedrock-session-{uuid4()}"
        self.session_id = session_id

        user_message = self._select_user_message(messages)
        if not user_message:
            raise ServiceException("No user message found in conversation")

        input_text = self._extract_input_text(user_message)
        if not input_text:
            logger.error(
                "Unable to extract text from message: type=%s, dir=%s",
                type(user_message).__name__,
                dir(user_message),
            )
            raise ServiceException("No text content found in user message")

        try:
            response, response_text, resolved_session_id, raw_events = await asyncio.to_thread(
                self._invoke_agent_sync,
                input_text,
                session_id,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error("AWS Bedrock Agent error (%s): %s", error_code, error_message)
            raise ServiceException(f"AWS Bedrock Agent error: {error_message}") from e
        except Exception as e:
            logger.error("Unexpected error invoking AWS Bedrock agent: %s", e)
            raise ServiceException(f"Error invoking AWS Bedrock agent: {str(e)}") from e

        if resolved_session_id:
            self.session_id = resolved_session_id

        if not response_text:
            logger.warning("AWS Bedrock agent returned no text. Raw response: %s", response)
            response_text = "I'm sorry, I couldn't generate a response right now."

        assistant_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text=response_text)],
            additional_properties={"provider": "aws_bedrock"},
        )
        assistant_message.conversation_id = self.session_id

        chat_response = ChatResponse(
            messages=[assistant_message],
            # Don't set text parameter - it creates a duplicate message
            conversation_id=self.session_id,
            response_id=response.get("responseId") or response.get("sessionId"),
            model_id=response.get("modelId"),
            additional_properties={"raw_events": raw_events},
            raw_representation=response,
        )

        return chat_response
    
    async def _inner_get_streaming_response(
        self,
        messages: List[ChatMessage],
        *,
        chat_options: ChatOptions,
        **kwargs,
    ) -> AsyncGenerator[ChatResponseUpdate, None]:
        """Stream ChatResponseUpdate objects from the Bedrock agent."""

        session_id = chat_options.conversation_id or self.session_id or f"bedrock-session-{uuid4()}"
        self.session_id = session_id

        user_message = self._select_user_message(messages)
        if not user_message:
            raise ServiceException("No user message found in conversation")

        input_text = self._extract_input_text(user_message)
        if not input_text:
            raise ServiceException("No text content found in user message")

        try:
            response, response_text, resolved_session_id, raw_events = await asyncio.to_thread(
                self._invoke_agent_sync,
                input_text,
                session_id,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error("AWS Bedrock Agent streaming error (%s): %s", error_code, error_message)
            raise ServiceException(f"AWS Bedrock Agent streaming error: {error_message}") from e
        except Exception as e:
            logger.error("Unexpected error during Bedrock streaming: %s", e)
            raise ServiceException(f"Error in AWS Bedrock agent streaming: {str(e)}") from e

        if resolved_session_id:
            self.session_id = resolved_session_id

        accumulated_text = ""
        for event in raw_events:
            chunk = event.get("chunk")
            text_piece = ""
            if chunk and chunk.get("bytes"):
                if isinstance(chunk["bytes"], (bytes, bytearray)):
                    text_piece = chunk["bytes"].decode("utf-8")

            if text_piece:
                accumulated_text += text_piece
                yield ChatResponseUpdate(
                    text=text_piece,
                    role=Role.ASSISTANT,
                    conversation_id=self.session_id,
                    raw_representation=event,
                )

        if not accumulated_text and response_text:
            # Ensure at least one update is emitted even if raw events were empty
            yield ChatResponseUpdate(
                text=response_text,
                role=Role.ASSISTANT,
                conversation_id=self.session_id,
                raw_representation=response,
            )
    
    async def complete_chat_async(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> ChatMessage:
        """Compatibility helper that returns the assistant's ChatMessage."""

        chat_response = await self.get_response(messages, **kwargs)
        if chat_response.messages:
            return chat_response.messages[-1]

        fallback_message = ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=chat_response.text or "")])
        fallback_message.conversation_id = getattr(chat_response, "conversation_id", self.session_id)
        return fallback_message
    
    async def complete_chat_streaming_async(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Compatibility helper yielding plain text chunks for legacy callers."""

        async for update in self.get_streaming_response(messages, **kwargs):
            if update.text:
                yield update.text if isinstance(update.text, str) else update.text.text
            elif update.contents:
                for item in update.contents:
                    if isinstance(item, TextContent) and item.text:
                        yield item.text
    
class BedrockAgentWrapper:
    """
    Wrapper class to make AWS Bedrock Agent compatible with Microsoft Agent Framework.
    This class adapts the existing agent for use with the framework's patterns.
    """

    def __init__(self, agent_client: "AWSBedrockAgentClient"):
        """Initialize the wrapper with an AWS Bedrock Agent client."""

        self.client = agent_client
        self.agent_id = agent_client.agent_id
        self.session_id = agent_client.session_id

    async def run_async(self, messages: List[ChatMessage], **kwargs) -> Dict[str, Any]:
        """Run the agent with the given messages."""

        try:
            response_message = await self.client.complete_chat_async(messages, **kwargs)

            # Extract text content for response
            response_text = ""
            if hasattr(response_message, "contents") and isinstance(response_message.contents, list):
                for item in response_message.contents:
                    if isinstance(item, TextContent):
                        response_text += item.text + " "
                    elif hasattr(item, "text"):
                        response_text += item.text + " "
            elif hasattr(response_message, "text") and response_message.text:
                response_text = response_message.text

            return {
                "messages": [response_message],
                "response": response_text.strip(),
                "agent_id": self.agent_id,
                "session_id": self.session_id,
            }
        except Exception as e:
            logger.error(f"Error running Bedrock Agent wrapper: {str(e)}")
            raise ServiceException(f"Error running Bedrock Agent: {str(e)}")

    def get_info(self) -> Dict[str, Any]:
        """Get information about the agent."""

        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "type": "aws_bedrock_agent",
            "description": f"AWS Bedrock Agent {self.agent_id} (existing agent retrieval)",
        }