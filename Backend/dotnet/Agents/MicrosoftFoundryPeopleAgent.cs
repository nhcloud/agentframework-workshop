using Azure.AI.Agents.Persistent;
using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Services;
using OpenTelemetry.Trace;
using System.Diagnostics;

namespace DotNetAgentFramework.Agents;

/// <summary>
/// Microsoft Foundry People Agent - Azure AI Foundry agent for finding people information
/// </summary>
public class MicrosoftFoundryPeopleAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private readonly AzureAIConfig? _azureConfig = azureConfig?.Value;
    private PersistentAgentsClient? _azureAgentClient;
    private Microsoft.Agents.AI.ChatClientAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();

    public override string Name => "ms_foundry_people_agent";
    public override string Description => _instructionsService.GetDescription("ms_foundry_people_agent");

    public override string Instructions => _instructionsService.GetInstructions("ms_foundry_people_agent");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("MicrosoftFoundryPeopleAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);

        await base.InitializeAsync();

        try
        {
            // Try Azure AI Foundry first if configured
            if (_azureConfig?.AzureAIFoundry?.IsConfigured() == true &&
                !string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.AgentId))
            {
                await InitializeAzureFoundryAgentAsync();
                activity?.SetStatus(ActivityStatusCode.Ok);
                return;
            }
            else
            {
                throw new Exception("Azure AI Foundry Agent is not configured.");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize Microsoft Foundry People Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }

    private async Task InitializeAzureFoundryAgentAsync()
    {
        var projectEndpoint = _azureConfig?.AzureAIFoundry?.ProjectEndpoint;
        var agentId = _azureConfig?.AzureAIFoundry?.AgentId;
        var managedIdentityClientId = _azureConfig?.AzureAIFoundry?.ManagedIdentityClientId;

        if (string.IsNullOrEmpty(projectEndpoint) || string.IsNullOrEmpty(agentId))
        {
            throw new InvalidOperationException("Azure AI Foundry project endpoint and agent ID are required for Microsoft Foundry People Agent");
        }

        _logger.LogInformation("Initializing Microsoft Foundry People Agent with Azure AI Foundry agent ID: {AgentId}", agentId);

        Azure.Core.TokenCredential credential = !string.IsNullOrEmpty(managedIdentityClientId)
            ? new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(managedIdentityClientId))
            : new DefaultAzureCredential();

        _azureAgentClient = new PersistentAgentsClient(projectEndpoint, credential);
        _agent = _azureAgentClient.AsIChatClient(agentId).CreateAIAgent();

        _logger.LogInformation("Initialized Microsoft Foundry People Agent with Azure AI Foundry agent: {AgentName}", _agent.Id);
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("MicrosoftFoundryPeopleAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("message.length", message.Length);

        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("Microsoft Foundry People Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with Microsoft Foundry People Agent");

            var thread = GetOrCreateThread(conversationHistory);
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(new() { MaxOutputTokens = 1000 });

            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the Microsoft Foundry People Agent.";

            _logger.LogInformation("Microsoft Foundry People Agent generated response: {ResponseLength} characters", responseText.Length);

            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);

            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with Microsoft Foundry People Agent");
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
        if (_azureAgentClient != null && _agent != null)
        {
            foreach (var thread in _threadCache.Values)
            {
                try
                {
                    if (thread is Microsoft.Agents.AI.ChatClientAgentThread chatThread)
                    {
                        await _azureAgentClient.Threads.DeleteThreadAsync(chatThread.ConversationId);
                        _logger.LogDebug("Cleaned up thread: {ConversationId}", chatThread.ConversationId);
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Failed to cleanup thread for Microsoft Foundry People Agent");
                }
            }
        }

        _threadCache.Clear();
    }
}
