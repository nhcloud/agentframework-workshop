using DotNetAgentFramework.Services;
using System.Diagnostics;

namespace DotNetAgentFramework.Agents;

/// <summary>
/// OpenAI Agent - Direct OpenAI API model (non-Azure) using Microsoft.Agents.AI
/// </summary>
public class OpenAIGenericAgent(ILogger logger, AgentInstructionsService instructionsService, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private Microsoft.Agents.AI.AIAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();

    public override string Name => "openai_agent";
    public override string Description => _instructionsService.GetDescription("openai_agent");
    public override string Instructions => _instructionsService.GetInstructions("openai_agent");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("OpenAIGenericAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);

        await base.InitializeAsync();

        try
        {
            InitializeOpenAIAgent();
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize OpenAI Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            throw;
        }
    }

    private void InitializeOpenAIAgent()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY");
        var modelId = Environment.GetEnvironmentVariable("OPENAI_MODEL_ID") ?? "gpt-4.1";

        if (string.IsNullOrEmpty(apiKey))
        {
            throw new InvalidOperationException("OPENAI_API_KEY must be set for OpenAI Agent");
        }

        var client = new OpenAIClient(apiKey);
        var chatClient = client.GetChatClient(modelId);
        IChatClient iChatClient = chatClient.AsIChatClient();

        _agent = iChatClient.CreateAIAgent(instructions: Instructions);

        _logger.LogInformation("Initialized OpenAI Agent with model {ModelId}", modelId);
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("OpenAIGenericAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("message.length", message.Length);

        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("OpenAI Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with OpenAI Agent");

            var thread = GetOrCreateThread(conversationHistory);

            var chatOptions = new ChatOptions { MaxOutputTokens = 1000 };
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(chatOptions);

            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the OpenAI Agent.";

            _logger.LogInformation("OpenAI Agent generated response: {ResponseLength} characters", responseText.Length);

            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);

            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with OpenAI Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
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
            _logger.LogDebug("Created new OpenAI thread for key: {ThreadKey}", threadKey);
        }

        return thread;
    }

    public async ValueTask DisposeAsync()
    {
        _threadCache.Clear();
        _logger.LogDebug("OpenAI Agent cleanup completed");
        await Task.CompletedTask;
    }
}
