# AgentGroupChat - Multi-Framework Group Chat Implementation

This directory contains complete group chat implementations for both **Semantic Kernel** and **LangChain** frameworks, providing intelligent multi-agent conversations with configurable templates, web API integration, and **enterprise-grade content safety**.

## 🚀 Features

### Core Functionality
- **Multi-Agent Conversations**: Orchestrate conversations between multiple AI agents
- **Intelligent Speaker Selection**: AI-powered participant routing
- **Configurable Templates**: Predefined scenarios for common use cases
- **Web API Integration**: RESTful endpoints for all operations
- **Session Management**: Persistent conversations across HTTP requests
- **Role-Based Participants**: Facilitators, participants, and observers
- **🛡️ Content Safety**: Automatic input validation and output filtering

### Framework-Specific Features

#### Semantic Kernel (`python_semantic_kernel/`)
- Native SK ChatCompletionAgent integration
- Azure OpenAI service configuration
- Kernel-based agent orchestration
- Service configuration management
- Integrated content safety filtering

#### LangChain (`langchain/`)
- Azure AI Chat Completions model integration
- AI-powered speaker selection algorithm
- Conversation summarization capabilities
- Advanced message routing with context awareness
- Content safety middleware integration

### 🛡️ Content Safety Integration

Both implementations include Azure AI Content Safety:
- **Input Validation**: User messages scanned before agent processing
- **Output Filtering**: Agent responses filtered before delivery
- **Configurable Thresholds**: Per-category severity controls
- **Automatic Blocking**: Unsafe content blocked with user-friendly messages
- **Monitoring**: Detailed logging of flagged content

See [`CONTENT_SAFETY.md`](CONTENT_SAFETY.md) for configuration details.

## 📁 Directory Structure

```
Backend/python/
├── sk/                             # Semantic Kernel Implementation
│   ├── agents/
│   │   └── agent_group_chat.py     # SemanticKernelAgentGroupChat
│   ├── services/
│   │   └── content_safety_service.py # Content Safety Service
│   ├── group_chat_config.py        # Configuration loader
│   ├── example_template_usage.py   # Usage examples
│   ├── config.yml                  # Templates and settings
│   └── main.py                     # FastAPI with group chat endpoints
└── langchain/                      # LangChain Implementation  
    ├── agents/
    │   └── agent_group_chat.py     # LangChainAgentGroupChat
    ├── services/
    │   └── content_safety_service.py # Content Safety Service
    ├── group_chat_config.py        # Configuration loader
    ├── example_template_usage.py   # Usage examples  
    ├── config.yml                  # Templates and settings
    └── main.py                     # FastAPI with group chat endpoints
```

## 🛠️ Configuration Templates

Both implementations include predefined templates in `config.yml`:

### Available Templates
- **product_team**: Product Manager, Developer, Designer collaboration
- **technical_review**: Architect, Security Expert, DevOps Engineer review
- **marketing_team**: Marketing Manager, Content Creator, Analyst strategy
- **technical_architecture**: Solution Architect, Platform Engineer, Security Architect
- **customer_support**: Support Lead, Technical Specialist, Escalation Manager
- **data_science**: Data Scientist, ML Engineer, Data Analyst pipeline

### Template Structure
```yaml
group_chats:
  templates:
    product_team:
      name: "Product Development Team"
      description: "Collaborative product planning and development"
      max_turns: 15
      auto_select_speaker: true
      participants:
        - name: "Product Manager"
          role: "facilitator"
          priority: 3
          instructions: "Lead product strategy and requirements gathering..."
        - name: "Developer"
          role: "participant"
          priority: 2
          instructions: "Provide technical implementation perspective..."
```

## 🌐 Web API Endpoints

Both frameworks expose identical REST API endpoints:

### Group Chat Operations
- `POST /group-chat` - Send message to group chat
- `POST /group-chat/create` - Create new group chat session
- `GET /group-chats` - List all active group chats
- `POST /group-chat/{session_id}/reset` - Reset conversation history
- `DELETE /group-chat/{session_id}` - Delete group chat session

### Template Management
- `GET /group-chat/templates` - List available templates
- `GET /group-chat/templates/{template_name}` - Get template details
- `POST /group-chat/from-template` - Create group chat from template

### Example API Usage
```bash
# List templates
curl http://localhost:8000/group-chat/templates

# Create from template
curl -X POST http://localhost:8000/group-chat/from-template \
  -H "Content-Type: application/json" \
  -d '{"template_name": "product_team"}'

# Send message
curl -X POST http://localhost:8000/group-chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Let's discuss the new feature requirements",
    "session_id": "your-session-id"
  }'
```

## 💻 Usage Examples

### 1. Using Templates (Recommended)
```python
from group_chat_config import get_config_loader
from agents.agent_group_chat import SemanticKernelAgentGroupChat

# Load configuration
config_loader = get_config_loader()

# Create from template
group_chat_config = config_loader.create_group_chat_config("product_team")
group_chat = SemanticKernelAgentGroupChat(config=group_chat_config)

# Get participants from template
participants_config = config_loader.get_template_participants("product_team")
```

### 2. Custom Configuration
```python
from agents.agent_group_chat import GroupChatConfig, LangChainAgentGroupChat

# Create custom config
config = GroupChatConfig(
    name="Custom Discussion",
    description="A specialized team discussion",
    max_turns=10,
    auto_select_speaker=True
)

group_chat = LangChainAgentGroupChat(config=config)
```

### 3. Adding Participants
```python
from agents.agent_group_chat import GroupChatParticipant, GroupChatRole

participant = GroupChatParticipant(
    name="Expert Analyst",
    agent=your_agent_instance,
    role=GroupChatRole.PARTICIPANT,
    priority=2,
    max_consecutive_turns=3
)

group_chat.add_participant(participant)
```

## 🚀 Getting Started

### 1. Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp env.template .env
# Edit .env with your Azure OpenAI credentials
```

### 2. Run Examples
```bash
# Semantic Kernel examples
cd Backend/python/sk
python example_template_usage.py

# LangChain examples  
cd Backend/python/langchain
python example_template_usage.py
```

### 3. Start Web API
```bash
# Semantic Kernel API (port 8001)
cd Backend/python/sk
python main.py

# LangChain API (port 8000)
cd Backend/python/langchain  
python main.py
```

## 🔧 Configuration

### Environment Variables
```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure AI Foundry (for LangChain)
AZURE_AI_PROJECT_CONNECTION_STRING=your_connection_string
```

### Custom Templates
Add new templates to `config.yml`:
```yaml
group_chats:
  templates:
    your_template:
      name: "Your Custom Template"
      description: "Description of your use case"
      max_turns: 10
      auto_select_speaker: true
      participants:
        - name: "Role 1"
          role: "facilitator"
          priority: 3
          instructions: "Detailed instructions for this role..."
```
## 🛡️ Content Safety Configuration

Enable content safety for group chats by adding to your `.env`:

```env
# Azure Content Safety
CONTENT_SAFETY_ENABLED=true
CONTENT_SAFETY_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
CONTENT_SAFETY_API_KEY=your-api-key-here
CONTENT_SAFETY_SEVERITY_THRESHOLD=4
CONTENT_SAFETY_BLOCK_UNSAFE_INPUT=true
CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT=true
```

### How It Works in Group Chat

```
User Message
    ↓
[Content Safety Check] ← Block if unsafe
    ↓ (if safe)
Agent 1 Response
    ↓
[Content Safety Filter] ← Filter if unsafe
    ↓
Agent 2 Response
    ↓
[Content Safety Filter] ← Filter if unsafe
    ↓
Combined Response
```

### Benefits

✅ **Multi-layer Protection**: Each agent response is filtered individually
✅ **Graceful Degradation**: Unsafe responses replaced with safe messages
✅ **Audit Trail**: All flagged content logged for review
✅ **User Experience**: Clear, respectful error messages

## 📚 Next Steps

1. **Test the implementations**: Run the example files
2. **Try the web APIs**: Use the REST endpoints
3. **Create custom templates**: Add your own scenarios
4. **Integrate with your app**: Use the provided classes in your application
5. **Extend functionality**: Add new participant roles or conversation patterns

Both implementations are production-ready and can be used as complete working examples or integrated into larger applications. Choose the framework that best fits your existing architecture and AI service preferences.
