# Python Agent Framework Implementation

A production-ready multi-agent orchestration framework built with Python, Microsoft Agent Framework, and FastAPI. This implementation mirrors the functionality of the .NET version while leveraging Python's ecosystem and the Microsoft Agent Framework for Python.

## 🚀 Features

- **Microsoft Agent Framework Integration** - Built on Microsoft's official Python agent framework
- **Multi-Agent Orchestration** - Coordinate multiple AI agents with intelligent turn-based conversations  
- **Unified Chat API** - Single `/chat` endpoint automatically handles both single-agent and multi-agent conversations
- **Flexible Response Formats** - Choose between user-friendly synthesized responses or detailed conversation logs
- **Session Management** - Persistent conversation history with file-based or Redis storage
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

## 🛠️ Installation

### Prerequisites

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Azure OpenAI** or **Azure AI Foundry** account
- **pip** or **pipenv** for package management

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
   
   # Edit .env file with your Azure credentials
   # Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME
   ```

5. **Run the application:**
   ```bash
   # Development mode with auto-reload
   python app.py
   
   # Or using uvicorn directly
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will start on:
   - **HTTP**: http://localhost:8000
   - **Interactive Docs**: http://localhost:8000 (Swagger UI)
   - **ReDoc**: http://localhost:8000/redoc

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
# Azure OpenAI (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Application Settings
FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO
PORT=8000

# Session Management
SESSION_STORAGE_TYPE=file  # or 'redis'
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
```

## 🚀 Usage Examples

### Single Agent Chat

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how can you help me?",
    "agents": ["generic_agent"]
  }'
```

### Multi-Agent Chat

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find information about John Doe and any related documents",
    "agents": ["people_lookup", "knowledge_finder"],
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
├── src/
│   ├── agents/          # Agent implementations
│   ├── core/           # Configuration and logging
│   ├── models/         # Pydantic data models
│   ├── routers/        # FastAPI route handlers
│   ├── services/       # Business logic services
│   └── main.py         # FastAPI application
├── config.yml          # Agent configurations
├── requirements.txt    # Python dependencies
├── pyproject.toml     # Project configuration
└── app.py             # Application entry point
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

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
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

3. **Session Storage Issues**
   - Ensure session storage directory exists and is writable
   - For Redis: verify Redis server is running and accessible

### Logging

Logs are written to both console and `agent_framework.log`. Set `LOG_LEVEL=DEBUG` for detailed debugging information.

## 📄 License

This project follows the same license as the Microsoft Agent Framework.