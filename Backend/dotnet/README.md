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

    Client->>ChatController: POST /chat<br/>{message, agents:["azure_openai_agent"]}
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

### Service Interaction Diagram

```mermaid
graph LR
    subgraph Controllers
        CC[ChatController]
        AC[AgentsController]
    end
    
    subgraph CoreServices["Core Services"]
        AS[AgentService]
        GCS[GroupChatService]
        SM[SessionManager]
    end
    
    subgraph UtilityServices["Utility Services"]
        RFS[ResponseFormatterService]
        GTS[GroupChatTemplateService]
        AIS[AgentInstructionsService]
    end
    
    subgraph AgentLayer["Agent Implementations"]
        AOA[AzureOpenAIAgent]
        AFA[AzureAIFoundryAgent]
    end
    
    CC -->|Single agent| AS
    CC -->|Multi agent| GCS
    CC -->|Load history| SM
    CC -->|Format response| RFS
    CC -->|Get template| GTS
    
    AC -->|Get agents| AS
    
    AS -->|Load config| AIS
    AS -->|Create| AOA
    AS -->|Create| AFA
    AS -->|Format| RFS
    
    GCS -->|Create| AOA
    GCS -->|Create| AFA
    GCS -->|Save history| SM
    GCS -->|Format| RFS
    
    GTS -->|Load config| AIS
    
    style Controllers fill:#e1f5ff
    style CoreServices fill:#fff3e0
    style UtilityServices fill:#f3e5f5
    style AgentLayer fill:#e8f5e9
```

### Data Flow - Session Management

```mermaid
flowchart TD
    Request[Chat Request] --> LoadHistory{Has<br/>session_id?}
    
    LoadHistory -->|Yes| GetHistory[SessionManager<br/>GetSessionHistory]
    LoadHistory -->|No| NewSession[Generate new<br/>session_id]
    
    GetHistory --> History[Load conversation<br/>history from memory]
    History --> FilterHistory[Filter relevant<br/>messages by agent]
    
    NewSession --> EmptyHistory[Empty history array]
    EmptyHistory --> FilterHistory
    
    FilterHistory --> ProcessChat[Process chat<br/>with history context]
    
    ProcessChat --> SaveUser[Save user message<br/>to session]
    SaveUser --> SaveAgent[Save agent response<br/>to session]
    
    SaveAgent --> UpdateMeta[Update session<br/>metadata]
    UpdateMeta --> Return[Return response<br/>with session_id]
    
    style Request fill:#e1f5ff
    style History fill:#fff3e0
    style ProcessChat fill:#f3e5f5
    style Return fill:#e8f5e9
```

### Response Format Transformation

```mermaid
flowchart TD
    GroupResponse[Group Chat Response<br/>Multiple agent messages] --> CheckFormat{Format<br/>parameter?}
    
    CheckFormat -->|user_friendly<br/>or not specified| UF[User-Friendly Path]
    CheckFormat -->|detailed| DF[Detailed Path]
    
    UF --> Analyze[Analyze all agent<br/>responses]
    Analyze --> Synthesize[Synthesize coherent<br/>combined response]
    Synthesize --> AddMeta1[Add metadata:<br/>- primary_agent<br/>- contributing_agents<br/>- agent_count]
    AddMeta1 --> UFResponse[Single content response<br/>Clean & user-facing]
    
    DF --> ExtractTurns[Extract all turns<br/>with full details]
    ExtractTurns --> AddMeta2[Add metadata:<br/>- total_turns<br/>- active_participants<br/>- terminated_agents]
    AddMeta2 --> DFResponse[Array of responses<br/>Full conversation log]
    
    UFResponse --> Client[Client receives<br/>formatted response]
    DFResponse --> Client
    
    style GroupResponse fill:#e1f5ff
    style UF fill:#fff3e0
    style DF fill:#f3e5f5
    style Client fill:#e8f5e9
```

### Component Dependency Graph

```mermaid
graph TD
    Program[Program.cs<br/>Startup & DI] --> Controllers
    Program --> Services
    Program --> Config[Configuration]
    
    Controllers[ChatController<br/>AgentsController] --> Services
    
    Services[AgentService<br/>GroupChatService<br/>SessionManager<br/>ResponseFormatterService<br/>TemplateService] --> Agents
    
    Agents[AzureOpenAIAgent<br/>AzureAIFoundryAgent] --> Framework[Microsoft.Agents.AI]
    
    Framework --> Azure[Azure OpenAI<br/>Azure AI Foundry]
    
    Config --> Services
    Config[config.yml<br/>.env<br/>appsettings.json] --> Agents
    
    style Program fill:#e1f5ff
    style Controllers fill:#fff3e0
    style Services fill:#f3e5f5
    style Agents fill:#ffe0b2
    style Framework fill:#f8bbd0
    style Azure fill:#e8f5e9
```

> **Note**: These diagrams render automatically in GitHub and VS Code (with Mermaid extension). You can also export them to PNG/SVG at [mermaid.live](https://mermaid.live) for blog posts and presentations.

## 🚀 Quick Start

### Prerequisites

- **.NET 9 SDK** - [Download](https://dotnet.microsoft.com/download/dotnet/9.0)
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
   ```

3. **Configure Azure credentials in `.env`:**
   ```env
   # Azure OpenAI Configuration (Required)
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   AZURE_OPENAI_API_KEY=your-api-key-here
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-10-21

   # Azure AI Foundry Configuration (Optional)
   PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
   PEOPLE_AGENT_ID=asst_xxxxx
   KNOWLEDGE_AGENT_ID=asst_xxxxx
   ```

4. **Build and run:**
   ```bash
   dotnet restore
   dotnet build
   dotnet run --urls http://localhost:8000
   ```

5. **Access the API:**
   - Swagger UI: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - Agent List: http://localhost:8000/agents

## 🤖 Available Agents

| Agent | Type | Specialization | Use Cases |
|-------|------|----------------|-----------|
| **azure_openai_agent** | AzureOpenAI | General-purpose assistant | Technical questions, explanations, coding help |
| **foundry_ms_foundry_people_agent** | AzureAIFoundry | Find people and expertise | Employee search, skill matching, team discovery |
| **foundry_knowledge_finder** | AzureAIFoundry | Document and policy search | Policy questions, documentation lookup |

> **Note:** Foundry agents require Azure AI Foundry PROJECT_ENDPOINT and agent IDs. Generic agents work with Azure OpenAI only.

## 📡 API Endpoints

### Unified Chat Endpoint

The `/chat` endpoint automatically handles both single-agent and multi-agent conversations based on the `agents` array.

```http
POST /chat
Content-Type: application/json

{
  "message": "What are the best practices for .NET development?",
  "agents": ["azure_openai_agent"],              // Optional: defaults to auto-select
  "format": "user_friendly",                // Optional: "user_friendly" | "detailed"
  "session_id": "user-session-123",        // Optional: for conversation history
  "max_turns": 3                           // Optional: for multi-agent (default: 2-3)
}
```

#### Single Agent Request
```json
{
  "message": "Explain async/await in C#",
  "agents": ["azure_openai_agent"],
  "session_id": "user123"
}
```

#### Multi-Agent Request (Automatic Group Chat)
```json
{
  "message": "Who are the ML experts and what resources do we have?",
  "agents": ["foundry_ms_foundry_people_agent", "foundry_knowledge_finder"],
  "format": "detailed",
  "max_turns": 2
}
```

### Template Endpoints

```http
# Get available chat templates
GET /chat/templates

# Get specific template details
GET /chat/templates/{templateName}

# Create chat from template
POST /chat/from-template
{
  "template_name": "comprehensive_inquiry"
}

# Get active chat sessions
GET /chat/sessions
```

### Agent Management

```http
# Get all available agents
GET /agents

# Get specific agent details
GET /agents/{agentName}
```

## 📤 Response Formats

### User-Friendly Format (Default)
Synthesized, clean response optimized for end users:

```json
{
  "content": "Based on the expertise search and knowledge base, here are the ML experts...",
  "agent": "system",
  "session_id": "user123",
  "timestamp": "2024-01-15T10:30:00Z",
  "format": "user_friendly",
  "metadata": {
    "agent_count": 2,
    "primary_agent": "foundry_ms_foundry_people_agent",
    "contributing_agents": ["foundry_ms_foundry_people_agent", "foundry_knowledge_finder"],
    "is_group_chat": true,
    "total_turns": 4,
    "response_type": "user_friendly",
    "agent_framework": true
  }
}
```

### Detailed Format
Full conversation with all agent turns and metadata:

```json
{
  "conversation_id": "user123",
  "total_turns": 4,
  "active_participants": ["foundry_ms_foundry_people_agent", "foundry_knowledge_finder"],
  "responses": [
    {
      "agent": "foundry_ms_foundry_people_agent",
      "content": "I found 5 ML experts in the organization...",
      "message_id": "msg-001",
      "is_terminated": false,
      "metadata": {
        "turn": 1,
        "agent_type": "AzureAIFoundry",
        "timestamp": "2024-01-15T10:30:00Z",
        "terminated": false
      }
    },
    {
      "agent": "foundry_knowledge_finder",
      "content": "We have extensive ML documentation including...",
      "message_id": "msg-002",
      "is_terminated": true,
      "metadata": {
        "turn": 2,
        "agent_type": "AzureAIFoundry",
        "timestamp": "2024-01-15T10:30:02Z",
        "terminated": true
      }
    }
  ],
  "summary": "Combined findings from expertise search and knowledge base",
  "content": "Combined findings from expertise search and knowledge base",
  "metadata": {
    "group_chat_type": "RoundRobinGroupChat",
    "agent_count": 2,
    "agents_used": ["foundry_ms_foundry_people_agent", "foundry_knowledge_finder"],
    "max_turns_used": 2,
    "agent_framework": true,
    "early_termination": false,
    "terminated_agents": ["foundry_knowledge_finder"],
    "response_type": "detailed",
    "conversation_length": 0
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
PEOPLE_AGENT_ID=asst_8tcAIexm3X8k6dQVbuQo4vRV
KNOWLEDGE_AGENT_ID=asst_pAqWN6pRcu67JqPZ4BiZis0o
MANAGED_IDENTITY_CLIENT_ID=your-managed-identity-id

# Application Settings
FRONTEND_URL=http://localhost:3001
```

### Agent Configuration (`config.yml`)

```yaml
agents:
  - name: azure_openai_agent
    model: gpt-4o
    temperature: 0.7
    max_tokens: 1500
    instructions: |
      You are a helpful AI assistant specialized in software development...

  - name: foundry_ms_foundry_people_agent
    type: foundry
    agent_id: ${PEOPLE_AGENT_ID}
    description: Finds people and expertise within the organization

  - name: foundry_knowledge_finder
    type: foundry
    agent_id: ${KNOWLEDGE_AGENT_ID}
    description: Searches documentation and knowledge base
```

## 🛠️ Development

### Project Structure

```
Backend/dotnet/
├── Controllers/
│   ├── ChatController.cs          # Unified chat endpoint (single + multi-agent)
│   └── AgentsController.cs        # Agent information endpoints
├── Services/
│   ├── AgentService.cs            # Agent creation and single-agent chat
│   ├── IAgentService.cs           # Interface
│   ├── GroupChatService.cs        # Multi-agent orchestration
│   ├── IGroupChatService.cs       # Interface
│   ├── SessionManager.cs          # Conversation history with AgentThread
│   ├── ISessionManager.cs         # Interface (implicit)
│   ├── ResponseFormatterService.cs # Format handling (user_friendly/detailed)
│   ├── IResponseFormatterService.cs # Interface (implicit)
│   ├── GroupChatTemplateService.cs # Template management
│   ├── IGroupChatTemplateService.cs # Interface
│   └── AgentInstructionsService.cs # Dynamic agent configuration
├── Agents/
│   ├── BaseAgent.cs               # IAgent, AzureOpenAIAgent, AzureAIFoundryAgent
│   └── SpecificAgents.cs          # Legacy agent implementations (deprecated)
├── Models/
│   └── ChatModels.cs              # Request/response models
├── Configuration/
│   ├── AzureAIConfig.cs           # Azure configuration models
│   └── AgentConfig.cs             # Agent configuration models
├── Program.cs                      # ASP.NET Core setup and DI
├── config.yml                      # Agent definitions
├── .env                            # Environment variables (Azure credentials)
└── DotNetAgentFramework.http      # REST Client test collection
```

### Key Services & Interfaces

| Service | Interface | Responsibility |
|---------|-----------|----------------|
| **AgentService** | IAgentService | Agent creation, single-agent chat, agent lookup |
| **GroupChatService** | IGroupChatService | Multi-agent orchestration, turn-based conversations |
| **SessionManager** | ISessionManager | Conversation history, AgentThread management |
| **ResponseFormatterService** | IResponseFormatterService | Format selection and response transformation |
| **GroupChatTemplateService** | IGroupChatTemplateService | Template loading and management |
| **AgentInstructionsService** | - | Dynamic agent instruction loading from YAML |

### Microsoft.Agents.AI Framework Components

- **`IAgent`** - Base interface for all agents
- **`AzureOpenAIAgent`** - Standard agents using ChatClient (Azure OpenAI)
- **`AzureAIFoundryAgent`** - Enterprise agents using PersistentAgentsClient (Azure AI Foundry)
- **`AgentThread`** - Stateful conversation thread management
- **`ChatClientAgent`** - Agent execution wrapper
- **`PersistentAgentsClient`** - Azure AI Foundry agent client

## 🔍 Testing

### REST Client Testing (`DotNetAgentFramework.http`)

The workspace includes comprehensive API tests:

```http
# Single agent chat
POST {{baseUrl}}/chat
{
  "message": "Explain async/await",
  "agents": ["azure_openai_agent"]
}

# Multi-agent chat (user-friendly)
POST {{baseUrl}}/chat
{
  "message": "Find ML experts and relevant docs",
  "agents": ["foundry_ms_foundry_people_agent", "foundry_knowledge_finder"],
  "format": "user_friendly"
}

# Multi-agent chat (detailed)
POST {{baseUrl}}/chat
{
  "message": "Find ML experts and relevant docs",
  "agents": ["foundry_ms_foundry_people_agent", "foundry_knowledge_finder"],
  "format": "detailed"
}

# Get templates
GET {{baseUrl}}/chat/templates

# Create from template
POST {{baseUrl}}/chat/from-template
{
  "template_name": "comprehensive_inquiry"
}

# Get active sessions
GET {{baseUrl}}/chat/sessions
```

### Swagger UI

Interactive API documentation available at: http://localhost:8000

## 📊 Performance

- **Single Agent Response**: 2-5 seconds
- **Multi-Agent (2-3 agents)**: 5-15 seconds (depends on max_turns)
- **Session Persistence**: In-memory with AgentThread support
- **Concurrent Requests**: ASP.NET Core async pipeline handles multiple users
- **Timeout Configuration**: 5-minute default for AI operations

## 🔒 Security

- HTTPS enabled in production
- CORS configured for frontend origin
- API key validation for Azure services
- Session isolation per user
- Request validation and sanitization
- Environment-based configuration

## 🚦 Best Practices

### Single Agent vs Multi-Agent

**Use Single Agent When:**
- Simple Q&A
- One domain of expertise needed
- Fast response required
- Straightforward queries

**Use Multi-Agent When:**
- Multiple perspectives needed
- Cross-domain expertise required
- Complex analysis
- Collaborative problem-solving

### Format Selection

**User-Friendly Format (Default):**
- End-user facing applications
- Clean, synthesized responses
- Production UI/UX
- Mobile apps

**Detailed Format:**
- Debugging and development
- Audit trails
- Research and analysis
- Agent behavior inspection

## 📚 Documentation

- **Swagger UI**: http://localhost:8000 - Live API documentation
- **`DotNetAgentFramework.http`**: REST Client test examples
- **Health Endpoint**: http://localhost:8000/health - System status

## 🎯 Roadmap

- [ ] Redis-backed session persistence
- [ ] Streaming responses with Server-Sent Events (SSE)
- [ ] Agent performance metrics dashboard
- [ ] Custom agent plugin system
- [ ] Advanced agent selection strategies (semantic routing)
- [ ] Conversation export/import
- [ ] Multi-language support
- [ ] Agent behavior analytics

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
- **Swagger UI**: http://localhost:8000 for API exploration
- **Health Check**: http://localhost:8000/health for system status

---

Built with ❤️ using .NET 9, Microsoft.Agents.AI Framework, and Azure AI