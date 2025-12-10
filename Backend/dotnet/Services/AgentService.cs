using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Agents;
using System.Diagnostics;

namespace DotNetAgentFramework.Services;

public interface IAgentService
{
    Task<IEnumerable<AgentInfo>> GetAvailableAgentsAsync();
    Task<IAgent?> GetAgentAsync(string agentName, bool enableMemory = false);
    Task<DotNetAgentFramework.Models.ChatResponse> ChatWithAgentAsync(string agentName, ChatRequest request);
    Task<DotNetAgentFramework.Models.ChatResponse> ChatWithAgentAsync(string agentName, ChatRequest request, List<GroupChatMessage>? conversationHistory);
    Task<IAgent?> CreateAzureFoundryAgentAsync(string agentType);
}

public class AgentService : IAgentService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<AgentService> _logger;
    private readonly AzureAIConfig _azureConfig;
    private readonly IConfiguration _configuration;
    private readonly IOptions<AzureAIConfig> _azureConfigOptions;
    private readonly Dictionary<string, Func<Task<IAgent>>> _agentFactories;
    
    // Add caching for Azure AI Foundry agents to prevent multiple initializations
    private readonly Dictionary<string, IAgent> _foundryAgentCache = new();
    private readonly SemaphoreSlim _foundryAgentCacheLock = new(1, 1);

    public AgentService(
        IServiceProvider serviceProvider, 
        ILogger<AgentService> logger,
        IOptions<AzureAIConfig> azureConfig,
        IConfiguration configuration)
    {
        _serviceProvider = serviceProvider;
        _logger = logger;
        _azureConfig = azureConfig.Value;
        _azureConfigOptions = azureConfig;
        _configuration = configuration;
        
        // Initialize agent factories with async initialization
        _agentFactories = new Dictionary<string, Func<Task<IAgent>>>
        {
            ["ms_foundry_people_agent"] = async () => await CreateStandardAgentAsync<MicrosoftFoundryPeopleAgent>(),
            ["azure_openai_agent"] = async () => await CreateStandardAgentAsync<AzureOpenAIGenericAgent>(),
            ["bedrock_agent"] = async () => await CreateStandardAgentAsync<BedrockHRAgent>(),
            ["openai_agent"] = async () => await CreateStandardAgentAsync<OpenAIGenericAgent>()
        };
    }

    private async Task<IAgent> CreateStandardAgentAsync<T>(bool enableMemory = false) where T : BaseAgent
    {
        var logger = _serviceProvider.GetRequiredService<ILogger<T>>();
        var instructionsService = _serviceProvider.GetRequiredService<AgentInstructionsService>();
        var activitySource = _serviceProvider.GetService<ActivitySource>(); // Get ActivitySource from DI
        
        // Log memory setting for debugging
        _logger.LogDebug("Creating agent with memory setting: {MemoryEnabled}", enableMemory);
        
        // Create agent with configuration support
        IAgent agent;
        if (typeof(T) == typeof(AzureOpenAIGenericAgent))
        {
            agent = (T)Activator.CreateInstance(typeof(T), logger, instructionsService, _azureConfigOptions, enableMemory, activitySource)!;
        }
        else if (typeof(T) == typeof(MicrosoftFoundryPeopleAgent))
        {
            agent = (T)Activator.CreateInstance(typeof(T), logger, instructionsService, _azureConfigOptions, activitySource)!;
        }
        else if (typeof(T) == typeof(BedrockHRAgent))
        {
            // Bedrock HR agent does not use Azure config, but we still pass options for consistency
            agent = (T)Activator.CreateInstance(typeof(T), logger, instructionsService, _azureConfigOptions, activitySource)!;
        }
        else if (typeof(T) == typeof(OpenAIGenericAgent))
        {
            // OpenAI agent only needs logger, instructions service, and activity source (no Azure config)
            agent = (T)Activator.CreateInstance(typeof(T), logger, instructionsService, activitySource)!;
        }
        else
        {
            agent = (T)Activator.CreateInstance(typeof(T), logger, instructionsService, _azureConfigOptions)!;
        }
        
        await agent.InitializeAsync();
        return agent;
    }

    public async Task<IAgent?> CreateAzureFoundryAgentAsync(string agentType)
    {
        if (_azureConfig?.AzureAIFoundry == null || 
            string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.ProjectEndpoint))
        {
            _logger.LogWarning("Azure AI Foundry not configured, cannot create foundry agent");
            return null;
        }

        // Check cache first to prevent multiple initializations
        var cacheKey = $"foundry_{agentType}";
        if (_foundryAgentCache.TryGetValue(cacheKey, out var cachedAgent))
        {
            _logger.LogDebug("Returning cached Azure AI Foundry agent: {AgentType}", agentType);
            return cachedAgent;
        }

        await _foundryAgentCacheLock.WaitAsync();
        try
        {
            // Double-check after acquiring lock
            if (_foundryAgentCache.TryGetValue(cacheKey, out cachedAgent))
            {
                _logger.LogDebug("Returning cached Azure AI Foundry agent after lock: {AgentType}", agentType);
                return cachedAgent;
            }

            _logger.LogInformation("Creating new Azure AI Foundry agent: {AgentType}", agentType);
            
            var logger = _serviceProvider.GetRequiredService<ILogger<AzureAIFoundryAgent>>();
            var activitySource = _serviceProvider.GetService<ActivitySource>(); // Get ActivitySource from DI
            
            var (agentId, description, instructions) = agentType.ToLowerInvariant() switch
            {
                "ms_foundry_people_agent" => (
                    _azureConfig.AzureAIFoundry.AgentId ?? "people-agent",
                    "Azure AI Foundry People Lookup Agent with enterprise directory access",
                    "You are a specialized People Lookup agent running in Azure AI Foundry. You have access to enterprise people directory and contact information. Use your enterprise knowledge to help users find the right people for their needs."
                ),
                _ => throw new ArgumentException($"Azure AI Foundry agent type '{agentType}' not supported")
            };

            if (string.IsNullOrEmpty(agentId))
            {
                throw new InvalidOperationException($"Agent ID not configured for {agentType} in Azure AI Foundry");
            }

            // Get Azure OpenAI configuration for the foundry agent
            var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME") ?? _azureConfig?.AzureOpenAI?.DeploymentName ?? "";
            
            if (string.IsNullOrEmpty(deploymentName))
            {
                throw new InvalidOperationException("Azure OpenAI deployment name is required for Azure AI Foundry agent");
            }

            Azure.Core.TokenCredential? credential = null;
            
            if (!string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.ManagedIdentityClientId))
            {
                credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
                {
                    ManagedIdentityClientId = _azureConfig.AzureAIFoundry.ManagedIdentityClientId
                });
            }
            else
            {
                credential = new DefaultAzureCredential();
            }

            var foundryAgent = new AzureAIFoundryAgent(
                name: "ms_foundry_people_agent",//_azureConfig.AzureAIFoundry.AgentId,
                agentId: agentId,
                projectEndpoint: _azureConfig.AzureAIFoundry.ProjectEndpoint,
                description: description,
                instructions: instructions,
                modelDeployment: deploymentName,
                credential: credential,
                logger: logger,
                managedIdentityClientId: _azureConfig.AzureAIFoundry.ManagedIdentityClientId,
                activitySource: activitySource
            );

            await foundryAgent.InitializeAsync();
            
            // Cache the agent to prevent future reinitializations
            _foundryAgentCache[cacheKey] = foundryAgent;
            
            _logger.LogInformation("Created and cached Azure AI Foundry agent: {AgentName} with ID: {AgentId}", foundryAgent.Name, agentId);
            return foundryAgent;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create Azure AI Foundry agent for type {AgentType}", agentType);
            return null;
        }
        finally
        {
            _foundryAgentCacheLock.Release();
        }
    }

    public async Task<IEnumerable<AgentInfo>> GetAvailableAgentsAsync()
    {
        var agents = new List<AgentInfo>();

        // Check Azure AI Foundry configuration
        var hasFoundryConfig = _azureConfig?.AzureAIFoundry != null && 
                              !string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.ProjectEndpoint);

        _logger.LogInformation("Azure AI Foundry configured: {HasFoundry}", hasFoundryConfig);

        // Always add the generic agent (Azure OpenAI)
        try
        {
            var genericAgent = await _agentFactories["azure_openai_agent"]();
            agents.Add(new AgentInfo
            {
                Name = genericAgent.Name,
                Id = genericAgent.Name, // Set Id to be the same as Name
                Description = genericAgent.Description,
                Instructions = genericAgent.Instructions,
                Model = "Azure OpenAI GPT-4o",
                AgentType = "Azure OpenAI",
                Capabilities = new List<string> { "General conversation", "Problem solving", "Task assistance", "Information provision" }
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create generic agent info");
        }

        // People Lookup agent
        await AddAgentInfo(agents, "ms_foundry_people_agent", hasFoundryConfig, 
            new List<string> { "People search", "Contact discovery", "Team coordination", "Role identification" });

        // Bedrock agent (AWS)
        try
        {
            if (_agentFactories.TryGetValue("bedrock_agent", out var bedrockFactory))
            {
                var bedrockAgent = await bedrockFactory();
                agents.Add(new AgentInfo
                {
                    Name = bedrockAgent.Name,
                    Id = bedrockAgent.Name,
                    Description = bedrockAgent.Description,
                    Instructions = bedrockAgent.Instructions,
                    Model = Environment.GetEnvironmentVariable("AWS_BEDROCK_MODEL_ID") ?? "amazon.nova-pro-v1:0",
                    AgentType = "AWS Bedrock",
                    Capabilities = new List<string> { "hr_policies", "benefits_explanation", "workplace_guidance" }
                });

                _logger.LogInformation("Added AWS Bedrock agent: {AgentName}", bedrockAgent.Name);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create AWS Bedrock agent info");
        }

        // OpenAI direct agent (non-Azure)
        try
        {
            if (_agentFactories.TryGetValue("openai_agent", out var openaiFactory))
            {
                var openaiAgent = await openaiFactory();
                agents.Add(new AgentInfo
                {
                    Name = openaiAgent.Name,
                    Id = openaiAgent.Name,
                    Description = openaiAgent.Description,
                    Instructions = openaiAgent.Instructions,
                    Model = Environment.GetEnvironmentVariable("OPENAI_MODEL_ID") ?? "gpt-4.1",
                    AgentType = "OpenAI",
                    Capabilities = new List<string> { "general_conversation", "coding_help", "analysis" }
                });

                _logger.LogInformation("Added OpenAI agent: {AgentName}", openaiAgent.Name);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create OpenAI agent info");
        }

        _logger.LogInformation("Returning {AgentCount} available agents", agents.Count);
        return agents;
    }

    private async Task AddAgentInfo(List<AgentInfo> agents, string agentType, bool hasFoundryConfig, List<string> capabilities)
    {
        // Try Azure AI Foundry first if configured
        if (hasFoundryConfig)
        {
            var foundryConfig = _azureConfig?.AzureAIFoundry;
            var hasAgentId = agentType switch
            {
                "ms_foundry_people_agent" => !string.IsNullOrEmpty(foundryConfig?.AgentId),
                _ => false
            };

            if (hasAgentId)
            {
                try
                {
                    var foundryAgent = await CreateAzureFoundryAgentAsync(agentType);
                    if (foundryAgent != null)
                    {
                        agents.Add(new AgentInfo
                        {
                            Name = foundryAgent.Name,
                            Id = foundryAgent.Name, // Set Id to be the same as Name
                            Description = foundryAgent.Description,
                            Instructions = foundryAgent.Instructions,
                            Model = "Azure AI Foundry",
                            AgentType = "Azure AI Foundry",
                            Capabilities = capabilities
                        });
                        
                        _logger.LogInformation("Added Azure AI Foundry agent: {AgentName}", foundryAgent.Name);
                        return; // Successfully added Foundry agent, don't add standard version
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Failed to create Azure AI Foundry agent {AgentType}, falling back to standard", agentType);
                }
            }
        }

        // Add standard Azure OpenAI agent as fallback
        try
        {
            if (_agentFactories.TryGetValue(agentType, out var factory))
            {
                var standardAgent = await factory();
                agents.Add(new AgentInfo
                {
                    Name = standardAgent.Name,
                    Id = standardAgent.Name, // Set Id to be the same as Name
                    Description = standardAgent.Description,
                    Instructions = standardAgent.Instructions,
                    Model = "Azure OpenAI GPT-4o",
                    AgentType = "Azure OpenAI",
                    Capabilities = capabilities
                });
                
                _logger.LogInformation("Added Azure OpenAI agent: {AgentName}", standardAgent.Name);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create standard agent {AgentType}", agentType);
        }
    }

    public async Task<IAgent?> GetAgentAsync(string agentName, bool enableMemory = false)
    {
        var normalizedName = agentName.ToLowerInvariant();
        
        _logger.LogInformation("Retrieving agent: {AgentName} with memory: {MemoryEnabled}", agentName, enableMemory);

        // Determine agent type from name
        var agentType = DetermineAgentType(normalizedName);
        
        _logger.LogDebug("Determined agent type: {AgentType} for agent name: {AgentName}", agentType, agentName);

        // Handle different agent types
        switch (agentType)
        {
            case "ms_foundry_agent":
                return await GetMicrosoftFoundryAgent(normalizedName);
                
            case "azure_openai_agent":
                return await CreateStandardAgentAsync<AzureOpenAIGenericAgent>(enableMemory);
                
            case "bedrock_agent":
                return await CreateStandardAgentAsync<BedrockHRAgent>();
                
            case "openai_agent":
                return await CreateStandardAgentAsync<OpenAIGenericAgent>();
                
            default:
                _logger.LogWarning("Unknown agent type '{AgentType}' for agent '{AgentName}'", agentType, agentName);
                return null;
        }
    }

    private string DetermineAgentType(string normalizedAgentName)
    {
        // Map agent names to their types
        if (normalizedAgentName.StartsWith("foundry_") || normalizedAgentName == "ms_foundry_people_agent")
        {
            return "ms_foundry_agent";
        }

        return normalizedAgentName switch
        {
            "azure_openai_agent" or "generic_agent" or "generic" => "azure_openai_agent",
            "bedrock_agent" => "bedrock_agent",
            "openai_agent" => "openai_agent",
            _ => normalizedAgentName // Return as-is if no specific mapping
        };
    }

    private async Task<IAgent?> GetMicrosoftFoundryAgent(string normalizedName)
    {
        // Check if Azure AI Foundry is configured
        var hasFoundryConfig = _azureConfig?.AzureAIFoundry != null &&
                              !string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.ProjectEndpoint) &&
                              !string.IsNullOrEmpty(_azureConfig.AzureAIFoundry.AgentId);

        if (!hasFoundryConfig)
        {
            _logger.LogWarning("Azure AI Foundry not configured for Microsoft Foundry agent");
            // Fall back to standard agent
            return await CreateStandardAgentAsync<MicrosoftFoundryPeopleAgent>();
        }

        try
        {
            // Try to create Azure AI Foundry agent
            var foundryAgent = await CreateAzureFoundryAgentAsync("ms_foundry_people_agent");
            if (foundryAgent != null)
            {
                _logger.LogInformation("Using Azure AI Foundry agent for {AgentName}", normalizedName);
                return foundryAgent;
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to create Azure AI Foundry agent, using standard version");
        }

        // Fallback to standard Microsoft Foundry People Agent
        return await CreateStandardAgentAsync<MicrosoftFoundryPeopleAgent>();
    }

    public async Task<DotNetAgentFramework.Models.ChatResponse> ChatWithAgentAsync(string agentName, ChatRequest request)
    {
        return await ChatWithAgentAsync(agentName, request, null);
    }

    public async Task<DotNetAgentFramework.Models.ChatResponse> ChatWithAgentAsync(string agentName, ChatRequest request, List<GroupChatMessage>? conversationHistory)
    {
        // Determine memory setting: request flag > environment variable > default false
        var enableMemory = request.EnableMemory ?? 
                          (bool.TryParse(Environment.GetEnvironmentVariable("ENABLE_LONG_RUNNING_MEMORY"), out var envMemory) && envMemory);
        
        _logger.LogDebug("Chat with {AgentName}: memory={MemoryEnabled} (from request: {RequestMemory}, env: {EnvMemory})", 
            agentName, enableMemory, request.EnableMemory, Environment.GetEnvironmentVariable("ENABLE_LONG_RUNNING_MEMORY"));
        
        var agent = await GetAgentAsync(agentName, enableMemory);
        if (agent == null)
        {
            throw new ArgumentException($"Agent '{agentName}' not found");
        }

        try
        {
            _logger.LogInformation("Starting chat with agent {AgentName} for message: {Message}", agentName, request.Message);
            var response = await agent.ChatWithHistoryAsync(request, conversationHistory);
            _logger.LogInformation("Chat completed with agent {AgentName}, response length: {Length}", agentName, response.Content?.Length ?? 0);
            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error during chat with agent {AgentName}", agentName);
            throw;
        }
    }
}