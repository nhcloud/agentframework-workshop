namespace DotNetAgentFramework.Configuration;

public class AzureAIConfig
{
    public AzureOpenAIConfig? AzureOpenAI { get; set; }
    public AzureAIFoundryConfig? AzureAIFoundry { get; set; }
    public ContentSafetyConfig? ContentSafety { get; set; }
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

public class ContentSafetyConfig
{
    public string? Endpoint { get; set; }
    public string? ApiKey { get; set; }
    public int SeverityThreshold { get; set; } = 5; // Legacy single threshold
    public bool Enabled { get; set; } = true;
    public int HateThreshold { get; set; } = 4;
    public int SelfHarmThreshold { get; set; } = 4;
    public int SexualThreshold { get; set; } = 4;
    public int ViolenceThreshold { get; set; } = 4;
    public bool BlockUnsafeInput { get; set; } = true;
    public bool FilterUnsafeOutput { get; set; } = true;
    public string? Blocklists { get; set; } // Comma-separated names
    public string OutputAction { get; set; } = "redact"; // redact | placeholder | empty
    public string PlaceholderText { get; set; } = "[Content removed due to safety policy]";

    public bool IsConfigured()
        => !string.IsNullOrWhiteSpace(Endpoint) && !string.IsNullOrWhiteSpace(ApiKey);
}