#!/usr/bin/env python3
"""
Test script to verify Azure AI agents are properly retrieved with knowledge bases
"""
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents import create_agent


async def test_agent_retrieval():
    """Test that agents are properly retrieved from Azure AI Foundry"""
    print("🔍 Testing Agent Retrieval from Azure AI Foundry")
    print("=" * 60)
    
    # Test People Lookup Agent retrieval
    print("\n=== Testing PeopleLookupAgent Retrieval ===")
    try:
        agent = create_agent('people_lookup')
        await agent.initialize()
        
        # Check if we successfully retrieved the agent
        if hasattr(agent, 'azure_ai_agent') and agent.azure_ai_agent:
            print(f"✅ Successfully retrieved agent: {agent.azure_ai_agent.id}")
            print(f"   Agent name: {agent.azure_ai_agent.name}")
            print(f"   Agent model: {agent.azure_ai_agent.model}")
            print(f"   Agent instructions: {agent.azure_ai_agent.instructions[:100]}...")
            
            # Test with a specific employee query
            response = await agent.run("Who is Udai?")
            print(f"✅ Agent response (first 200 chars): {response[:200]}...")
        else:
            print("❌ Failed to retrieve agent from Azure AI Foundry")
            
        await agent.cleanup()
        
    except Exception as e:
        print(f"❌ PeopleLookupAgent retrieval failed: {str(e)}")
    
    # Test Knowledge Finder Agent retrieval
    print("\n=== Testing KnowledgeFinderAgent Retrieval ===")
    try:
        agent = create_agent('knowledge_finder')
        await agent.initialize()
        
        # Check if we successfully retrieved the agent
        if hasattr(agent, 'azure_ai_agent') and agent.azure_ai_agent:
            print(f"✅ Successfully retrieved agent: {agent.azure_ai_agent.id}")
            print(f"   Agent name: {agent.azure_ai_agent.name}")
            print(f"   Agent model: {agent.azure_ai_agent.model}")
            print(f"   Agent instructions: {agent.azure_ai_agent.instructions[:100]}...")
            
            # Test with a specific policy query
            response = await agent.run("Eligible contributors of PIM?")
            print(f"✅ Agent response (first 200 chars): {response[:200]}...")
        else:
            print("❌ Failed to retrieve agent from Azure AI Foundry")
            
        await agent.cleanup()
        
    except Exception as e:
        print(f"❌ KnowledgeFinderAgent retrieval failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✨ Agent retrieval tests completed!")


if __name__ == "__main__":
    asyncio.run(test_agent_retrieval())