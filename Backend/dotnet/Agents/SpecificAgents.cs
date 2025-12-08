using Azure.AI.Agents.Persistent;
using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Services;
using Microsoft.Extensions.AI;
using Microsoft.Extensions.Options;
using System.Text.Json;
using System.Diagnostics;
using OpenTelemetry.Trace;

namespace DotNetAgentFramework.Agents;

/// <summary>
/// People Lookup Agent - Azure AI Foundry agent for finding people information
/// </summary>
public class PeopleLookupAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private readonly AzureAIConfig? _azureConfig = azureConfig?.Value;
    private PersistentAgentsClient? _azureAgentClient;
    private Microsoft.Agents.AI.ChatClientAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();

    public override string Name => "people_lookup";
    public override string Description => _instructionsService.GetDescription("people_lookup");
    
    public override string Instructions => _instructionsService.GetInstructions("people_lookup");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("PeopleLookupAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        
        await base.InitializeAsync();

        try
        {
            // Try Azure AI Foundry first if configured
            if (_azureConfig?.AzureAIFoundry?.IsConfigured() == true && 
                !string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.PeopleAgentId))
            {
                await InitializeAzureFoundryAgentAsync();
                activity?.SetStatus(ActivityStatusCode.Ok);
                return;
            }

            // Fallback to Azure OpenAI
            await InitializeAzureOpenAIAgentAsync();
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize People Lookup Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }

    private async Task InitializeAzureFoundryAgentAsync()
    {
        var projectEndpoint = _azureConfig?.AzureAIFoundry?.ProjectEndpoint;
        var agentId = _azureConfig?.AzureAIFoundry?.PeopleAgentId;
        var managedIdentityClientId = _azureConfig?.AzureAIFoundry?.ManagedIdentityClientId;

        if (string.IsNullOrEmpty(projectEndpoint) || string.IsNullOrEmpty(agentId))
        {
            throw new InvalidOperationException("Azure AI Foundry project endpoint and agent ID are required for People Lookup Agent");
        }

        _logger.LogInformation("Initializing People Lookup Agent with Azure AI Foundry agent ID: {AgentId}", agentId);

        // Create credential - use managed identity if client ID is provided, otherwise use default
        // Replace obsolete ManagedIdentityCredential constructor usage with the recommended pattern
        Azure.Core.TokenCredential credential = !string.IsNullOrEmpty(managedIdentityClientId)
            ? new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(managedIdentityClientId))
            : new DefaultAzureCredential();

        // Create PersistentAgentsClient following the sample pattern
        _azureAgentClient = new PersistentAgentsClient(projectEndpoint, credential);

        // Get the AI agent using the sample pattern
        _agent =  _azureAgentClient.AsIChatClient(agentId).CreateAIAgent();

        _logger.LogInformation("Initialized People Lookup Agent with Azure AI Foundry agent: {AgentName}", _agent.Id);
    }

    private Task InitializeAzureOpenAIAgentAsync()
    {
        // Get Azure OpenAI configuration
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? _azureConfig?.AzureOpenAI?.Endpoint;
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? _azureConfig?.AzureOpenAI?.ApiKey;
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME") ?? _azureConfig?.AzureOpenAI?.DeploymentName ?? "gpt-4o";

        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey))
        {
            throw new InvalidOperationException("Azure OpenAI endpoint and API key are required for People Lookup Agent");
        }

        // Create Azure OpenAI client and get chat client following the new pattern
        var azureClient = new AzureOpenAIClient(new Uri(endpoint), new AzureCliCredential());
        _agent = azureClient.GetChatClient(deploymentName)
            .CreateAIAgent(name: "PeopleLookup", instructions: Instructions);
        
        _logger.LogInformation("Initialized People Lookup Agent with Azure OpenAI deployment: {DeploymentName}", deploymentName);
        return Task.CompletedTask;
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("PeopleLookupAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("message.length", message.Length);
        
        // Ensure agent is initialized
        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("People Lookup Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with People Lookup Agent");

            // Get or create thread for this conversation
            var thread = GetOrCreateThread(conversationHistory);

            // Create agent options following the sample pattern
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(new() { MaxOutputTokens = 1000 });

            // Add context to message if provided
            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            // Run the agent following the sample pattern
            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the People Lookup Agent.";
            
            _logger.LogInformation("People Lookup Agent generated response: {ResponseLength} characters", responseText.Length);
            
            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);
            
            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with People Lookup Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            return $"I encountered an error while processing your request: {ex.Message}";
        }
    }

    private Microsoft.Agents.AI.AgentThread GetOrCreateThread(List<GroupChatMessage>? conversationHistory)
    {
        // Simple thread management - in production you might want more sophisticated caching
        var threadKey = "default";
        if (conversationHistory != null && conversationHistory.Any())
        {
            // Create a thread key based on conversation history
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

    // Cleanup method to dispose of threads when agent is disposed
    public async ValueTask DisposeAsync()
    {
        if (_azureAgentClient != null && _agent != null)
        {
            // Clean up threads
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
                    _logger.LogWarning(ex, "Failed to cleanup thread for People Lookup Agent");
                }
            }
        }
        
        _threadCache.Clear();
    }
}

/// <summary>
/// Knowledge Finder Agent - Azure AI Foundry agent for searching and retrieving information
/// </summary>
public class KnowledgeFinderAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private readonly AzureAIConfig? _azureConfig = azureConfig?.Value;
    private PersistentAgentsClient? _azureAgentClient;
    private Microsoft.Agents.AI.ChatClientAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();

    public override string Name => "knowledge_finder";
    public override string Description => _instructionsService.GetDescription("knowledge_finder");
    
    public override string Instructions => _instructionsService.GetInstructions("knowledge_finder");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("KnowledgeFinderAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        
        await base.InitializeAsync();

        try
        {
            // Try Azure AI Foundry first if configured
            if (_azureConfig?.AzureAIFoundry?.IsConfigured() == true && 
                !string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.KnowledgeAgentId))
            {
                await InitializeAzureFoundryAgentAsync();
                activity?.SetStatus(ActivityStatusCode.Ok);
                return;
            }

            // Fallback to Azure OpenAI
            await InitializeAzureOpenAIAgentAsync();
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize Knowledge Finder Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }

    private async Task InitializeAzureFoundryAgentAsync()
    {
        var projectEndpoint = _azureConfig?.AzureAIFoundry?.ProjectEndpoint;
        var agentId = _azureConfig?.AzureAIFoundry?.KnowledgeAgentId;
        var managedIdentityClientId = _azureConfig?.AzureAIFoundry?.ManagedIdentityClientId;

        if (string.IsNullOrEmpty(projectEndpoint) || string.IsNullOrEmpty(agentId))
        {
            throw new InvalidOperationException("Azure AI Foundry project endpoint and agent ID are required for Knowledge Finder Agent");
        }

        _logger.LogInformation("Initializing Knowledge Finder Agent with Azure AI Foundry agent ID: {AgentId}", agentId);

        // Create credential - use managed identity if client ID is provided, otherwise use default
        // Replace obsolete ManagedIdentityCredential constructor usage with the recommended pattern
        Azure.Core.TokenCredential credential = !string.IsNullOrEmpty(managedIdentityClientId)
            ? new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(managedIdentityClientId))
            : new DefaultAzureCredential();

        // Create PersistentAgentsClient following the sample pattern
        _azureAgentClient = new PersistentAgentsClient(projectEndpoint, credential);

        // Get the AI agent using the sample pattern
        _agent = _azureAgentClient.AsIChatClient(agentId).CreateAIAgent();

        _logger.LogInformation("Initialized Knowledge Finder Agent with Azure AI Foundry agent: {AgentName}", _agent.Id);
    }

    private Task InitializeAzureOpenAIAgentAsync()
    {
        // Get Azure OpenAI configuration
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? _azureConfig?.AzureOpenAI?.Endpoint;
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? _azureConfig?.AzureOpenAI?.ApiKey;
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME") ?? _azureConfig?.AzureOpenAI?.DeploymentName ?? "gpt-4o";

        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey))
        {
            throw new InvalidOperationException("Azure OpenAI endpoint and API key are required for Knowledge Finder Agent");
        }

        // Create Azure OpenAI client and get chat client following the new pattern
        var azureClient = new AzureOpenAIClient(new Uri(endpoint), new AzureCliCredential());
        _agent = azureClient.GetChatClient(deploymentName)
            .CreateAIAgent(name: "KnowledgeFinder", instructions: Instructions);
        
        _logger.LogInformation("Initialized Knowledge Finder Agent with Azure OpenAI deployment: {DeploymentName}", deploymentName);
        return Task.CompletedTask;
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("KnowledgeFinderAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("message.length", message.Length);
        
        // Ensure agent is initialized
        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("Knowledge Finder Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with Knowledge Finder Agent");

            // Get or create thread for this conversation
            var thread = GetOrCreateThread(conversationHistory);

            // Create agent options following the sample pattern
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(new() { MaxOutputTokens = 1000 });

            // Add context to message if provided
            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            // Run the agent following the sample pattern
            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the Knowledge Finder Agent.";
            
            _logger.LogInformation("Knowledge Finder Agent generated response: {ResponseLength} characters", responseText.Length);
            
            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);
            
            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with Knowledge Finder Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            return $"I encountered an error while processing your request: {ex.Message}";
        }
    }

    private Microsoft.Agents.AI.AgentThread GetOrCreateThread(List<GroupChatMessage>? conversationHistory)
    {
        // Simple thread management - in production you might want more sophisticated caching
        var threadKey = "default";
        if (conversationHistory != null && conversationHistory.Any())
        {
            // Create a thread key based on conversation history
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

    // Cleanup method to dispose of threads when agent is disposed
    public async ValueTask DisposeAsync()
    {
        if (_azureAgentClient != null && _agent != null)
        {
            // Clean up threads
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
                    _logger.LogWarning(ex, "Failed to cleanup thread for Knowledge Finder Agent");
                }
            }
        }
        
        _threadCache.Clear();
    }
}

/// <summary>
/// Generic Agent - Default agent for general-purpose conversations
/// </summary>
public class GenericAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, bool enableMemory = false, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private readonly AzureAIConfig? _azureConfig = azureConfig?.Value;
    private Microsoft.Agents.AI.ChatClientAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();
    private readonly Dictionary<string, JsonElement> _memoryStates = new();

    public override string Name => "generic_agent";
    public override string Description => _instructionsService.GetDescription("generic_agent");
    
    public override string Instructions => _instructionsService.GetInstructions("generic_agent");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("GenericAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("memory.enabled", enableMemory);
        
        await base.InitializeAsync();

        // Set memory flag from constructor
        EnableLongRunningMemory = enableMemory;

        try
        {
            // Use Azure OpenAI only
            await InitializeAzureOpenAIAgentAsync();
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize Generic Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }

    private Task InitializeAzureOpenAIAgentAsync()
    {
        // Get Azure OpenAI configuration
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? _azureConfig?.AzureOpenAI?.Endpoint;
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? _azureConfig?.AzureOpenAI?.ApiKey;
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME") ?? _azureConfig?.AzureOpenAI?.DeploymentName ?? "gpt-4o";

        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey))
        {
            throw new InvalidOperationException("Azure OpenAI endpoint and API key are required for Generic Agent");
        }

        // Create Azure OpenAI client and get chat client following the new pattern
        var azureClient = new AzureOpenAIClient(new Uri(endpoint), new AzureCliCredential());
        var chatClient = azureClient.GetChatClient(deploymentName);
        var iChatClient = chatClient.AsIChatClient();

        // If memory is enabled, create with AIContextProvider using UserInfoMemory
        if (EnableLongRunningMemory)
        {
            _logger.LogInformation("Initializing Generic Agent with UserInfoMemory for long-running memory support");
            
            // Create AIAgent with UserInfoMemory context provider using ChatClientAgentOptions
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
            _logger.LogInformation("Initializing Generic Agent without memory");
            
            // Standard agent without memory - using simple overload
            _agent = iChatClient.CreateAIAgent(instructions: Instructions);
        }
        
        _logger.LogInformation("Initialized Generic Agent with Azure OpenAI deployment: {DeploymentName} (Memory: {MemoryEnabled})", 
            deploymentName, EnableLongRunningMemory);
        return Task.CompletedTask;
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("GenericAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("memory.enabled", EnableLongRunningMemory);
        activity?.SetTag("message.length", message.Length);
        
        // Ensure agent is initialized
        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("Generic Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with Generic Agent (Memory: {MemoryEnabled})", EnableLongRunningMemory);

            // Get or create thread for this conversation
            var thread = GetOrCreateThread(conversationHistory);

            // Create agent options following the sample pattern
            var chatOptions = new ChatOptions { MaxOutputTokens = 1000 };
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(chatOptions);

            // Add context to message if provided
            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            // Run the agent following the sample pattern
            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the Generic Agent.";
            
            _logger.LogInformation("Generic Agent generated response: {ResponseLength} characters", responseText.Length);
            
            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);
            
            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with Generic Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            return $"I encountered an error while processing your request: {ex.Message}";
        }
    }

    private Microsoft.Agents.AI.AgentThread GetOrCreateThread(List<GroupChatMessage>? conversationHistory)
    {
        // Simple thread management - in production you might want more sophisticated caching
        var threadKey = "default";
        if (conversationHistory != null && conversationHistory.Any())
        {
            // Create a thread key based on conversation history
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

    // Cleanup method to dispose of threads when agent is disposed
    public async ValueTask DisposeAsync()
    {
        // Clean up threads - simplified for Azure OpenAI only
        _threadCache.Clear();
        _memoryStates.Clear();
        
        _logger.LogDebug("Generic Agent cleanup completed");
    }
}