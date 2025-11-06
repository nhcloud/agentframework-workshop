# Rate Limiting & Performance Guide

## ⚠️ Azure OpenAI Rate Limits

### Problem
When selecting **multiple agents simultaneously** (5+ agents), you may encounter:
```
Rate limit is exceeded. Try again in 10 seconds.
```

### Why This Happens
- **GroupChat Manager** makes LLM calls to select agents
- **Each selected agent** makes its own LLM calls
- **Synthesis** makes additional LLM calls
- All happening in parallel → **Rate limit exceeded**

---

## ✅ Solutions Implemented

### 1. **Automatic Retry with Exponential Backoff** ✨
```python
# In workflow_orchestration_service.py
max_retries = 3
retry_delay = 10  # seconds

# Automatically retries with increasing delays:
# - Attempt 1: immediate
# - Attempt 2: wait 10 seconds
# - Attempt 3: wait 20 seconds
```

**What it does**: Automatically retries failed requests due to rate limiting.

---

### 2. **Max Rounds Limit**
```python
.with_max_rounds(5)  # Limits workflow iterations
```

**What it does**: Prevents infinite loops and excessive API calls.

---

## 💡 Best Practices

### For Users - Query Design

#### ❌ **Don't Do This** (Triggers All 5 Agents)
```
"I need: Udai's contact, vacation policy, Tor setup, restaurant recommendations, 
and travel tips"
```
**Result**: All 5 agents selected → Rate limit likely

---

#### ✅ **Do This Instead** (Target 2-3 Agents)

**Option 1: Split into multiple queries**
```
Query 1: "Get Udai's contact and suggest restaurants near his office"
→ 2 agents: people_lookup + generic_agent

Query 2: "What's the vacation policy and how do I set up Tor?"
→ 2 agents: bedrock_agent + knowledge_finder
```

**Option 2: Focus on primary need**
```
Query: "Get Udai's contact information"
→ 1 agent: people_lookup
```

**Option 3: Use specific agent selection**
```
Query: "Check the storage encryption requirements"
→ 1 agent: knowledge_finder
```

---

## 🔧 Rate Limit Configuration

### Azure OpenAI Quotas
Check your current limits in Azure Portal:
```
Azure OpenAI → Your Resource → Quotas and Limits
```

Typical limits:
- **Free Tier**: 3 requests/minute, 20K tokens/minute
- **Standard**: 60 requests/minute, 240K tokens/minute
- **Enterprise**: Higher limits (configurable)

---

## 📊 Query Complexity Guidelines

| Agents Selected | Rate Limit Risk | Recommendation |
|----------------|-----------------|----------------|
| 1 agent | ✅ Low | Safe to use |
| 2-3 agents | ⚠️ Medium | Usually fine, monitor |
| 4-5 agents | ⚠️ High | May hit limits |
| 5+ agents | ❌ Very High | Avoid or split query |

---

## 🛠️ If You Still Hit Rate Limits

### Quick Fixes:

1. **Wait and Retry**
   - System automatically retries with backoff
   - Manual retry after 10-30 seconds

2. **Reduce Max Rounds**
   ```python
   # In workflow_orchestration_service.py
   .with_max_rounds(3)  # Reduce from 5 to 3
   ```

3. **Upgrade Azure OpenAI Tier**
   - Move from Free to Standard
   - Request quota increase in Azure Portal

4. **Use Agent-Specific Endpoints**
   - Instead of GroupChat, call specific agent directly:
   ```
   POST /agents/people_lookup/chat
   ```

---

## 📈 Monitoring Rate Limits

### Check Current Usage
```bash
# Azure CLI
az cognitiveservices account list-usage \
  --name <your-openai-resource> \
  --resource-group <your-rg>
```

### Logs to Watch
```
2025-11-05 13:13:15 - agent_framework.azure - ERROR - 
  Error processing stream: Rate limit is exceeded. Try again in 10 seconds.
```

---

## 🎯 Optimal Query Patterns

### Pattern 1: Single Focus
```
"What's the vacation policy?"
→ bedrock_agent only
→ Fast, no rate limit issues
```

### Pattern 2: Related Tasks
```
"Get John's email and his office location"
→ people_lookup only
→ One agent handles both
```

### Pattern 3: Multi-Step (Best for Complex)
```
Step 1: "Get Udai's contact"
→ people_lookup

Step 2: "Based on Seattle office, suggest restaurants"
→ generic_agent
```

---

## 🔄 Retry Strategy Details

```python
# Implemented in workflow_orchestration_service.py

Attempt 1: Execute immediately
    ↓ (fails with rate limit)
    
Attempt 2: Wait 10 seconds, retry
    ↓ (fails with rate limit)
    
Attempt 3: Wait 20 seconds, retry
    ↓ (fails with rate limit)
    
User-friendly error message displayed
```

---

## 💬 User-Friendly Error Messages

When rate limit is exhausted after retries:

```
⚠️ Azure OpenAI rate limit exceeded. Too many agents selected simultaneously.

Please try:
1. Simplifying your query to target fewer agents
2. Waiting a few seconds before retrying
3. Breaking your request into smaller parts
```

---

## 🚀 Future Improvements

### Possible Enhancements:
1. **Request Queuing**: Queue requests and process sequentially
2. **Agent Pooling**: Reuse agent instances across requests
3. **Caching**: Cache common queries
4. **Load Balancing**: Distribute across multiple Azure OpenAI instances
5. **Rate Limit Prediction**: Warn users before hitting limits

---

## 📝 Summary

**Current Implementation**:
- ✅ Automatic retry (3 attempts)
- ✅ Exponential backoff
- ✅ User-friendly error messages
- ✅ Max rounds limit (5)

**Best Practice**:
- Target 2-3 agents per query
- Split complex queries into multiple simpler ones
- Monitor Azure OpenAI quotas
- Upgrade tier if hitting limits frequently

**Your system is now resilient to rate limits and will automatically retry!** 🎉
