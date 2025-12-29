namespace DotNetAgentFramework.Configuration;

/// <summary>
/// MCP (Model Context Protocol) configuration
/// </summary>
public class McpConfig
{
    /// <summary>
    /// List of configured MCP servers
    /// </summary>
    public List<McpServerConfig> Servers { get; set; } = new();
    
    /// <summary>
    /// Whether MCP client is enabled
    /// </summary>
    public bool Enabled { get; set; } = true;
    
    /// <summary>
    /// Default timeout for MCP operations in seconds
    /// </summary>
    public int DefaultTimeoutSeconds { get; set; } = 30;
}

/// <summary>
/// Configuration for a single MCP server
/// </summary>
public class McpServerConfig
{
    /// <summary>
    /// Unique name/identifier for the server
    /// </summary>
    public string Name { get; set; } = string.Empty;
    
    /// <summary>
    /// Description of what this MCP server provides
    /// </summary>
    public string Description { get; set; } = string.Empty;
    
    /// <summary>
    /// Server transport type: "stdio", "sse", or "http"
    /// </summary>
    public string Transport { get; set; } = "http";
    
    /// <summary>
    /// For HTTP/SSE transport: the base URL of the MCP server
    /// </summary>
    public string? Endpoint { get; set; }
    
    /// <summary>
    /// For stdio transport: the command to execute
    /// </summary>
    public string? Command { get; set; }
    
    /// <summary>
    /// For stdio transport: command arguments
    /// </summary>
    public List<string>? Arguments { get; set; }
    
    /// <summary>
    /// Environment variables to set for stdio transport
    /// </summary>
    public Dictionary<string, string>? EnvironmentVariables { get; set; }
    
    /// <summary>
    /// Authorization header value (e.g., "Bearer token123")
    /// </summary>
    public string? Authorization { get; set; }
    
    /// <summary>
    /// Additional headers to include in HTTP requests
    /// </summary>
    public Dictionary<string, string>? Headers { get; set; }
    
    /// <summary>
    /// Whether this server is enabled
    /// </summary>
    public bool Enabled { get; set; } = true;
    
    /// <summary>
    /// Timeout for operations on this server in seconds
    /// </summary>
    public int TimeoutSeconds { get; set; } = 30;
    
    /// <summary>
    /// List of tool names to expose from this server (null = all tools)
    /// </summary>
    public List<string>? AllowedTools { get; set; }
    
    public bool IsConfigured()
    {
        return !string.IsNullOrEmpty(Name) && 
               (Transport == "stdio" ? !string.IsNullOrEmpty(Command) : !string.IsNullOrEmpty(Endpoint));
    }
}
