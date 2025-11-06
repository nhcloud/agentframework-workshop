# Agent Framework Workshop - Project Structure

## 📁 Clean Project Organization

```
agentframework-workshop/
├── Backend/
│   ├── python/                        # Python FastAPI Backend
│   │   ├── agents/                    # Agent implementations
│   │   │   ├── __init__.py
│   │   │   └── specific_agents.py    # All agent classes (Generic, PeopleLookup, KnowledgeFinder, Bedrock, Gemini)
│   │   │
│   │   ├── clients/                   # Custom chat clients
│   │   │   ├── __init__.py
│   │   │   ├── aws_bedrock_client.py
│   │   │   ├── aws_bedrock_agent_client.py
│   │   │   └── google_gemini_client.py
│   │   │
│   │   ├── core/                      # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Settings and environment variables
│   │   │   └── logging_config.py     # Logging configuration
│   │   │
│   │   ├── models/                    # Data models
│   │   │   ├── __init__.py
│   │   │   └── chat_models.py        # Pydantic models for API
│   │   │
│   │   ├── routers/                   # FastAPI routes
│   │   │   ├── __init__.py
│   │   │   ├── agents.py             # Agent management endpoints
│   │   │   └── chat.py               # Chat endpoints
│   │   │
│   │   ├── services/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── agent_service.py      # Agent lifecycle management
│   │   │   ├── group_chat_service.py # Group chat orchestration
│   │   │   ├── response_formatter_service.py
│   │   │   ├── session_manager.py    # Session persistence
│   │   │   └── workflow_orchestration_service.py  # Main workflow logic
│   │   │
│   │   ├── sessions/                  # Session data (gitignored)
│   │   │
│   │   ├── .env                       # Environment variables (gitignored)
│   │   ├── .gitignore
│   │   ├── config.yml                 # Agent configuration
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── README.md                  # Python backend documentation
│   │   ├── requirements.txt           # Python dependencies
│   │   └── BEDROCK_GEMINI_SETUP.md   # Setup guide for AWS/Google
│   │
│   ├── dotnet/                        # .NET Backend (alternative implementation)
│   └── env.template                   # Environment variables template
│
├── frontend/                          # React Frontend
│   ├── public/
│   ├── src/
│   │   ├── services/
│   │   │   ├── ChatService.js
│   │   │   └── VoiceService.js
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   └── package.json
│
├── docs/                              # Documentation
│   ├── AI_SERVICES.md                # AI service integration guide
│   ├── GROUP_CHAT.md                 # GroupChat workflow documentation
│   ├── INSTALL.md                    # Installation guide
│   ├── PROMPTS.md                    # Prompt engineering guide
│   ├── START.md                      # Getting started guide
│   ├── img/                          # Documentation images
│   └── sample-data/                  # Sample data for testing
│
├── venv/                              # Python virtual environment (gitignored)
├── .gitignore                         # Root gitignore
└── README.md                          # Main project documentation
```

## 🎯 Key Components

### **Agents** (`Backend/python/agents/`)
- **GenericAgent**: General-purpose Azure OpenAI assistant
- **PeopleLookupAgent**: Employee directory search (Azure AI Foundry)
- **KnowledgeFinderAgent**: Company knowledge base search (Azure AI Foundry)
- **BedrockAgent**: AWS Bedrock integration
- **GeminiAgent**: Google Gemini integration

### **Workflow** (`Backend/python/services/workflow_orchestration_service.py`)
- **GroupChat Pattern**: LLM-managed agent selection
- **Dynamic Routing**: Intelligent agent selection based on query
- **Response Synthesis**: Combines multi-agent responses

### **API Endpoints** (`Backend/python/routers/`)
- `POST /chat` - Send message to workflow
- `GET /agents` - List available agents
- `POST /agents/{agent_name}/chat` - Direct agent chat

## 🧹 Cleaned Up Files

### Removed:
- ❌ Test files (`test_*.py`)
- ❌ Old migration docs (`*MIGRATION*.md`, `*QUICK*.md`)
- ❌ Session data (`sessions/*.json`)
- ❌ Log files (`*.log`)
- ❌ Compiled Python (`__pycache__/`)

### Kept:
- ✅ Core application code
- ✅ Configuration files
- ✅ Organized documentation in `/docs`
- ✅ Setup guides (BEDROCK_GEMINI_SETUP.md)

## 🚀 Quick Start

### Backend:
```bash
cd Backend/python
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend:
```bash
cd frontend
npm install
npm start
```

## 📚 Documentation
- **Installation**: `docs/INSTALL.md`
- **Getting Started**: `docs/START.md`
- **AI Services**: `docs/AI_SERVICES.md`
- **GroupChat Workflow**: `docs/GROUP_CHAT.md`
- **Prompts**: `docs/PROMPTS.md`

## 🔧 Configuration

### Environment Variables (`.env`):
```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=

# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=
PEOPLE_AGENT_ID=
KNOWLEDGE_AGENT_ID=

# AWS Bedrock (Optional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AWS_BEDROCK_MODEL_ID=

# Google Gemini (Optional)
GOOGLE_API_KEY=
GOOGLE_GEMINI_MODEL_ID=
```

## 🏗️ Architecture

```
User Request
    ↓
FastAPI Router (/chat)
    ↓
WorkflowOrchestrationService
    ↓
GroupChat Manager (LLM)
    ↓
┌─────────────┬──────────────┬─────────────────┐
│ Generic     │ PeopleLookup │ KnowledgeFinder │
│ Agent       │ Agent        │ Agent           │
└─────────────┴──────────────┴─────────────────┘
    ↓
Manager Synthesizes Responses
    ↓
Return to User
```

## 📝 Notes

- **Workflow Pattern**: Uses Microsoft Agent Framework's **GroupChat** pattern
- **Agent Selection**: LLM-based intelligent routing
- **Multi-Agent**: Supports parallel agent execution
- **Extensible**: Easy to add new agents (Bedrock, Gemini already integrated)
- **Production-Ready**: FastAPI with proper error handling and logging
