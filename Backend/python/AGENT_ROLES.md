# Agent Roles & Data Sources - Corrected

## 🎯 Agent Assignments (Fixed)

### **1. PeopleLookupAgent** 👥
**Purpose**: Employee directory and contact information
**Data Source**: Employee database in Azure AI Foundry
**Contains**:
- Employee names
- Email addresses
- Phone numbers
- Office locations
- Job titles
- Organizational structure

**Example Queries**:
- "Get Udai's contact information"
- "Who is the manager of engineering?"
- "Find John Smith's email"

---

### **2. BedrockAgent** 📋 (AWS Bedrock)
**Purpose**: Company policies, HR rules, workplace culture
**Data Source**: HR policies and workplace guidelines
**Contains**:
- Vacation policies
- Dress code policies
- Benefits information
- HR rules and regulations
- Workplace culture guidelines
- Employee handbook content

**Example Queries**:
- "What's the vacation policy?"
- "What are the dress code rules?"
- "Tell me about employee benefits"
- "What's the work from home policy?"

---

### **3. KnowledgeFinderAgent** 📚
**Purpose**: Technical documentation and configuration guides
**Data Source**: Technical PDFs in Azure AI Foundry vector store
**Contains**:
- **Configuration.pdf** - System configuration guides
- **Privileged Identity Management.pdf** - PIM setup and management
- **Storage Encryption.pdf** - Encryption requirements and setup
- **TorSetup.pdf** - Tor network configuration
- **Mobile App Configuration.pdf** - Mobile app setup guides

**Example Queries**:
- "How do I configure Tor?"
- "What are the storage encryption requirements?"
- "How do I set up privileged identity management?"
- "How do I configure the mobile app?"

---

### **4. GenericAgent** 💬 (Azure OpenAI)
**Purpose**: General-purpose assistant
**Model**: Azure OpenAI GPT-4
**Contains**: No specific data - uses general knowledge
**Capabilities**:
- General recommendations
- Travel suggestions
- Casual conversation
- Information not requiring specialized databases

**Example Queries**:
- "Suggest places to visit in Seattle"
- "What's the weather like today?"
- "Recommend a good restaurant"
- "Tell me a joke"

---

### **5. GeminiAgent** 🌟 (Google Gemini)
**Purpose**: General-purpose assistant (alternative to GenericAgent)
**Model**: Google Gemini 2.0 Flash
**Contains**: No specific data - uses general knowledge
**Capabilities**:
- General recommendations
- Information synthesis
- Creative responses
- Alternative general assistant

**Example Queries**:
- Same as GenericAgent
- Can be used when GenericAgent is busy
- Alternative AI model for general queries

---

## 🔄 Data Flow Diagram

```
User Query
    ↓
GroupChat Manager (LLM)
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent Selection                          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌──────────────┬───────────────┬─────────────────┬─────────────┬──────────────┐
│ PeopleLookup │ BedrockAgent  │ KnowledgeFinder │ GenericAgent│ GeminiAgent  │
│              │               │                 │             │              │
│ 👥 Employee  │ 📋 HR         │ 📚 Technical    │ 💬 General  │ 🌟 General   │
│ Directory    │ Policies      │ Docs (PDFs)     │ AI          │ AI           │
│              │               │                 │             │              │
│ Azure AI     │ AWS Bedrock   │ Azure AI        │ Azure       │ Google       │
│ Foundry      │               │ Foundry         │ OpenAI      │ Gemini       │
└──────────────┴───────────────┴─────────────────┴─────────────┴──────────────┘
    ↓
Manager Synthesizes Responses
    ↓
Final Answer to User
```

---

## 📊 Query Routing Examples

### Example 1: Employee Contact
**Query**: "Get Udai's contact information"
**Manager Selects**: `people_lookup` ✅
**Result**: Email, phone, office location

### Example 2: HR Policy
**Query**: "What's the vacation policy?"
**Manager Selects**: `bedrock_agent` ✅
**Result**: Vacation days, request process, approval workflow

### Example 3: Technical Configuration
**Query**: "How do I configure storage encryption?"
**Manager Selects**: `knowledge_finder` ✅
**Result**: Reads Storage Encryption.pdf, provides setup steps

### Example 4: Multi-Agent Query
**Query**: "Get Udai's contact and suggest places near his office"
**Manager Selects**: `people_lookup` + `generic_agent` ✅
**Result**: 
- people_lookup → "Udai is in Seattle office, email: udai@company.com"
- generic_agent → "Near Seattle: Space Needle, Pike Place Market..."
- Manager synthesizes both into coherent response

### Example 5: HR + Technical
**Query**: "What's the remote access policy and how do I set up Tor?"
**Manager Selects**: `bedrock_agent` + `knowledge_finder` ✅
**Result**:
- bedrock_agent → "Remote access requires VPN, approved by IT..."
- knowledge_finder → "Tor setup steps from TorSetup.pdf..."

---

## 🎯 Key Differences (Corrected Understanding)

| Agent | Data Source | Use Case |
|-------|------------|----------|
| **people_lookup** | Employee DB | Contact info, org structure |
| **bedrock_agent** | HR Policies | Vacation, benefits, workplace rules |
| **knowledge_finder** | Technical PDFs | Configuration guides, setup docs |
| **generic_agent** | Azure OpenAI | General questions, recommendations |
| **gemini_agent** | Google Gemini | General questions (alternative) |

---

## 🔧 Configuration Files

### Azure AI Foundry Agents (Need Agent IDs)
```env
# People Lookup Agent
PEOPLE_AGENT_ID=<your-people-agent-id>

# Knowledge Finder Agent (with PDFs)
KNOWLEDGE_AGENT_ID=<your-knowledge-agent-id>
```

### AWS Bedrock Agent
```env
# Bedrock Agent for HR Policies
AWS_BEDROCK_AGENT_ID=<your-bedrock-agent-id>
# OR use direct model
AWS_BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

### Generic Agents (No Agent ID needed)
```env
# Generic Agent (Azure OpenAI)
AZURE_OPENAI_ENDPOINT=<your-endpoint>
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment>

# Gemini Agent (Google)
GOOGLE_API_KEY=<your-api-key>
GOOGLE_GEMINI_MODEL_ID=gemini-2.0-flash
```

---

## ✅ Workflow Manager Instructions (Updated)

The manager now correctly understands:
- **people_lookup** = Employee contacts
- **bedrock_agent** = HR policies (vacation, benefits, culture)
- **knowledge_finder** = Technical PDFs (Tor, encryption, PIM)
- **generic_agent** / **gemini_agent** = General AI assistance

**This ensures the right agent is selected for each query type!** 🎯
