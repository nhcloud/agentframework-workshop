"""
Agent module exports - Using Microsoft Agent Framework.
"""

from .specific_agents import (
    GenericAgent,
    PeopleLookupAgent, 
    KnowledgeFinderAgent,
    create_agent,
    AVAILABLE_AGENTS
)

__all__ = [
    "GenericAgent",
    "PeopleLookupAgent",
    "KnowledgeFinderAgent", 
    "create_agent",
    "AVAILABLE_AGENTS"
]