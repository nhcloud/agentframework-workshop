# Content Safety Integration Guide

## Overview

The .NET Agent Framework includes comprehensive **Azure AI Content Safety** integration to protect your application from harmful content. This guide covers setup, configuration, and best practices for implementing content safety in your multi-agent system.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Setup](#setup)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Features

### ??? Content Monitoring

- **4 Safety Categories**: Hate, SelfHarm, Sexual, Violence
- **Severity Levels**: 0-7 scale for precise risk assessment
- **Real-time Analysis**: Both text and image content scanning
- **Custom Blocklists**: Industry-specific term blocking
- **Configurable Thresholds**: Per-category severity thresholds

### ?? Protection Layers

1. **Input Validation** - Blocks unsafe user input before agent processing
2. **Output Filtering** - Filters unsafe agent responses before delivery
3. **Automatic Blocking** - Configurable blocking with user-friendly messages
4. **Graceful Degradation** - Continues operation when safety is disabled

### ?? Monitoring & Logging

- Severity logging for flagged content
- Detailed analysis results
- Blocklist match tracking
- Category-specific severity breakdowns

## Architecture

### Content Safety Flow

```
???????????????????
?   User Input    ?
???????????????????
         ?
         ?
??????????????????????????????
? Content Safety Service     ?
? CheckUserInputAsync()      ?
?                            ?
? ? Analyze text             ?
? ? Check severity levels    ?
? ? Compare to thresholds    ?
? ? Check blocklists         ?
??????????????????????????????
         ?
    ???????????
    ?         ?
    ?         ?
[Block]   [Allow]
    ?         ?
    ?         ?
    ?   ???????????????
    ?   ?Agent Process?
    ?   ???????????????
    ?          ?
    ?          ?
    ?   ??????????????????????????????
    ?   ? Content Safety Service     ?
    ?   ? FilterOutput()             ?
    ?   ?                            ?
    ?   ? ? Analyze response         ?
    ?   ? ? Check severity levels    ?
    ?   ? ? Apply filtering action   ?
    ?   ??????????????????????????????
    ?            ?
    ?       ???????????
    ?       ?         ?
    ?       ?         ?
    ?   [Filter]  [Allow]
    ?       ?         ?
    ?       ?         ?
???????????????????????????
?   Error Message or      ?
?   Filtered Response     ?
???????????????????????????
```

### Service Integration

```csharp
public class ContentSafetyService : IContentSafetyService
{
    // Configuration
    private readonly ContentSafetyConfig? _config;
    private readonly ContentSafetyClient? _client;
    
    // Core Methods
    Task<ContentSafetyResult> AnalyzeTextAsync(string text, CancellationToken ct);
    Task<ContentSafetyResult> AnalyzeImageAsync(Stream imageStream, CancellationToken ct);
    Task<(bool allowed, string? error)> CheckUserInputAsync(string text, CancellationToken ct);
    string FilterOutput(string original, ContentSafetyResult analysis);
    bool IsSafe(ContentSafetyResult result);
}
```

### Integration Points

The Content Safety Service is called at:

1. **ChatController** - Before agent processing
2. **GroupChatService** - Multi-agent input validation
3. **AgentWorkflowService** - Workflow orchestration input/output filtering

## Setup

### 1. Create Azure Content Safety Resource

```bash
# Using Azure CLI
az cognitiveservices account create \
  --name your-content-safety-name \
  --resource-group your-resource-group \
  --kind ContentSafety \
  --sku S0 \
  --location eastus
```

Or create via Azure Portal:
1. Go to **Azure Portal**
2. Create a new **Azure AI Content Safety** resource
3. Copy the **Endpoint** and **Key**

### 2. Configure Environment Variables

Update your `.env` file:

```env
# Azure Content Safety - Required
CONTENT_SAFETY_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
CONTENT_SAFETY_API_KEY=your-api-key-here

# Master Switch
CONTENT_SAFETY_ENABLED=true

# Global threshold (0-7) - used if per-category thresholds not set
CONTENT_SAFETY_SEVERITY_THRESHOLD=4

# Per-category thresholds (use -1 to disable a category)
CONTENT_SAFETY_THRESHOLD_HATE=4
CONTENT_SAFETY_THRESHOLD_SELFHARM=4
CONTENT_SAFETY_THRESHOLD_SEXUAL=4
CONTENT_SAFETY_THRESHOLD_VIOLENCE=4

# Behavior Configuration
CONTENT_SAFETY_BLOCK_UNSAFE_INPUT=true        # Block unsafe user input
CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT=true      # Filter unsafe agent output

# Optional: Blocklists (comma-separated names from Azure Content Safety Studio)
CONTENT_SAFETY_BLOCKLISTS=myblocklist,industryterms

# Output Filtering Action (redact | placeholder | empty)
CONTENT_SAFETY_OUTPUT_ACTION=redact
CONTENT_SAFETY_PLACEHOLDER_TEXT=[Content removed due to safety policy]
```

### 3. Verify Configuration

The service automatically initializes on startup. Check logs for:

```
[INFO] Content Safety enabled at https://your-resource.cognitiveservices.azure.com/. Global threshold 4
```

Or if disabled:

```
[WARN] Content Safety not configured or disabled. Proceeding without safety checks.
```

## Configuration

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `Enabled` | bool | false | Master on/off switch |
| `Endpoint` | string | null | Azure Content Safety endpoint URL |
| `ApiKey` | string | null | Azure Content Safety API key |
| `SeverityThreshold` | int | 4 | Global default threshold (0-7) |
| `HateThreshold` | int | 4 | Hate speech threshold |
| `SelfHarmThreshold` | int | 4 | Self-harm content threshold |
| `SexualThreshold` | int | 4 | Sexual content threshold |
| `ViolenceThreshold` | int | 4 | Violence threshold |
| `BlockUnsafeInput` | bool | true | Block unsafe user input |
| `FilterUnsafeOutput` | bool | true | Filter unsafe agent output |
| `Blocklists` | string | null | Comma-separated blocklist names |
| `OutputAction` | string | "redact" | Action for unsafe output (redact/placeholder/empty) |
| `PlaceholderText` | string | "[Filtered]" | Replacement text for placeholder action |

### Severity Threshold Guide

| Level | Risk | Action | Use Case |
|-------|------|--------|----------|
| 0-1 | None | Allow | No concerns |
| 2-3 | Low | Allow + Log | Monitor usage |
| 4-5 | Medium | Block/Filter | Standard protection |
| 6-7 | High | Block/Filter | Strict protection |

### Threshold Strategies

#### Lenient (Creative Applications)
```env
CONTENT_SAFETY_SEVERITY_THRESHOLD=6
CONTENT_SAFETY_THRESHOLD_HATE=5
CONTENT_SAFETY_THRESHOLD_SELFHARM=6
CONTENT_SAFETY_THRESHOLD_SEXUAL=6
CONTENT_SAFETY_THRESHOLD_VIOLENCE=5
```

#### Balanced (Default - Enterprise)
```env
CONTENT_SAFETY_SEVERITY_THRESHOLD=4
CONTENT_SAFETY_THRESHOLD_HATE=4
CONTENT_SAFETY_THRESHOLD_SELFHARM=4
CONTENT_SAFETY_THRESHOLD_SEXUAL=4
CONTENT_SAFETY_THRESHOLD_VIOLENCE=4
```

#### Strict (Healthcare, Education, Children)
```env
CONTENT_SAFETY_SEVERITY_THRESHOLD=2
CONTENT_SAFETY_THRESHOLD_HATE=2
CONTENT_SAFETY_THRESHOLD_SELFHARM=2
CONTENT_SAFETY_THRESHOLD_SEXUAL=2
CONTENT_SAFETY_THRESHOLD_VIOLENCE=3
```

#### Disable Specific Category
```env
# Disable sexual content filtering only
CONTENT_SAFETY_THRESHOLD_SEXUAL=-1
```

## API Reference

### Scan Text

**Endpoint:** `POST /safety/scan-text`

**Request:**
```json
{
  "text": "Your text content to scan"
}
```

**Response:**
```json
{
  "isSafe": true,
  "highestSeverity": 0,
  "highestCategory": null,
  "categorySeverities": {
    "Hate": 0,
    "SelfHarm": 0,
    "Sexual": 0,
    "Violence": 0
  },
  "flaggedCategories": [],
  "blocklistMatches": []
}
```

### Scan Image

**Endpoint:** `POST /safety/scan-image`

**Request:**
```http
POST /safety/scan-image
Content-Type: multipart/form-data

file: [binary image data]
```

**Response:**
```json
{
  "isSafe": false,
  "highestSeverity": 5,
  "highestCategory": "Violence",
  "categorySeverities": {
    "Hate": 0,
    "SelfHarm": 0,
    "Sexual": 1,
    "Violence": 5
  },
  "flaggedCategories": ["Violence"]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isSafe` | bool | Overall safety status (false if any category exceeds threshold) |
| `highestSeverity` | int | Highest severity across all categories (0-7) |
| `highestCategory` | string | Category with highest severity |
| `categorySeverities` | object | Severity level for each category |
| `flaggedCategories` | array | Categories that exceeded thresholds |
| `blocklistMatches` | array | Matched items from blocklists (text only) |

## Testing

### Frontend UI Testing

The React frontend includes a dedicated **Content Safety Testing** panel:

1. Navigate to the sidebar
2. Scroll to "Content Safety Testing" section
3. Use the text scanner or image uploader
4. View real-time results with severity breakdowns

### REST Client Testing

Use the provided test collection:

```http
### Test text scanning
POST {{baseUrl}}/safety/scan-text
Content-Type: application/json

{
  "text": "I love puppies and sunshine"
}

### Test image scanning
POST {{baseUrl}}/safety/scan-image
Content-Type: multipart/form-data; boundary=boundary

--boundary
Content-Disposition: form-data; name="file"; filename="test.jpg"
Content-Type: image/jpeg

< ./test-images/safe-image.jpg
--boundary--
```

### Unit Testing Example

```csharp
[Fact]
public async Task CheckUserInputAsync_BlocksUnsafeContent()
{
    // Arrange
    var config = new AzureAIConfig
    {
        ContentSafety = new ContentSafetyConfig
        {
            Enabled = true,
            BlockUnsafeInput = true,
            SeverityThreshold = 4
        }
    };
    
    var service = new ContentSafetyService(Options.Create(config), logger);
    
    // Act
    var (allowed, error) = await service.CheckUserInputAsync("unsafe content here");
    
    // Assert
    Assert.False(allowed);
    Assert.NotNull(error);
    Assert.Contains("blocked due to unsafe content", error);
}
```

## Best Practices

### ? Do's

1. **Enable in Production** - Always enable content safety for production deployments
2. **Test Thresholds** - Test with your specific use cases to find optimal thresholds
3. **Use Blocklists** - Create custom blocklists for industry-specific terms
4. **Monitor Logs** - Review flagged content to improve safety policies
5. **Provide Feedback** - Give users clear, respectful error messages
6. **Regular Review** - Periodically review and adjust thresholds based on usage patterns
7. **Document Policies** - Maintain clear content safety policies for your users

### ? Don'ts

1. **Don't Set Too Low** - Overly strict thresholds (0-1) may block legitimate content
2. **Don't Ignore Warnings** - Review content that triggers severity 3+ even if allowed
3. **Don't Skip Testing** - Always test safety features before production deployment
4. **Don't Expose Raw Errors** - Provide user-friendly error messages, not raw API responses
5. **Don't Disable Logging** - Keep logs enabled to monitor safety patterns
6. **Don't Forget Images** - Remember to scan both text and image content

### Error Message Guidelines

**Good Error Messages:**
```
?? Your request was blocked due to content safety policies.

Reason: The content was flagged for violence.

Please rephrase your request in a respectful and appropriate manner.
```

**Bad Error Messages:**
```
Error 400: Content filter violation - severity 6
```

### Threshold Selection Guide

| Application Type | Recommended Threshold |
|-----------------|----------------------|
| Public-facing chatbot | 3-4 (balanced) |
| Internal enterprise tool | 4-5 (moderate) |
| Healthcare/medical | 2-3 (strict) |
| Education (K-12) | 2-3 (strict) |
| Creative writing tool | 5-6 (lenient) |
| Customer support | 3-4 (balanced) |

## Troubleshooting

### Common Issues

#### 1. Content Safety Not Working

**Symptom:** No content filtering despite enabled configuration

**Solutions:**
- Verify `CONTENT_SAFETY_ENABLED=true` in `.env`
- Check endpoint and API key are correct
- Ensure Azure Content Safety resource is deployed and active
- Review logs for initialization errors

#### 2. Too Much Content Blocked

**Symptom:** Legitimate content being blocked frequently

**Solutions:**
- Increase severity thresholds (e.g., from 4 to 5)
- Adjust per-category thresholds based on which categories are triggering
- Review Azure Content Safety Studio for threshold guidance
- Test specific content to understand severity levels

#### 3. Blocklist Not Working

**Symptom:** Blocklist items not being matched

**Solutions:**
- Verify blocklist name matches exactly (case-sensitive)
- Ensure blocklist is created in Azure Content Safety Studio
- Check blocklist is in the same region as your Content Safety resource
- Verify comma-separated format in configuration

#### 4. Performance Issues

**Symptom:** Slow response times with safety enabled

**Solutions:**
- Content Safety adds ~500-1000ms per request
- Consider caching results for identical content
- Use async operations properly
- Check Azure Content Safety service health

#### 5. Configuration Not Loading

**Symptom:** Settings from `.env` not being applied

**Solutions:**
- Restart the application after changing `.env`
- Verify `.env` file is in the correct directory
- Check for syntax errors in `.env` (no spaces around `=`)
- Ensure environment variables are being loaded properly

### Debug Logging

Enable detailed logging to troubleshoot issues:

```csharp
builder.Logging.AddFilter("DotNetAgentFramework.Services.ContentSafetyService", LogLevel.Debug);
```

Look for log messages like:

```
[INFO] Content Safety enabled at https://...
[WARN] Content Safety text analyze failed
[ERROR] Azure Content Safety API error: ...
```

### Testing Connectivity

Test your Azure Content Safety connection:

```bash
curl -X POST "https://your-resource.cognitiveservices.azure.com/contentsafety/text:analyze?api-version=2023-10-01" \
  -H "Ocp-Apim-Subscription-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'
```

## Advanced Configuration

### Custom Filtering Logic

Implement custom filtering by extending `ContentSafetyService`:

```csharp
public class CustomContentSafetyService : ContentSafetyService
{
    public override string FilterOutput(string original, ContentSafetyResult analysis)
    {
        if (!IsSafe(analysis))
        {
            // Custom logic: mask offensive words instead of blocking entire response
            return MaskOffensiveWords(original, analysis.FlaggedCategories);
        }
        return original;
    }
    
    private string MaskOffensiveWords(string text, List<string> categories)
    {
        // Your custom masking logic here
        return text;
    }
}
```

### Integration with Custom Agents

```csharp
public class MyCustomAgent : BaseAgent
{
    private readonly IContentSafetyService _safetyService;
    
    public override async Task<string> ExecuteAsync(string message, List<ConversationMessage>? history = null)
    {
        // Check input before processing
        var (allowed, error) = await _safetyService.CheckUserInputAsync(message);
        if (!allowed)
        {
            return error!;
        }
        
        // Process with agent
        var response = await base.ExecuteAsync(message, history);
        
        // Filter output before returning
        var safetyResult = await _safetyService.AnalyzeTextAsync(response);
        return _safetyService.FilterOutput(response, safetyResult);
    }
}
```

## Resources

- [Azure AI Content Safety Documentation](https://learn.microsoft.com/azure/ai-services/content-safety/)
- [Content Safety Studio](https://contentsafety.cognitive.azure.com/)
- [Severity Definitions](https://learn.microsoft.com/azure/ai-services/content-safety/concepts/harm-categories)
- [Blocklist Management](https://learn.microsoft.com/azure/ai-services/content-safety/how-to/use-blocklist)
- [Best Practices Guide](https://learn.microsoft.com/azure/ai-services/content-safety/concepts/best-practices)

---

**Need Help?** 
- Review logs for detailed error messages
- Test with the frontend safety testing panel
- Check Azure Content Safety service health in Azure Portal
- Verify API keys and endpoints are correct
