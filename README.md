# .NET Agent Framework

A production-ready multi-agent orchestration framework built with .NET 9, ASP.NET Core, **Microsoft.Agents.AI Framework**, and Azure AI integration. This framework enables intelligent agent collaboration, conversation management, and flexible response formatting for complex AI-powered applications.

## 🌟 Features

- **Microsoft.Agents.AI Framework** - Built on Microsoft's official .NET AI agent framework with dual agent architecture
- **Unified Chat Endpoint** - Single `/chat` endpoint automatically handles both single-agent and multi-agent conversations
- **Multi-Agent Orchestration** - Coordinate multiple AI agents with intelligent turn-based conversations
- **Flexible Response Formats** - Choose between user-friendly synthesized responses or detailed conversation logs
- **Session Management** - Persistent conversation history across requests with AgentThread support
- **Agent Auto-Selection** - Automatic agent selection based on query intent when no agents specified
- **Template System** - Pre-configured chat templates for common single and multi-agent scenarios
- **Azure AI Integration** - Seamless integration with Azure AI Foundry and Azure OpenAI
- **Interactive Frontend** - React-based UI with voice input/output, markdown rendering, and real-time chat
- **RESTful API** - Well-documented API with Swagger UI and comprehensive .http test collection

## 🗺️ Architecture Diagrams

### High-Level System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        UI[React Frontend<br/>Chat UI, Voice I/O]
        HTTP[REST Clients<br/>Swagger, .http Tests]
    end

    subgraph API["ASP.NET Core API (.NET 9)"]
        subgraph Controllers
            ChatCtrl[ChatController<br/>/chat - Unified endpoint<br/>/templates<br/>/from-template<br/>/sessions]
            AgentCtrl[AgentsController<br/>/agents<br/>/agents/:name]
        end
        
        subgraph Services
            AgentSvc[AgentService<br/>Create agents<br/>Single-agent chat]
            GroupSvc[GroupChatService<br/>Multi-agent orchestration<br/>Turn-based conversations]
            SessionMgr[SessionManager<br/>History management<br/>AgentThread support]
            Formatter[ResponseFormatterService<br/>user_friendly<br/>detailed formats]
            Template[TemplateService<br/>YAML config loader]
        end
        
        subgraph Agents["Agent Layer"]
            IAgent[IAgent Interface]
            AzureOAI[AzureOpenAIAgent<br/>ChatClient-based]
            AzureFoundry[AzureAIFoundryAgent<br/>PersistentAgentsClient]
        end
    end
    
    subgraph Framework["Microsoft.Agents.AI Framework"]
        ChatClient[ChatClient<br/>Azure OpenAI SDK]
        PersistentClient[PersistentAgentsClient<br/>Azure AI Agent Service]
        AgentThread[AgentThread<br/>Conversation state]
    end
    
    subgraph Azure["Azure AI Services"]
        OpenAI[Azure OpenAI<br/>GPT-4/GPT-4o]
        Foundry[Azure AI Foundry<br/>Agent Service<br/>People Lookup<br/>Knowledge Finder]
    end

    UI --> ChatCtrl
    HTTP --> ChatCtrl
    HTTP --> AgentCtrl
    
    ChatCtrl --> AgentSvc
    ChatCtrl --> GroupSvc
    ChatCtrl --> SessionMgr
    ChatCtrl --> Template
    AgentCtrl --> AgentSvc
    
    AgentSvc --> Formatter
    GroupSvc --> Formatter
    
    AgentSvc --> IAgent
    GroupSvc --> IAgent
    IAgent --> AzureOAI
    IAgent --> AzureFoundry
    
    AzureOAI --> ChatClient
    AzureFoundry --> PersistentClient
    
    ChatClient --> OpenAI
    PersistentClient --> Foundry
    
    SessionMgr --> AgentThread
    
    style Client fill:#e1f5ff
    style API fill:#fff3e0
    style Framework fill:#f3e5f5
    style Azure fill:#e8f5e9
```

### Request Flow - Single Agent

```mermaid
sequenceDiagram
    participant Client
    participant ChatController
    participant AgentService
    participant SessionManager
    participant AzureOpenAIAgent
    participant ChatClient
    participant AzureOpenAI
    participant ResponseFormatter

    Client->>ChatController: POST /chat<br/>{message, agents:["generic_agent"]}
    ChatController->>SessionManager: GetSessionHistory(session_id)
    SessionManager-->>ChatController: conversationHistory[]
    
    ChatController->>ChatController: Check agents.Count == 1
    ChatController->>AgentService: ChatWithAgentAsync(agentName, request, history)
    
    AgentService->>AzureOpenAIAgent: ExecuteAsync(message, history)
    AzureOpenAIAgent->>ChatClient: CompleteAsync(messages)
    ChatClient->>AzureOpenAI: Chat Completion API
    AzureOpenAI-->>ChatClient: Response
    ChatClient-->>AzureOpenAIAgent: ChatCompletion
    AzureOpenAIAgent-->>AgentService: AgentResponse
    
    AgentService-->>ChatController: ChatResponse
    
    ChatController->>SessionManager: AddMessageToSession(userMessage)
    ChatController->>SessionManager: AddMessageToSession(agentMessage)
    
    ChatController->>ResponseFormatter: Format(response)
    ResponseFormatter-->>ChatController: FormattedResponse
    
    ChatController-->>Client: JSON Response<br/>{content, agent, session_id, metadata}
```

### Request Flow - Multi-Agent (Group Chat)

```mermaid
sequenceDiagram
    participant Client
    participant ChatController
    participant GroupChatService
    participant SessionManager
    participant AgentThread
    participant Agent1 as Agent 1<br/>(People Lookup)
    participant Agent2 as Agent 2<br/>(Knowledge Finder)
    participant ResponseFormatter

    Client->>ChatController: POST /chat<br/>{message, agents:["agent1","agent2"], format:"user_friendly"}
    ChatController->>SessionManager: GetSessionHistory(session_id)
    SessionManager-->>ChatController: conversationHistory[]
    
    ChatController->>ChatController: Check agents.Count > 1
    ChatController->>GroupChatService: StartGroupChatAsync(request)
    
    GroupChatService->>AgentThread: Create thread
    GroupChatService->>AgentThread: Add Agent1
    GroupChatService->>AgentThread: Add Agent2
    
    loop For max_turns
        GroupChatService->>AgentThread: InvokeAsync(message)
        
        AgentThread->>Agent1: Process turn 1
        Agent1-->>AgentThread: Response 1
        
        AgentThread->>Agent2: Process turn 2
        Agent2-->>AgentThread: Response 2
        
        alt Agent terminates
            Agent2->>AgentThread: Terminate signal
            AgentThread-->>GroupChatService: Early termination
        end
    end
    
    AgentThread-->>GroupChatService: All agent messages
    GroupChatService-->>ChatController: GroupChatResponse
    
    ChatController->>ChatController: Check format preference
    
    alt format == "user_friendly"
        ChatController->>ResponseFormatter: FormatGroupChatResponseAsync(response)
        ResponseFormatter-->>ChatController: Synthesized response
    else format == "detailed"
        ChatController->>ResponseFormatter: Return detailed with all turns
        ResponseFormatter-->>ChatController: Full conversation
    end
    
    ChatController->>SessionManager: Save all messages
    ChatController-->>Client: JSON Response<br/>(formatted based on preference)
```

### Agent Type Decision Flow

```mermaid
flowchart TD
    Start([Chat Request Received]) --> CheckAgents{Agents<br/>specified?}
    
    CheckAgents -->|No| AutoSelect[Auto-select agent<br/>based on message]
    CheckAgents -->|Yes| CountAgents{How many<br/>agents?}
    
    AutoSelect --> CountAgents
    
    CountAgents -->|1| SingleAgent[Single Agent Flow]
    CountAgents -->|>1| MultiAgent[Multi-Agent Flow]
    
    SingleAgent --> CheckAgentType{Agent<br/>Type?}
    
    CheckAgentType -->|Config-based| CreateOpenAI[Create AzureOpenAIAgent<br/>ChatClient]
    CheckAgentType -->|Foundry| CreateFoundry[Create AzureAIFoundryAgent<br/>PersistentAgentsClient]
    
    CreateOpenAI --> ExecuteSingle[Execute single chat]
    CreateFoundry --> ExecuteSingle
    
    ExecuteSingle --> FormatSingle[Format response<br/>user-friendly]
    
    MultiAgent --> CreateThread[Create AgentThread]
    CreateThread --> AddAgents[Add all agents to thread]
    AddAgents --> ExecuteGroup[Execute group chat<br/>max_turns rounds]
    
    ExecuteGroup --> CheckFormat{Response<br/>format?}
    
    CheckFormat -->|user_friendly| Synthesize[Synthesize response<br/>from all turns]
    CheckFormat -->|detailed| AllTurns[Return all agent<br/>turns with metadata]
    
    Synthesize --> SaveSession[Save to SessionManager]
    AllTurns --> SaveSession
    FormatSingle --> SaveSession
    
    SaveSession --> Return([Return JSON Response])
    
    style Start fill:#e1f5ff
    style Return fill:#e1f5ff
    style SingleAgent fill:#fff3e0
    style MultiAgent fill:#f3e5f5
    style CreateOpenAI fill:#e8f5e9
    style CreateFoundry fill:#e8f5e9
```

> **Note**: These diagrams render automatically in GitHub and VS Code (with Mermaid extension). You can also export them to PNG/SVG at [mermaid.live](https://mermaid.live) for blog posts and presentations.

## 🚀 Quick Start

### Prerequisites

- **.NET 9 SDK** - [Download](https://dotnet.microsoft.com/download/dotnet/9.0)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Azure OpenAI** or **Azure AI Foundry** account
- **VS Code** with REST Client extension (optional, for testing)

### Backend Setup

1. **Navigate to backend directory:**
   ```powershell
   cd Backend\dotnet\agentframework
   ```

2. **Configure environment variables:**
   ```powershell
   # Copy template
   cp ..\..\env.template ..\..\env
   
   # Edit env file with your Azure credentials
   # Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT
   ```

3. **Restore dependencies:**
   ```powershell
   dotnet restore
   ```

4. **Run the API:**
   ```powershell
   dotnet run
   ```

   The API will start on:
   - **HTTP**: http://localhost:8000
   - **HTTPS**: https://localhost:51038
   - **Swagger UI**: http://localhost:8000

### Frontend Setup

1. **Navigate to frontend directory:**
   ```powershell
   cd frontend
   ```

2. **Install dependencies:**
   ```powershell
   npm install
   ```

3. **Start development server:**
   ```powershell
   npm start
   ```

   The UI will open at: http://localhost:3000

## 📡 API Endpoints

### Chat Endpoint (Unified)

**POST** `/chat`

Handles both single-agent and multi-agent conversations. The `/chat` endpoint automatically routes to multi-agent orchestration when multiple agents are specified.

**Request Body:**
```json
{
  "message": "Your question here",
  "agents": ["agent1", "agent2"],        // Optional: specific agents or null for auto-route
  "session_id": "unique-session-id",     // Optional: for conversation continuity
  "max_turns": 2,                        // Optional: max turns per agent (default: 2)
  "format": "user_friendly"              // Optional: "user_friendly" or "detailed"
}
```

**Response Formats:**

#### User-Friendly Format (Default)
Returns a clean, synthesized response:
```json
{
  "content": "Synthesized answer combining all agent insights...",
  "agent": "system",
  "session_id": "session-123",
  "timestamp": "2024-10-08T10:30:00Z",
  "format": "markdown",
  "metadata": {
    "agent_count": 3,
    "primary_agent": "PolicyAgent",
    "contributing_agents": ["PolicyAgent", "HRAgent", "ManagerAgent"],
    "is_group_chat": true,
    "total_turns": 6,
    "response_type": "user_friendly"
  }
}
```

#### Detailed Format
Returns full conversation history with all agent turns:
```json
{
  "conversation_id": "session-123",
  "total_turns": 6,
  "active_participants": ["PolicyAgent", "HRAgent", "ManagerAgent"],
  "responses": [
    {
      "agent": "PolicyAgent",
      "content": "Agent's response...",
      "message_id": "msg-1",
      "is_terminated": false,
      "metadata": {
        "turn": 1,
        "agent_type": "PolicyAgent",
        "timestamp": "2024-10-08T10:30:01Z"
      }
    }
    // ... more agent responses
  ],
  "summary": "Conversation summary",
  "content": "Final response",
  "metadata": {
    "group_chat_type": "sequential",
    "agent_count": 3,
    "response_type": "detailed"
  }
}
```

### Template & Session Endpoints

- **GET** `/agents` - List all available agents
- **GET** `/health` - Health check endpoint
- **GET** `/chat/templates` - List chat templates (single & multi-agent)
- **GET** `/chat/templates/{name}` - Get specific template details
- **POST** `/chat/from-template` - Create chat session from template
- **GET** `/chat/sessions` - List active chat sessions (both single and multi-agent)
- **GET** `/messages/{sessionId}` - Get session message history
- **POST** `/reset` - Reset session history
- **DELETE** `/messages/{sessionId}` - Delete session

## 🤖 Available Agents

| Agent | Type | Purpose | Use Cases |
|-------|------|---------|-----------|
| **generic_agent** | AzureOpenAI | General-purpose assistant | Technical questions, explanations, coding help |
| **foundry_people_lookup** | AzureAIFoundry | Find people and expertise | Employee search, skill matching, team discovery |
| **foundry_knowledge_finder** | AzureAIFoundry | Document and policy search | Policy questions, documentation lookup |
| **PolicyAgent** | Config-based | HR policy expert | Leave policies, conduct rules, compliance |

> **Note:** Foundry agents require Azure AI Foundry PROJECT_ENDPOINT and agent IDs. Generic agents work with Azure OpenAI only.

## 🎨 Frontend Features

### Format Selector
Toggle between response formats in the sidebar:
- **User Friendly** - Clean, synthesized responses (markdown formatted)
- **Detailed** - Full conversation with all agent turns and metadata

### Voice Integration
- **Voice Input** - Speech-to-text for hands-free message entry
- **Voice Output** - Text-to-speech for response playback
- Pause/resume controls during playback

### Multi-Agent Configuration
- Select multiple agents from dropdown
- Adjust max turns (1-5) for conversation depth
- Visual indicators for agent participation

### Message Display
- Markdown rendering with syntax highlighting
- Turn badges showing conversation flow
- Agent attribution for each response
- Timestamps and metadata

## 🧪 Testing

### Using REST Client (VS Code)

Open `Backend/dotnet/agentframework/DotNetAgentFramework.http` and click "Send Request" above any test:

```http
### Single Agent Chat
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "What are best practices for .NET?",
  "agents": ["generic_agent"]
}

### Multi-Agent with User-Friendly Format
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "Explain our leave policy",
  "agents": ["PolicyAgent", "HRAgent"],
  "max_turns": 2,
  "format": "user_friendly"
}

### Multi-Agent with Detailed Format
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "Explain our leave policy",
  "agents": ["PolicyAgent", "HRAgent"],
  "max_turns": 2,
  "format": "detailed"
}
```

### Using Swagger UI

1. Navigate to http://localhost:8000
2. Expand `/chat` endpoint
3. Click "Try it out"
4. Modify request body
5. Click "Execute"

## 📚 Documentation

- **[Installation Guide](docs/INSTALL.md)** - Detailed setup instructions
- **[Getting Started](docs/START.md)** - Step-by-step tutorial
- **[AI Services Configuration](docs/AI_SERVICES.md)** - Azure AI setup
- **[Multi-Agent Orchestration](docs/GROUP_CHAT.md)** - Group chat guide
- **[Prompt Engineering](docs/PROMPTS.md)** - Agent instruction design

## 📧 Configuration

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
│       ├── Controllers/          # API endpoints
│       ├── Services/             # Business logic
│       ├── Models/               # Data models
│       ├── Agents/               # Agent implementations
│       ├── Configuration/        # Config models
│       └── config.yml            # Agent definitions
├── frontend/
│   └── src/
│       ├── App.js                    # Main React component
│       ├── services/                 # API clients
│       └── components/               # UI components
└── docs/                             # Documentation
```

### Key Services

- **`ChatController`** - Unified chat endpoint with format handling
- **`AgentService`** - Agent lifecycle and execution management
- **`GroupChatService`** - Multi-agent orchestration
- **`ResponseFormatterService`** - Response formatting strategies
- **`SessionManager`** - Conversation history persistence
- **`AgentInstructionsService`** - Dynamic agent instruction loading

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

## 🔐 Security

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

## 📄 License

This project is licensed under the MIT License.

## 🙋 Support

For issues, questions, or contributions:
- **GitHub Issues**: [Create an issue](https://github.com/nhcloud/agentframework-workshop/issues)
- **Documentation**: Check the `docs/` folder
- **Examples**: See `DotNetAgentFramework.http` for API examples

## 🎯 Roadmap

- [ ] Redis-backed session persistence
- [ ] Agent performance metrics dashboard
- [ ] Custom agent plugins system
- [ ] Streaming responses with SSE
- [ ] Multi-language support
- [ ] Advanced agent selection strategies
- [ ] Conversation export/import

---

Built with ❤️ using .NET 9, Microsoft.Agents.AI Framework, React, and Azure AI