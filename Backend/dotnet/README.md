# .NET Agent Framework

A production-ready multi-agent orchestration framework built with .NET 9, ASP.NET Core, **Microsoft.Agents.AI Framework**, and Azure AI integration. This framework enables intelligent agent collaboration, conversation management, and flexible response formatting for complex AI-powered applications.

## 🌟 Features

- **Microsoft.Agents.AI Framework** - Built on Microsoft's official .NET AI agent framework with dual agent architecture
- **Unified Chat Endpoint** - Single `/chat` endpoint handles both single-agent and multi-agent conversations
- **Multi-Agent Orchestration** - Coordinate multiple AI agents with intelligent turn-based conversations
- **Flexible Response Formats** - Choose between user-friendly synthesized responses or detailed conversation logs
- **Session Management** - Persistent conversation history across requests
- **Agent Auto-Routing** - Automatic agent selection based on query intent
- **Template System** - Pre-configured group chat templates for common scenarios
- **Azure AI Integration** - Seamless integration with Azure AI Foundry and Azure OpenAI
- **Interactive Frontend** - React-based UI with voice input/output, markdown rendering, and real-time chat
- **RESTful API** - Well-documented API with Swagger UI and comprehensive .http test collection

## 🗺️ Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  - Chat Interface  - Voice I/O  - Format Selector          │
└────────────────────┬──────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼──────────────────────────────────────┐
│              ASP.NET Core API (.NET 9)                      │
│           Microsoft.Agents.AI Framework                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ChatController│  │AgentService  │  │GroupChatService  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         ResponseFormatterService                     │  │
│  │  - SingleAgent  - Synthesis  - Structured  Formats  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Agent Types:                                               │
│  • AzureOpenAIAgent - Standard ChatClient-based agents      │
│  • AzureAIFoundryAgent - PersistentAgentsClient enterprise  │
└────────────────────┬──────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────┐
│              Azure AI Foundry / OpenAI                      │
│  - GPT-4  - Microsoft.Agents.AI  - Embeddings              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **.NET 9 SDK** - [Download](https://dotnet.microsoft.com/download/dotnet/9.0)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Azure OpenAI** or **Azure AI Foundry** account
- **VS Code** with REST Client extension (optional, for testing)

### Backend Setup (.NET 9 + Microsoft.Agents.AI)

1. **Navigate to backend directory:**
   ```bash
   cd Backend/dotnet
   ```

2. **Create environment file:**
   ```bash
   cp .env.template .env
   # Edit env file with your Azure credentials
   # Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME
   ```

3. **Build and run:**
   ```bash
   dotnet restore
   dotnet build
   dotnet run --urls http://localhost:8000
   ```

4. **Access the API:**
   - Swagger UI: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - Agent List: http://localhost:8000/agents

### Frontend Setup (React)

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm start
   ```

4. **Access the UI:**
   - Open http://localhost:3001
   - Start chatting with AI agents!

## 🤖 Available Agents

| Agent | Specialization | Use Cases |
|-------|----------------|-----------|
| **generic_agent** | General-purpose assistant | Technical questions, explanations, coding help |
| **foundry_people_lookup** | Find people and expertise | Employee search, skill matching, team discovery |
| **foundry_knowledge_finder** | Document and policy search | Policy questions, documentation lookup |
| **PolicyAgent** | HR policy expert | Leave policies, conduct rules, compliance |

> **Note:** Foundry agents require Azure AI Foundry configuration. Generic agents work with Azure OpenAI only.

## 📡 API Endpoints

### Chat API (Unified)

```http
POST /chat
Content-Type: application/json

{
  "message": "What is the vacation policy?",
  "agent": "generic_agent",              // Optional: specific agent
  "agents": ["generic_agent", "PolicyAgent"],  // Optional: multi-agent
  "format": "synthesis",                 // Optional: "synthesis" | "detailed"
  "session_id": "user123",              // Optional: for conversation history
  "max_turns": 3                        // Optional: for multi-agent
}
```

### Response Formats

#### Synthesis Format (Default)
```json
{
  "content": "Based on company policy, you get 15 days...",
  "agent": "PolicyAgent",
  "session_id": "user123",
  "timestamp": "2024-01-15T10:30:00Z",
  "metadata": {
    "format": "synthesis",
    "agent_framework": "Microsoft.Agents.AI"
  }
}
```

#### Detailed Format
```json
{
  "content": "Multi-agent conversation completed",
  "responses": [
    {
      "agent": "generic_agent",
      "content": "Let me help you with that...",
      "turn": 1
    },
    {
      "agent": "PolicyAgent", 
      "content": "According to HR policy...",
      "turn": 2
    }
  ],
  "metadata": {
    "format": "detailed",
    "total_turns": 2,
    "agent_framework": "Microsoft.Agents.AI"
  }
}
```

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Azure OpenAI Configuration (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21

# Azure AI Foundry Configuration (Optional)
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
PEOPLE_AGENT_ID=asst-people-agent
KNOWLEDGE_AGENT_ID=asst-knowledge-agent
MANAGED_IDENTITY_CLIENT_ID=your-managed-identity-id

# Application Settings
FRONTEND_URL=http://localhost:3001
LOG_LEVEL=Information
```

### Agent Configuration (`config.yml`)

```yaml
agents:
  - name: generic_agent
    model: gpt-4
    temperature: 0.7
    max_tokens: 1500
    instructions: |
      You are a helpful AI assistant...

  - name: PolicyAgent
    model: gpt-4
    temperature: 0.5
    instructions: |
      You are an HR policy expert...
```

### API Configuration (`appsettings.json`)

```json
{
  "AzureAI": {
    "Endpoint": "https://your-endpoint.openai.azure.com/",
    "DeploymentName": "gpt-4",
    "ApiKey": "your-api-key"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information"
    }
  }
}
```

## 🛠️ Development

### Project Structure

```
agentframework-workshop/
├── Backend/
│   └── dotnet/
│       ├── Controllers/              # API endpoints
│       ├── Services/                 # Business logic
│       ├── Models/                   # Data models
│       ├── Agents/                   # Agent implementations
│       │   ├── BaseAgent.cs          # IAgent interface, AzureOpenAIAgent, AzureAIFoundryAgent
│       │   └── SpecificAgents.cs     # Legacy agent implementations
│       ├── Configuration/            # Config models
│       ├── config.yml                # Agent definitions
│       ├── README.md                 # Detailed .NET implementation docs
│       └── workshop_dotnet_agent_framework.ipynb  # Interactive tutorial
├── frontend/
│   └── src/
│       ├── App.js                    # Main React component
│       ├── services/                 # API clients
│       └── components/               # UI components
└── docs/                             # Documentation
```

### Key Services

- **`ChatController`** - Unified chat endpoint with format handling
- **`AgentService`** - Agent lifecycle and execution management (creates AzureOpenAIAgent and AzureAIFoundryAgent)
- **`GroupChatService`** - Multi-agent orchestration with Microsoft.Agents.AI
- **`ResponseFormatterService`** - Response formatting strategies
- **`SessionManager`** - Conversation history persistence with AgentThread support
- **`AgentInstructionsService`** - Dynamic agent instruction loading

### Microsoft.Agents.AI Framework Components

- **`AzureOpenAIAgent`** - Standard agents using ChatClient for Azure OpenAI
- **`AzureAIFoundryAgent`** - Enterprise agents using PersistentAgentsClient
- **`AgentThread`** - Stateful conversation thread management
- **`ChatClientAgent`** - Agent wrapper for execution
- **`PersistentAgentsClient`** - Azure AI Foundry integration client

## 🚦 Response Format Details

### Format Selection Logic

```csharp
// Backend automatically detects format preference
if (request.Format?.ToLower() == "detailed") {
    // Return full conversation with all turns
    return DetailedResponse(groupResponse);
} else {
    // Return synthesized user-friendly response (default)
    return FormattedResponse(groupResponse);
}
```

### Frontend Format Handling

```javascript
// Frontend adapts rendering based on format
if (responseFormat === 'detailed' && response.responses) {
    // Display multiple messages with turn badges
    response.responses.forEach(resp => displayAgentMessage(resp));
} else {
    // Display single synthesized message
    displayMessage(response.content);
}
```

## 📊 Performance

- **Response Time**: 2-5 seconds for single agent
- **Multi-Agent**: 5-15 seconds (depends on max_turns and agent count)
- **Session Persistence**: In-memory with optional Redis backend
- **Concurrent Users**: Scales with ASP.NET Core async pipeline
- **Timeout Management**: 5-minute default for AI operations

## 🔍 Testing

### Interactive Notebook
- **`workshop_dotnet_agent_framework.ipynb`** - Hands-on tutorial with Microsoft.Agents.AI examples
- Test agents interactively in VS Code with .NET Interactive
- Learn agent creation patterns and multi-agent orchestration

### API Testing
- **Swagger UI**: http://localhost:8000 - Interactive API documentation
- **`DotNetAgentFramework.http`** - REST Client test collection
- Health checks, single-agent, and multi-agent test cases

## 🔒 Security

- HTTPS enabled by default
- CORS configured for frontend origin
- API key validation for Azure services
- Session isolation per user
- Request validation and sanitization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- **`Backend/dotnet/README.md`** - Comprehensive .NET implementation guide
- **`workshop_dotnet_agent_framework.ipynb`** - Interactive learning tutorial
- **`DotNetAgentFramework.http`** - API test examples
- **Swagger UI** - Live API documentation

## 📄 License

This project is licensed under the MIT License.

## 🙋 Support

For issues, questions, or contributions:
- **GitHub Issues**: [Create an issue](https://github.com/nhcloud/agentframework-workshop/issues)
- **Documentation**: Check the `Backend/dotnet/README.md` for detailed implementation docs
- **Examples**: See `DotNetAgentFramework.http` for API examples
- **Tutorial**: Open `workshop_dotnet_agent_framework.ipynb` in VS Code

## 🎯 Roadmap

- [ ] Redis-backed session persistence
- [ ] Agent performance metrics dashboard
- [ ] Custom agent plugins system
- [ ] Streaming responses with SSE
- [ ] Multi-language support
- [ ] Advanced agent selection strategies
- [ ] Conversation export/import
- [ ] Enhanced Microsoft.Agents.AI integration features

---

Built with ❤️ using .NET 9, Microsoft.Agents.AI Framework, React, and Azure AI