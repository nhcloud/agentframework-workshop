#!/usr/bin/env python3
"""
Test script for Microsoft Agent Framework implementation
"""
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents import create_agent
from src.services.agent_service import AgentService


async def test_generic_agent():
    """Test GenericAgent with Agent Framework"""
    print("=== Testing GenericAgent ===")
    try:
        agent = create_agent('generic_agent')
        agent.initialize()
        print(f"✅ Generic Agent created: {agent.get_info()}")
        
        # Test running the agent
        response = await agent.run("Hello, how are you?")
        print(f"✅ Generic Agent response: {response[:100]}...")
        
        agent.cleanup()
        print("✅ Generic Agent cleanup successful")
        
    except Exception as e:
        print(f"❌ Generic Agent test failed: {str(e)}")


async def test_azure_ai_agent():
    """Test Azure AI agents with Agent Framework"""
    print("\n=== Testing Azure AI Agents ===")
    
    # Test People Lookup Agent
    try:
        agent = create_agent('people_lookup')
        await agent.initialize()
        print(f"✅ People Lookup Agent created: {agent.get_info()}")
        
        # Test running the agent
        response = await agent.run("Find information about employees in the engineering team")
        print(f"✅ People Lookup Agent response: {response[:100]}...")
        
        await agent.cleanup()
        print("✅ People Lookup Agent cleanup successful")
        
    except Exception as e:
        print(f"❌ People Lookup Agent test failed: {str(e)}")
    
    # Test Knowledge Finder Agent
    try:
        agent = create_agent('knowledge_finder')
        await agent.initialize()
        print(f"✅ Knowledge Finder Agent created: {agent.get_info()}")
        
        # Test running the agent
        response = await agent.run("What are the company policies on remote work?")
        print(f"✅ Knowledge Finder Agent response: {response[:100]}...")
        
        await agent.cleanup()
        print("✅ Knowledge Finder Agent cleanup successful")
        
    except Exception as e:
        print(f"❌ Knowledge Finder Agent test failed: {str(e)}")


async def test_agent_service():
    """Test AgentService integration"""
    print("\n=== Testing AgentService Integration ===")
    try:
        service = AgentService()
        
        # Test generic agent through service
        response = await service.chat_with_agent(
            'generic_agent', 
            'Hello from Agent Service!'
        )
        print(f"✅ Agent Service (generic): {response['content'][:100]}...")
        
        # Test Azure AI agent through service
        response = await service.chat_with_agent(
            'people_lookup',
            'Find information about Sofia Alvarez'
        )
        print(f"✅ Agent Service (people_lookup): {response['content'][:100]}...")
        
        await service.cleanup()
        print("✅ Agent Service cleanup successful")
        
    except Exception as e:
        print(f"❌ Agent Service test failed: {str(e)}")


async def main():
    """Run all tests"""
    print("🚀 Testing Microsoft Agent Framework Integration")
    print("=" * 50)
    
    await test_generic_agent()
    await test_azure_ai_agent()
    await test_agent_service()
    
    print("\n" + "=" * 50)
    print("✨ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())