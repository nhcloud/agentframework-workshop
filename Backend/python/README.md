# Python Agent Framework Implementation

A production-ready multi-agent orchestration framework built with Python, Microsoft Agent Framework, and FastAPI. This implementation supports multiple AI providers including Azure OpenAI, AWS Bedrock, and Google Gemini.

## 🚀 Features

- **Microsoft Agent Framework Integration** - Built on Microsoft's official Python agent framework
- **Multi-Provider Support** - Seamlessly integrate Azure OpenAI, AWS Bedrock agents, and Google Gemini
- **Multi-Agent Orchestration** - Coordinate multiple AI agents with intelligent turn-based conversations  
- **Unified Chat API** - Single `/chat` endpoint automatically handles both single-agent and multi-agent conversations
- **AWS Bedrock Agent Integration** - Connect to existing AWS Bedrock agents via Runtime API
- **Google Gemini Support** - Direct integration with Google's Gemini 2.0 Flash models
- **Flexible Response Formats** - Choose between user-friendly synthesized responses or detailed conversation logs
- **Session Management** - Persistent conversation history with file-based storage
- **Agent Auto-Selection** - Automatic agent selection based on query intent when no agents specified
- **Template System** - Pre-configured chat templates for common scenarios
- **Azure AI Integration** - Seamless integration with Azure OpenAI and Azure AI Foundry
- **FastAPI Backend** - Modern, high-performance API with automatic OpenAPI documentation
- **Production Ready** - Comprehensive logging, error handling, and monitoring

## 🏗️ Architecture

### System Components

- **FastAPI Application** - Modern Python web framework with automatic API documentation
- **Microsoft Agent Framework** - Official Microsoft framework for agent orchestration
- **Agent Layer** - Specialized agents (Generic, People Lookup, Knowledge Finder)
- **Service Layer** - Business logic (AgentService, GroupChatService, SessionManager)
- **Storage Layer** - File-based or Redis session persistence
- **Azure Integration** - Azure OpenAI and Azure AI Foundry services

### Agent Types

1. **Generic Agent** - General-purpose assistant using Azure OpenAI
2. **People Lookup Agent** - Specialized for finding people and organizational information  
3. **Knowledge Finder Agent** - Specialized for searching and retrieving knowledge
4. **AWS Bedrock Agent** - Connects to existing AWS Bedrock agents (no creation, retrieval only)
5. **Google Gemini Agent** - Uses Google Gemini 2.0 Flash for conversations

## 🛠️ Installation

### Prerequisites

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Azure OpenAI** or **Azure AI Foundry** account (for Generic/People/Knowledge agents)
- **AWS Account** with Bedrock access (optional, for AWS Bedrock agent)
- **Google API Key** (optional, for Gemini agent)
- **pip** for package management

### Setup

1. **Clone and navigate to the Python backend:**
   ```bash
   cd Backend/python
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit .env file with your credentials
   ```

   **Required for Azure agents:**
   - `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint
   - `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
   - `AZURE_OPENAI_DEPLOYMENT_NAME` - Deployment name (e.g., gpt-4o)
   
   **Optional for AWS Bedrock agent:**
   - `AWS_BEDROCK_AGENT_ID` - Existing Bedrock agent ID (e.g., 4EZLIRQY2N)
   - `AWS_BEDROCK_AGENT_ALIAS_ID` - Agent alias (default: TSTALIASID)
   - `AWS_ACCESS_KEY_ID` - AWS access key
   - `AWS_SECRET_ACCESS_KEY` - AWS secret key
   - `AWS_REGION` - AWS region (default: us-east-1)
   
   **Optional for Google Gemini agent:**
   - `GOOGLE_API_KEY` - Google AI API key
   - `GOOGLE_GEMINI_MODEL_ID` - Model name (default: gemini-2.0-flash-exp)

5. **Run the application:**
   ```bash
   # Development mode with auto-reload
   python app.py
   
   # Or using uvicorn directly
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will start on:
   - **HTTP**: http://localhost:8000
   - **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
   - **ReDoc**: http://localhost:8000/redoc

## 🤖 Available Agents

| Agent Name | Provider | Description | Status |
|------------|----------|-------------|--------|
| `generic_agent` | Azure OpenAI | General-purpose conversational AI | ✅ Active |
| `people_lookup` | Azure AI Foundry | Employee and people information finder | ✅ Active |
| `knowledge_finder` | Azure AI Foundry | Document and policy search | ✅ Active |
| `bedrock_agent` | AWS Bedrock | Custom AWS Bedrock agent (retrieval mode) | ✅ Active |
| `gemini_agent` | Google Gemini | Gemini 2.0 Flash model | ✅ Active |

**Note:** Enable/disable agents by configuring appropriate environment variables in `.env` file.

## 📡 API Endpoints

### Chat Endpoints

- `POST /chat` - Unified chat endpoint (single or multi-agent)
- `GET /templates` - Get available chat templates
- `POST /from-template` - Create chat from template
- `GET /sessions` - List all chat sessions
- `GET /sessions/{session_id}` - Get session history
- `DELETE /sessions/{session_id}` - Delete session
- `POST /sessions/cleanup` - Cleanup expired sessions

### Agent Endpoints

- `GET /agents` - List all available agents
- `GET /agents/{agent_name}` - Get agent information
- `POST /agents/{agent_name}/initialize` - Initialize specific agent
- `GET /agents/{agent_name}/status` - Get agent status
- `POST /agents/{agent_name}/chat` - Chat directly with agent
- `GET /agents/{agent_name}/capabilities` - Get agent capabilities

### Health Endpoint

- `GET /health` - Health check

## 🔧 Configuration

### Environment Variables

```bash
# Azure OpenAI (Required for Azure agents)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01

# Azure AI Foundry (Optional for specialized agents)
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
PEOPLE_AGENT_ID=your-people-agent-id
KNOWLEDGE_AGENT_ID=your-knowledge-agent-id

# AWS Bedrock (Optional)
AWS_BEDROCK_AGENT_ID=4EZLIRQY2N  # Your existing Bedrock agent ID
AWS_BEDROCK_AGENT_ALIAS_ID=TSTALIASID
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=amazon.nova-pro-v1:0  # For direct model mode

# Google Gemini (Optional)
GOOGLE_API_KEY=your-google-api-key
GOOGLE_GEMINI_MODEL_ID=gemini-2.0-flash-exp

# Application Settings
FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO
PORT=8000

# Session Management
SESSION_STORAGE_PATH=./sessions
```

### Agent Configuration

Agents are configured in `config.yml`:

```yaml
agents:
  generic_agent:
    type: "generic"
    enabled: true
    instructions: "You are a helpful assistant..."
    description: "General-purpose assistant"
    
  people_lookup:
    type: "specialized"
    enabled: true
    instructions: "You are a people lookup specialist..."
    description: "People and organizational information finder"
    
  bedrock_agent:
    type: "aws_bedrock"
    enabled: true
    description: "AWS Bedrock agent integration"
    
  gemini_agent:
    type: "google_gemini"
    enabled: true
    description: "Google Gemini AI assistant"
```

## 🔌 Multi-Provider Integration

### Azure OpenAI (Generic Agent)
Uses Azure OpenAI with `AzureOpenAIChatClient` from the Agent Framework. Simple chat completion model.

### Azure AI Foundry (Specialized Agents)
Uses `AzureAIAgentClient` to connect to existing agents in Azure AI Foundry with:
- Vector stores for knowledge retrieval
- File search capabilities
- Custom tools and functions

### AWS Bedrock Agent
**Retrieval Mode Only** - Connects to existing AWS Bedrock agents:
- Uses `bedrock-agent-runtime` API (NOT creation API)
- Requires existing agent ID from AWS console
- Maintains server-side conversation history with session IDs
- Supports streaming responses

**Key Difference from Azure:** AWS agents are treated as **endpoints** you invoke directly, while Azure agents are **objects** you retrieve and manage.

### Google Gemini
Direct integration with Google's Gemini API:
- Uses `google-generativeai` library
- Supports Gemini 2.0 Flash models
- Handles role conversion (USER → "user", ASSISTANT → "model")
- Supports streaming and function calling

## 🆚 Integration Comparison

| Feature | Azure AI | AWS Bedrock | Google Gemini |
|---------|----------|-------------|---------------|
| **Client Type** | Built-in AzureAIAgentClient | Custom BaseChatClient | Custom BaseChatClient |
| **Agent Retrieval** | ✅ Get agent object | ❌ Direct invocation | ❌ Direct model access |
| **Knowledge Base** | Explicit vector store tools | Implicit (in agent config) | N/A |
| **Session Management** | Automatic threads | Manual session IDs | Conversation history |
| **Authentication** | Azure CLI / Managed Identity | AWS IAM keys | API key |
| **Best For** | Complex workflows with tools | Pre-configured AWS agents | Fast, simple conversations |

## 🚀 Usage Examples

### Single Agent Chat (Azure)

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how can you help me?",
    "agents": ["generic_agent"]
  }'
```

### AWS Bedrock Agent

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What can you tell me about our services?",
    "agents": ["bedrock_agent"],
    "session_id": "my-session-123"
  }'
```

### Google Gemini Agent

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in simple terms",
    "agents": ["gemini_agent"]
  }'
```

### Multi-Agent Chat (Mixed Providers)

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find information about John Doe and any related documents",
    "agents": ["people_lookup", "knowledge_finder", "bedrock_agent"],
    "max_turns": 3,
    "format": "user_friendly"
  }'
```

### Template-based Chat

```bash
curl -X POST "http://localhost:8000/from-template" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "general_inquiry",
    "message": "Research about our company policies"
  }'
```

## 🔧 Development

### Project Structure

```
Backend/python/
├── agents/             # Agent implementations
│   ├── specific_agents.py    # All agent classes
│   ├── base_agent.py         # Base agent class
│   └── __init__.py
├── clients/            # Custom chat clients
│   ├── aws_bedrock_agent_client.py   # AWS Bedrock agent client
│   ├── aws_bedrock_client.py         # AWS Bedrock model client
│   ├── google_gemini_client.py       # Google Gemini client
│   └── __init__.py
├── core/               # Configuration and logging
│   ├── config.py             # Settings and config
│   ├── logging_config.py     # Logging setup
│   └── __init__.py
├── models/             # Pydantic data models
│   ├── chat_models.py        # Request/response models
│   └── __init__.py
├── routers/            # FastAPI route handlers
│   ├── chat.py               # Chat endpoints
│   ├── agents.py             # Agent endpoints
│   └── __init__.py
├── services/           # Business logic services
│   ├── agent_service.py              # Agent management
│   ├── group_chat_service.py         # Multi-agent orchestration
│   ├── session_manager.py            # Session handling
│   ├── response_formatter_service.py # Response formatting
│   └── __init__.py
├── sessions/           # Session storage directory
├── main.py             # FastAPI application entry point
├── app.py              # Application runner
├── config.yml          # Agent configurations
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (create from .env.example)
└── README.md           # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

### Code Formatting

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/
```

## 🐳 Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t agent-framework-python .
docker run -p 8000:8000 --env-file .env agent-framework-python
```

## 🔒 Production Considerations

- **Environment Variables** - Use secure secret management
- **Logging** - Configure structured logging for monitoring
- **Session Storage** - Use Redis for production session management
- **Rate Limiting** - Implement API rate limiting
- **Authentication** - Add authentication middleware if needed
- **Monitoring** - Set up health checks and metrics collection

## 🤝 Frontend Integration

This Python backend is fully compatible with the existing React frontend. The API endpoints match the .NET implementation, ensuring seamless integration.

## 📚 API Documentation

When running the application, interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000
- **ReDoc**: http://localhost:8000/redoc

## 🔍 Troubleshooting

### Common Issues

1. **Azure OpenAI Connection Issues**
   - Verify endpoint URL and API key
   - Check deployment name matches your Azure resource
   - Ensure proper network connectivity

2. **Agent Initialization Failures**
   - Check Azure credentials are correctly configured
   - Verify the deployment has sufficient quota
   - Review logs for specific error messages

3. **AWS Bedrock Agent Issues**
   - Ensure you have an **existing** agent ID (this integration doesn't create agents)
   - Verify AWS credentials have `bedrock-agent-runtime:InvokeAgent` permission
   - Check the agent alias ID (default: `TSTALIASID` for test alias)
   - Confirm the agent is in the correct AWS region
   - Error: "Agent not found" means wrong ID or insufficient permissions

4. **Google Gemini Issues**
   - Verify API key is valid and has Gemini API enabled
   - Ensure model name is correct: `gemini-2.0-flash-exp` (not `gemini-pro`)
   - Check API quota limits
   - Error 404: Model not found means wrong model name

5. **Import Errors**
   - All files are now in the root Python folder (no `src/` directory)
   - Imports use direct paths: `from agents import ...`, `from clients import ...`
   - If you see `ModuleNotFoundError`, ensure all dependencies are installed: `pip install -r requirements.txt`

6. **Session Storage Issues**
   - Ensure session storage directory exists and is writable
   - Check `SESSION_STORAGE_PATH` in `.env` points to valid directory

### Logging

Logs are written to both console and `agent_framework.log`. Set `LOG_LEVEL=DEBUG` for detailed debugging information.

### Missing Dependencies

If you see import errors for specific libraries:
```bash
# AWS Bedrock
pip install boto3

# Google Gemini
pip install google-generativeai

# Azure
pip install azure-ai-projects azure-identity
```

## 📄 License

This project follows the same license as the Microsoft Agent Framework.