namespace DotNetAgentFramework.Configuration;

public class AzureAIConfig
{
    public AzureOpenAIConfig? AzureOpenAI { get; set; }
    public AzureAIFoundryConfig? AzureAIFoundry { get; set; }
}

public class AzureOpenAIConfig
{
    public string? Endpoint { get; set; }
    public string? ApiKey { get; set; }
    public string? DeploymentName { get; set; }
    public string? ApiVersion { get; set; }
    
    public bool IsConfigured()
    {
        return !string.IsNullOrEmpty(Endpoint) && 
               !string.IsNullOrEmpty(ApiKey) && 
               !string.IsNullOrEmpty(DeploymentName);
    }
}

public class AzureAIFoundryConfig
{
    public string? ProjectEndpoint { get; set; }
    public string? ManagedIdentityClientId { get; set; } // For Managed Identity authentication
    public string? PeopleAgentId { get; set; }
    public string? KnowledgeAgentId { get; set; }
    
    public bool IsConfigured()
    {
        return !string.IsNullOrEmpty(ProjectEndpoint);
    }
    
    public bool HasAgentIds()
    {
        return !string.IsNullOrEmpty(PeopleAgentId) || 
               !string.IsNullOrEmpty(KnowledgeAgentId);
    }
}