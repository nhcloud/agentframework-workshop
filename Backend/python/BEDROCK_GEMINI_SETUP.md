# AWS Bedrock and Google Gemini Integration Guide

## Overview
This guide helps you set up and test the new AWS Bedrock and Google Gemini agents in your Agent Framework project.

## 🚀 Quick Setup

### 1. Install Dependencies
Run the following commands in your Backend/python directory:
```bash
pip install boto3 botocore google-generativeai
```

### 2. Environment Configuration
Add these variables to your `.env` file:

#### AWS Bedrock Configuration
```bash
AWS_ACCESS_KEY_ID=your-aws-access-key-id-here
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key-here
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

#### Google Gemini Configuration
```bash
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_GEMINI_MODEL_ID=gemini-pro
```

### 3. Test the Setup
Run the test script:
```bash
python test_new_agents.py
```

## 📋 What's Been Added

### Backend Components
1. **Custom Chat Clients**: 
   - `AWSBedrockChatClient` - Integrates with AWS Bedrock runtime API
   - `GoogleGeminiChatClient` - Integrates with Google Gemini API

2. **Agent Classes**:
   - `BedrockAgent` - AWS Bedrock agent using Microsoft Agent Framework
   - `GeminiAgent` - Google Gemini agent using Microsoft Agent Framework

3. **Service Integration**:
   - Both agents work with existing `AgentService` and `GroupChatService`
   - Automatic agent discovery through the factory pattern

### Frontend Integration
- Agents are automatically discovered through the `/agents` API endpoint
- New agents will appear in the agent selection dropdown
- Group chat functionality supports the new agents

## 🔧 Available Agents

After setup, you'll have these agents available:

1. **Generic Agent** (`generic_agent`)
   - Azure OpenAI Chat Completion
   - General-purpose assistant

2. **People Lookup Agent** (`people_lookup`)  
   - Azure AI Foundry with employee knowledge base
   - Specialized for finding people information

3. **Knowledge Finder Agent** (`knowledge_finder`)
   - Azure AI Foundry with organizational knowledge base  
   - Specialized for organizational knowledge

4. **Bedrock Agent** (`bedrock_agent`) ⭐ NEW
   - AWS Bedrock with Amazon's foundation models
   - Supports Nova Pro and other Bedrock models

5. **Gemini Agent** (`gemini_agent`) ⭐ NEW
   - Google Gemini Pro model
   - Google's advanced AI capabilities

## 🧪 Testing

### Individual Agent Testing
```bash
# Test each agent individually
python test_new_agents.py
```

### Group Chat Testing
The agents work in group chat scenarios:
- Send one message to multiple agents
- Compare responses from different providers
- Mix and match Azure, AWS, and Google agents

### API Testing
Test via the REST API:
```bash
# Test individual agent
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "bedrock_agent", "message": "Hello!"}'

# Test group chat
curl -X POST "http://localhost:8000/group-chat" \
  -H "Content-Type: application/json" \
  -d '{"agent_names": ["generic_agent", "bedrock_agent", "gemini_agent"], "message": "Compare your capabilities"}'
```

## 📚 Usage Examples

### Python Usage
```python
from services.agent_service import AgentService

agent_service = AgentService()

# Get Bedrock agent
bedrock_agent = await agent_service.get_agent("bedrock_agent")
response = await bedrock_agent.run("What are your capabilities?")

# Get Gemini agent  
gemini_agent = await agent_service.get_agent("gemini_agent")
response = await gemini_agent.run("Tell me about yourself")
```

### Group Chat Usage
```python
from services.group_chat_service import GroupChatService

group_chat = GroupChatService()
agents = ["generic_agent", "bedrock_agent", "gemini_agent"]
responses = await group_chat.run_group_chat(agents, "Compare your AI models")
```

## 🛠️ Troubleshooting

### Common Issues

1. **AWS Credentials Not Working**
   - Verify AWS credentials are correct
   - Check region is supported for Bedrock
   - Ensure Bedrock service is enabled in your AWS account

2. **Google API Key Issues**
   - Verify API key is valid
   - Check quota limits in Google Cloud Console
   - Ensure Generative AI API is enabled

3. **Import Errors**
   - Make sure dependencies are installed: `pip install boto3 google-generativeai`
   - Check Python path includes the src directory

4. **Agent Not Found Errors**
   - Verify environment variables are set
   - Check .env file is loaded correctly
   - Run the test script to validate configuration

### Debug Mode
Set logging level to DEBUG in your .env file:
```bash
LOG_LEVEL=DEBUG
```

## 🔄 Next Steps

1. **Configure Your Providers**: Set up at least one of AWS or Google
2. **Run Tests**: Execute the test script to verify everything works
3. **Try the Frontend**: Access the web interface and test agent selection
4. **Experiment with Group Chat**: Compare responses from different AI providers
5. **Customize**: Modify model IDs and parameters in your .env file

## 💡 Tips

- You can use different Bedrock models by changing `AWS_BEDROCK_MODEL_ID`
- Gemini models include: `gemini-pro`, `gemini-pro-vision`
- All agents maintain conversation context within a session
- Group chat allows you to compare AI provider responses side-by-side