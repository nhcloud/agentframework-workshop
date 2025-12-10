using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Services;
using OpenTelemetry.Trace;
using System.ClientModel;
using System.Diagnostics;
using System.Text.Json;

namespace DotNetAgentFramework.Agents;

/// <summary>
/// Azure OpenAI Generic Agent - Default agent for general-purpose conversations
/// </summary>
public class AzureOpenAIGenericAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, bool enableMemory = false, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private readonly AzureAIConfig? _azureConfig = azureConfig?.Value;
    private Microsoft.Agents.AI.ChatClientAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();
    private readonly Dictionary<string, JsonElement> _memoryStates = new();

    public override string Name => "azure_openai_agent";
    public override string Description => _instructionsService.GetDescription("azure_openai_agent");

    public override string Instructions => _instructionsService.GetInstructions("azure_openai_agent");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("AzureOpenAIGenericAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("memory.enabled", enableMemory);

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
        var iChatClient = chatClient.AsIChatClient();

        if (EnableLongRunningMemory)
        {
            _logger.LogInformation("Initializing Azure OpenAI Generic Agent with UserInfoMemory for long-running memory support");

            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentOptions
            {
                Instructions = Instructions,
                AIContextProviderFactory = ctx => new UserInfoMemory(
                    iChatClient,
                    ctx.SerializedState,
                    ctx.JsonSerializerOptions)
            };

            _agent = iChatClient.CreateAIAgent(agentOptions);
        }
        else
        {
            _logger.LogInformation("Initializing Azure OpenAI Generic Agent without memory");
            _agent = iChatClient.CreateAIAgent(instructions: Instructions);
        }

        _logger.LogInformation("Initialized Azure OpenAI Generic Agent with Azure OpenAI deployment: {DeploymentName} (Memory: {MemoryEnabled})",
            deploymentName, EnableLongRunningMemory);
        return Task.CompletedTask;
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("AzureOpenAIGenericAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("memory.enabled", EnableLongRunningMemory);
        activity?.SetTag("message.length", message.Length);

        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("Azure OpenAI Generic Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with Azure OpenAI Generic Agent (Memory: {MemoryEnabled})", EnableLongRunningMemory);

            var thread = GetOrCreateThread(conversationHistory);

            var chatOptions = new ChatOptions { MaxOutputTokens = 1000 };
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(chatOptions);

            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
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
