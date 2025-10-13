#!/usr/bin/env python3
"""
Test script to verify agents have correct agent_type attribute
"""
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents import create_agent
from src.services.agent_service import AgentService


async def test_agent_types():
    """Test that all agents have the required agent_type attribute"""
    print("🔍 Testing Agent Types for Group Chat Compatibility")
    print("=" * 60)
    
    # Test direct agent creation
    print("\n=== Testing Direct Agent Creation ===")
    agent_names = ['generic_agent', 'people_lookup', 'knowledge_finder']
    
    for agent_name in agent_names:
        try:
            agent = create_agent(agent_name)
            
            # Check if agent has agent_type attribute
            if hasattr(agent, 'agent_type'):
                print(f"✅ {agent_name}: agent_type = '{agent.agent_type}'")
            else:
                print(f"❌ {agent_name}: Missing agent_type attribute")
            
            # Test initialization
            if agent_name in ['people_lookup', 'knowledge_finder']:
                await agent.initialize()
            else:
                agent.initialize()
            
            print(f"   Initialization successful for {agent_name}")
            
        except Exception as e:
            print(f"❌ {agent_name}: Error - {str(e)}")
    
    # Test through agent service
    print("\n=== Testing Agent Service ===")
    service = AgentService()
    
    for agent_name in agent_names:
        try:
            agent = await service.get_agent(agent_name)
            
            if hasattr(agent, 'agent_type'):
                print(f"✅ Service {agent_name}: agent_type = '{agent.agent_type}'")
            else:
                print(f"❌ Service {agent_name}: Missing agent_type attribute")
                
        except Exception as e:
            print(f"❌ Service {agent_name}: Error - {str(e)}")
    
    await service.cleanup()
    
    print("\n" + "=" * 60)
    print("✨ Agent type tests completed!")


if __name__ == "__main__":
    asyncio.run(test_agent_types())