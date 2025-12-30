using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Services;
using DotNetAgentFramework.Agents.Tools;
using Microsoft.Extensions.AI;
using OpenTelemetry.Trace;
using System.ClientModel;
using System.Diagnostics;
using System.Text.Json;

namespace DotNetAgentFramework.Agents;

/// <summary>
/// Azure OpenAI Generic Agent - Default agent for general-purpose conversations with WeatherTool
/// Supports dynamic tool injection for MCP tools via RespondWithToolsAsync
/// </summary>
public class AzureOpenAIGenericAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, bool enableMemory = false, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private readonly AzureAIConfig? _azureConfig = azureConfig?.Value;
    private Microsoft.Agents.AI.AIAgent? _agent;
    private IChatClient? _baseChatClient;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();
    private readonly Dictionary<string, JsonElement> _memoryStates = new();
    private readonly WeatherTool _weatherTool = new();
    private AIFunction? _weatherFunction;

    public override string Name => "azure_openai_agent";
    public override string Description => _instructionsService.GetDescription("azure_openai_agent");
    public override string Instructions => _instructionsService.GetInstructions("azure_openai_agent");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("AzureOpenAIGenericAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("memory.enabled", enableMemory);
        activity?.SetTag("tools.enabled", true);

        await base.InitializeAsync();

        EnableLongRunningMemory = enableMemory;

        try
        {
            await InitializeAzureOpenAIAgentAsync();
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize Azure OpenAI Generic Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }

    private Task InitializeAzureOpenAIAgentAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? _azureConfig?.AzureOpenAI?.Endpoint;
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? _azureConfig?.AzureOpenAI?.ApiKey;
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME") ?? _azureConfig?.AzureOpenAI?.DeploymentName ?? "gpt-4o";

        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey))
        {
            throw new InvalidOperationException("Azure OpenAI endpoint and API key are required for Azure OpenAI Generic Agent");
        }

        var azureClient = new AzureOpenAIClient(new Uri(endpoint), new ApiKeyCredential(apiKey));
        var chatClient = azureClient.GetChatClient(deploymentName);
        
        _baseChatClient = chatClient.AsIChatClient();
        _weatherFunction = AIFunctionFactory.Create(_weatherTool.GetWeather);

        if (EnableLongRunningMemory)
        {
            _logger.LogInformation("Initializing Azure OpenAI Generic Agent with UserInfoMemory and WeatherTool for long-running memory support");

            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentOptions
            {
                Instructions = Instructions,
                AIContextProviderFactory = ctx => new UserInfoMemory(
                    _baseChatClient,
                    ctx.SerializedState,
                    ctx.JsonSerializerOptions)
            };

            _agent = _baseChatClient.CreateAIAgent(
                instructions: Instructions,
                name: Name,
                description: Description,
                tools: [_weatherFunction]);
        }
        else
        {
            _logger.LogInformation("Initializing Azure OpenAI Generic Agent with WeatherTool without memory");
            
            _agent = _baseChatClient.CreateAIAgent(
                instructions: Instructions,
                name: Name,
                description: Description,
                tools: [_weatherFunction]);
        }

        _logger.LogInformation("Initialized Azure OpenAI Generic Agent with Azure OpenAI deployment: {DeploymentName} (Memory: {MemoryEnabled}, Tools: WeatherTool)",
            deploymentName, EnableLongRunningMemory);
        return Task.CompletedTask;
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        return await RespondWithToolsAsync(message, null, conversationHistory, context);
    }

    /// <summary>
    /// Respond with additional dynamic tools. The LLM decides when to call tools.
    /// </summary>
    public override async Task<string> RespondWithToolsAsync(string message, IEnumerable<AIFunction>? additionalTools = null, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("AzureOpenAIGenericAgent.RespondWithTools", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("memory.enabled", EnableLongRunningMemory);
        activity?.SetTag("message.length", message.Length);
        activity?.SetTag("additional.tools.count", additionalTools?.Count() ?? 0);

        if (_baseChatClient == null)
        {
            await InitializeAsync();
        }

        if (_baseChatClient == null)
        {
            throw new InvalidOperationException("Azure OpenAI Generic Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with Azure OpenAI Generic Agent (Memory: {MemoryEnabled}, Additional Tools: {ToolCount})", 
                EnableLongRunningMemory, additionalTools?.Count() ?? 0);

            // Combine built-in tools with additional tools
            var allTools = new List<AIFunction>();
            if (_weatherFunction != null)
            {
                allTools.Add(_weatherFunction);
            }
            if (additionalTools != null)
            {
                allTools.AddRange(additionalTools);
            }

            _logger.LogInformation("Total tools available to LLM: {Count}", allTools.Count);

            // If we have additional tools, use FunctionInvokingChatClient for dynamic tool calling
            if (additionalTools?.Any() == true)
            {
                return await RespondWithDynamicToolsAsync(message, allTools, conversationHistory, context);
            }

            // Use the standard agent if no additional tools
            var thread = GetOrCreateThread(conversationHistory);

            var chatOptions = new ChatOptions { MaxOutputTokens = 2000 };
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(chatOptions);

            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            var result = await _agent!.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the Azure OpenAI Generic Agent.";

            _logger.LogInformation("Azure OpenAI Generic Agent generated response: {ResponseLength} characters", responseText.Length);

            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);

            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with Azure OpenAI Generic Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            return $"I encountered an error while processing your request: {ex.Message}";
        }
    }

    /// <summary>
    /// Handle responses with dynamic tools using FunctionInvokingChatClient.
    /// </summary>
    private async Task<string> RespondWithDynamicToolsAsync(string message, IList<AIFunction> tools, List<GroupChatMessage>? conversationHistory, string? context)
    {
        _logger.LogInformation("Creating dynamic agent with {ToolCount} tools for LLM-driven function calling", tools.Count);

        // Build the conversation messages
        var chatMessages = new List<ChatMessage>();
        
        var systemPrompt = Instructions;
        if (!string.IsNullOrEmpty(context))
        {
            systemPrompt += $"\n\nAdditional Context: {context}";
        }
        chatMessages.Add(new ChatMessage(ChatRole.System, systemPrompt));

        if (conversationHistory != null && conversationHistory.Any())
        {
            foreach (var historyMessage in conversationHistory.OrderBy(m => m.Timestamp))
            {
                var role = historyMessage.Agent == "user" ? ChatRole.User : ChatRole.Assistant;
                chatMessages.Add(new ChatMessage(role, historyMessage.Content));
            }
        }

        chatMessages.Add(new ChatMessage(ChatRole.User, message));

        // Create FunctionInvokingChatClient with tools
        var functionInvokingClient = new FunctionInvokingChatClient(_baseChatClient!);

        // Configure chat options with tools (cast AIFunction to AITool)
        var chatOptions = new ChatOptions
        {
            MaxOutputTokens = 2000,
            Tools = tools.Cast<AITool>().ToList()
        };

        try
        {
            // Use GetService pattern for completing with function invocation
            var response = await functionInvokingClient.GetResponseAsync(chatMessages, chatOptions);
            
            var responseText = response.Text ?? "I apologize, but I couldn't generate a response.";

            _logger.LogInformation("Dynamic tool calling completed, response: {Length} chars", responseText.Length);

            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in dynamic tool calling");
            throw;
        }
    }

    private Microsoft.Agents.AI.AgentThread GetOrCreateThread(List<GroupChatMessage>? conversationHistory)
    {
        var threadKey = "default";
        if (conversationHistory != null && conversationHistory.Any())
        {
            threadKey = $"conv_{conversationHistory.First().MessageId}";
        }

        if (!_threadCache.TryGetValue(threadKey, out var thread))
        {
            thread = _agent!.GetNewThread();
            _threadCache[threadKey] = thread;
            _logger.LogDebug("Created new thread for key: {ThreadKey}", threadKey);
        }

        return thread;
    }

    public async ValueTask DisposeAsync()
    {
        _threadCache.Clear();
        _memoryStates.Clear();

        _logger.LogDebug("Azure OpenAI Generic Agent cleanup completed");
    }
}
