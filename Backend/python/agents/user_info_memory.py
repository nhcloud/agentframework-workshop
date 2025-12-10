"""
User Info Memory for agents.

Provides memory storage for user information that can be used across conversations.
Matches the pattern used in .NET for agent memory.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UserInfoMemory:
    """
    Memory storage for user information.
    
    Stores and retrieves user-specific information that can be used
    to personalize agent responses across conversations.
    """
    
    def __init__(self):
        """Initialize the user info memory."""
        self._memory: Dict[str, Dict[str, Any]] = {}
        logger.info("UserInfoMemory initialized")
    
    def store(self, session_id: str, key: str, value: Any) -> None:
        """
        Store a value in memory for a session.
        
        Args:
            session_id: Session identifier
            key: Key for the value
            value: Value to store
        """
        if session_id not in self._memory:
            self._memory[session_id] = {}
        
        self._memory[session_id][key] = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.debug(f"Stored '{key}' for session {session_id}")
    
    def retrieve(self, session_id: str, key: str) -> Optional[Any]:
        """
        Retrieve a value from memory.
        
        Args:
            session_id: Session identifier
            key: Key for the value
            
        Returns:
            Stored value or None if not found
        """
        if session_id not in self._memory:
            return None
        
        entry = self._memory[session_id].get(key)
        if entry:
            return entry.get("value")
        return None
    
    def get_all(self, session_id: str) -> Dict[str, Any]:
        """
        Get all stored values for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary of all stored values
        """
        if session_id not in self._memory:
            return {}
        
        return {
            key: entry.get("value")
            for key, entry in self._memory[session_id].items()
        }
    
    def clear(self, session_id: str) -> None:
        """
        Clear all memory for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._memory:
            del self._memory[session_id]
            logger.debug(f"Cleared memory for session {session_id}")
    
    def clear_all(self) -> None:
        """Clear all memory for all sessions."""
        self._memory = {}
        logger.info("Cleared all user info memory")
    
    def to_context_string(self, session_id: str) -> str:
        """
        Convert stored memory to a context string for the agent.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted string with user information
        """
        info = self.get_all(session_id)
        if not info:
            return ""
        
        lines = ["User Information:"]
        for key, value in info.items():
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)

