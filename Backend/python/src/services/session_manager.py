"""
Session management service for handling conversation history and persistence.

This service provides functionality similar to the .NET SessionManager.
"""

import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ..core.config import settings
from ..models.chat_models import GroupChatMessage


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Service for managing conversation sessions and history.
    
    This service provides functionality to:
    - Create and manage conversation sessions
    - Store and retrieve conversation history
    - Handle session cleanup and expiration
    """
    
    def __init__(self):
        """Initialize the session manager."""
        self.storage_type = settings.SESSION_STORAGE_TYPE
        self.storage_path = Path(settings.SESSION_STORAGE_PATH)
        self._sessions: Dict[str, List[GroupChatMessage]] = {}
        self._session_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Ensure storage directory exists
        if self.storage_type == "file":
            self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SessionManager initialized with storage type: {self.storage_type}")
    
    async def create_session(self) -> str:
        """
        Create a new conversation session.
        
        Returns:
            The session ID
        """
        try:
            session_id = str(uuid4())
            
            self._sessions[session_id] = []
            self._session_metadata[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "message_count": 0
            }
            
            if self.storage_type == "file":
                await self._save_session_to_file(session_id)
            
            logger.info(f"Created new session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise
    
    async def get_session_history(self, session_id: str) -> List[GroupChatMessage]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of chat messages in the session
        """
        try:
            # Try to get from memory first
            if session_id in self._sessions:
                await self._update_session_access(session_id)
                return self._sessions[session_id]
            
            # Try to load from file storage
            if self.storage_type == "file":
                history = await self._load_session_from_file(session_id)
                if history is not None:
                    self._sessions[session_id] = history
                    await self._update_session_access(session_id)
                    return history
            
            # Session not found, return empty list
            logger.warning(f"Session {session_id} not found, returning empty history")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get session history for {session_id}: {str(e)}")
            return []
    
    async def add_message_to_session(self, session_id: str, message: GroupChatMessage) -> None:
        """
        Add a message to a session.
        
        Args:
            session_id: The session ID
            message: The message to add
        """
        try:
            # Ensure session exists in memory
            if session_id not in self._sessions:
                self._sessions[session_id] = []
                self._session_metadata[session_id] = {
                    "created_at": datetime.utcnow().isoformat(),
                    "last_accessed": datetime.utcnow().isoformat(),
                    "message_count": 0
                }
            
            # Add message to session
            self._sessions[session_id].append(message)
            
            # Update metadata
            await self._update_session_access(session_id)
            self._session_metadata[session_id]["message_count"] = len(self._sessions[session_id])
            
            # Persist to storage
            if self.storage_type == "file":
                await self._save_session_to_file(session_id)
            
            logger.debug(f"Added message to session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its history.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Remove from memory
            if session_id in self._sessions:
                del self._sessions[session_id]
            
            if session_id in self._session_metadata:
                del self._session_metadata[session_id]
            
            # Remove from file storage
            if self.storage_type == "file":
                session_file = self.storage_path / f"{session_id}.json"
                if session_file.exists():
                    session_file.unlink()
                
                metadata_file = self.storage_path / f"{session_id}_metadata.json"
                if metadata_file.exists():
                    metadata_file.unlink()
            
            logger.info(f"Deleted session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            return False
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions.
        
        Returns:
            List of session information
        """
        try:
            sessions = []
            
            # Get sessions from memory
            for session_id, metadata in self._session_metadata.items():
                session_info = {
                    "session_id": session_id,
                    "message_count": len(self._sessions.get(session_id, [])),
                    **metadata
                }
                sessions.append(session_info)
            
            # Get additional sessions from file storage if using file storage
            if self.storage_type == "file":
                for file_path in self.storage_path.glob("*_metadata.json"):
                    session_id = file_path.stem.replace("_metadata", "")
                    
                    # Skip if already in memory
                    if session_id in self._session_metadata:
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        session_info = {
                            "session_id": session_id,
                            **metadata
                        }
                        sessions.append(session_info)
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for session {session_id}: {str(e)}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions based on max age.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            cleanup_count = 0
            max_age = timedelta(days=settings.SESSION_MAX_AGE_DAYS)
            cutoff_time = datetime.utcnow() - max_age
            
            sessions_to_delete = []
            
            # Check memory sessions
            for session_id, metadata in self._session_metadata.items():
                try:
                    last_accessed = datetime.fromisoformat(metadata["last_accessed"])
                    if last_accessed < cutoff_time:
                        sessions_to_delete.append(session_id)
                except Exception as e:
                    logger.warning(f"Invalid timestamp for session {session_id}: {str(e)}")
            
            # Delete expired sessions
            for session_id in sessions_to_delete:
                if await self.delete_session(session_id):
                    cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} expired sessions")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return 0
    
    async def _save_session_to_file(self, session_id: str) -> None:
        """Save session data to file."""
        try:
            # Save messages
            session_file = self.storage_path / f"{session_id}.json"
            messages_data = []
            
            for message in self._sessions.get(session_id, []):
                messages_data.append(message.model_dump() if hasattr(message, 'model_dump') else message.__dict__)
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, ensure_ascii=False, indent=2)
            
            # Save metadata
            metadata_file = self.storage_path / f"{session_id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._session_metadata.get(session_id, {}), f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save session {session_id} to file: {str(e)}")
            raise
    
    async def _load_session_from_file(self, session_id: str) -> Optional[List[GroupChatMessage]]:
        """Load session data from file."""
        try:
            session_file = self.storage_path / f"{session_id}.json"
            metadata_file = self.storage_path / f"{session_id}_metadata.json"
            
            if not session_file.exists():
                return None
            
            # Load messages
            with open(session_file, 'r', encoding='utf-8') as f:
                messages_data = json.load(f)
            
            messages = []
            for message_data in messages_data:
                message = GroupChatMessage(**message_data)
                messages.append(message)
            
            # Load metadata if available
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    self._session_metadata[session_id] = metadata
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id} from file: {str(e)}")
            return None
    
    async def _update_session_access(self, session_id: str) -> None:
        """Update session last accessed timestamp."""
        if session_id in self._session_metadata:
            self._session_metadata[session_id]["last_accessed"] = datetime.utcnow().isoformat()
    
    async def cleanup(self):
        """Clean up session manager resources."""
        try:
            self._sessions.clear()
            self._session_metadata.clear()
            logger.info("SessionManager cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during SessionManager cleanup: {str(e)}")