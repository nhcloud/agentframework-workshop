using Amazon;
using Amazon.BedrockRuntime;
using Amazon.Runtime;
using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Services;
using System.Diagnostics;

namespace DotNetAgentFramework.Agents;

/// <summary>
/// Bedrock HR Agent - AWS Bedrock nova-pro agent for HR/policy style conversations
/// </summary>
public class BedrockHRAgent(ILogger logger, AgentInstructionsService instructionsService, IOptions<AzureAIConfig>? azureConfig = null, ActivitySource? activitySource = null) : BaseAgent(logger, activitySource)
{
    private readonly AgentInstructionsService _instructionsService = instructionsService;
    private Microsoft.Agents.AI.AIAgent? _agent;
    private readonly Dictionary<string, Microsoft.Agents.AI.AgentThread> _threadCache = new();

    public override string Name => "bedrock_agent";
    public override string Description => _instructionsService.GetDescription("bedrock_agent");

    public override string Instructions => _instructionsService.GetInstructions("bedrock_agent");

    public override async Task InitializeAsync()
    {
        using var activity = _activitySource?.StartActivity("BedrockHRAgent.Initialize", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);

        await base.InitializeAsync();

        try
        {
            InitializeBedrockAgent();
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize Bedrock HR Agent");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            throw;
        }
    }

    private void InitializeBedrockAgent()
    {
        // Map .env keys to AWS credentials and model/region
       
        var accessKey = Environment.GetEnvironmentVariable("AWS_ACCESS_KEY_ID");
        var secretKey = Environment.GetEnvironmentVariable("AWS_SECRET_ACCESS_KEY");
        var regionName = Environment.GetEnvironmentVariable("AWS_REGION") ?? "us-east-1";
        var modelId = Environment.GetEnvironmentVariable("AWS_BEDROCK_MODEL_ID") ?? "amazon.nova-pro-v1:0";

        if (string.IsNullOrEmpty(secretKey))
        {
            throw new InvalidOperationException("AWS_SECRET_ACCESS_KEY must be set for Bedrock HR Agent");
        }

        // For API key style auth, use BasicAWSCredentials where the 'access key' is the API key
        var credentials = new BasicAWSCredentials(accessKey, secretKey);

        var config = new AmazonBedrockRuntimeConfig
        {
            RegionEndpoint = RegionEndpoint.GetBySystemName(regionName)
        };

        AmazonBedrockRuntimeClient runtimeClient = new(credentials, config);

        IChatClient bedrockChatClient = runtimeClient.AsIChatClient(modelId);

        // Create Microsoft Agents AI agent with our instructions
        _agent = bedrockChatClient.CreateAIAgent(instructions: Instructions);

        _logger.LogInformation("Initialized Bedrock HR Agent with AWS Bedrock model {ModelId} in region {Region}", modelId, regionName);
    }

    public override async Task<string> RespondAsync(string message, List<GroupChatMessage>? conversationHistory = null, string? context = null)
    {
        using var activity = _activitySource?.StartActivity("BedrockHRAgent.Respond", ActivityKind.Internal);
        activity?.SetTag("agent.name", Name);
        activity?.SetTag("message.length", message.Length);

        if (_agent == null)
        {
            await InitializeAsync();
        }

        if (_agent == null)
        {
            throw new InvalidOperationException("Bedrock HR Agent not properly initialized");
        }

        try
        {
            _logger.LogInformation("Processing message with Bedrock HR Agent");

            // Get or create thread for this conversation
            var thread = GetOrCreateThread(conversationHistory);

            // Create run options similar to AzureOpenAIGenericAgent
            var chatOptions = new ChatOptions { MaxOutputTokens = 1000 };
            var agentOptions = new Microsoft.Agents.AI.ChatClientAgentRunOptions(chatOptions);

            // Add optional context
            var enhancedMessage = message;
            if (!string.IsNullOrEmpty(context))
            {
                enhancedMessage = $"{message}\n\nAdditional Context: {context}";
            }

            var result = await _agent.RunAsync(enhancedMessage, thread, agentOptions);
            var responseText = result?.ToString() ?? "I apologize, but I couldn't generate a response from the Bedrock HR Agent.";

            _logger.LogInformation("Bedrock HR Agent generated response: {ResponseLength} characters", responseText.Length);

            activity?.SetTag("response.length", responseText.Length);
            activity?.SetStatus(ActivityStatusCode.Ok);

            return responseText;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing with Bedrock HR Agent");
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
            _logger.LogDebug("Created new Bedrock HR thread for key: {ThreadKey}", threadKey);
        }

        return thread;
    }

    public async ValueTask DisposeAsync()
    {
        _threadCache.Clear();
        _logger.LogDebug("Bedrock HR Agent cleanup completed");
        await Task.CompletedTask;
    }
}
