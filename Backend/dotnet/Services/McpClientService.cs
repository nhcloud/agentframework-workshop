using DotNetAgentFramework.Configuration;
using ModelContextProtocol;
using ModelContextProtocol.Client;
using System.Text.Json;
using System.Diagnostics;

namespace DotNetAgentFramework.Services;

/// <summary>
/// Service for managing MCP (Model Context Protocol) client connections
/// Allows the agent framework to connect to external MCP servers and call their tools
/// </summary>
public interface IMcpClientService
{
    /// <summary>
    /// Get all configured MCP servers
    /// </summary>
    Task<IEnumerable<McpServerInfo>> GetConfiguredServersAsync();
    
    /// <summary>
    /// Get available tools from a specific MCP server
    /// </summary>
    Task<IEnumerable<McpToolInfo>> GetToolsAsync(string serverName);
    
    /// <summary>
    /// Get available tools from all configured MCP servers
    /// </summary>
    Task<IEnumerable<McpToolInfo>> GetAllToolsAsync();
    
    /// <summary>
    /// Call a tool on an MCP server
    /// </summary>
    Task<McpToolResult> CallToolAsync(string serverName, string toolName, Dictionary<string, object>? arguments = null);
    
    /// <summary>
    /// Call a tool by its full name (server.tool format)
    /// </summary>
    Task<McpToolResult> CallToolByFullNameAsync(string fullToolName, Dictionary<string, object>? arguments = null);
    
    /// <summary>
    /// Test connection to an MCP server
    /// </summary>
    Task<McpConnectionTestResult> TestConnectionAsync(string serverName);
    
    /// <summary>
    /// Get resources from an MCP server
    /// </summary>
    Task<IEnumerable<McpResourceInfo>> GetResourcesAsync(string serverName);
}

public class McpClientService : IMcpClientService, IAsyncDisposable
{
    private readonly ILogger<McpClientService> _logger;
    private readonly McpConfig _config;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ActivitySource? _activitySource;
    private readonly Dictionary<string, IMcpClient> _clientCache = new();
    private readonly SemaphoreSlim _clientCacheLock = new(1, 1);

    public McpClientService(
        ILogger<McpClientService> logger,
        IOptions<McpConfig> config,
        IHttpClientFactory httpClientFactory,
        ActivitySource? activitySource = null)
    {
        _logger = logger;
        _config = config.Value;
        _httpClientFactory = httpClientFactory;
        _activitySource = activitySource;
    }

    public async Task<IEnumerable<McpServerInfo>> GetConfiguredServersAsync()
    {
        var servers = new List<McpServerInfo>();
        
        foreach (var serverConfig in _config.Servers.Where(s => s.Enabled))
        {
            servers.Add(new McpServerInfo
            {
                Name = serverConfig.Name,
                Description = serverConfig.Description,
                Transport = serverConfig.Transport,
                Endpoint = serverConfig.Endpoint,
                Enabled = serverConfig.Enabled,
                IsConfigured = serverConfig.IsConfigured()
            });
        }
        
        return await Task.FromResult(servers);
    }

    public async Task<IEnumerable<McpToolInfo>> GetToolsAsync(string serverName)
    {
        using var activity = _activitySource?.StartActivity($"MCP.GetTools.{serverName}", ActivityKind.Client);
        activity?.SetTag("mcp.server", serverName);
        
        try
        {
            var client = await GetOrCreateClientAsync(serverName);
            if (client == null)
            {
                _logger.LogWarning("Could not get MCP client for server {ServerName}", serverName);
                return Enumerable.Empty<McpToolInfo>();
            }

            var tools = await client.ListToolsAsync();
            var toolInfos = tools.Select(t => new McpToolInfo
            {
                Name = t.Name,
                Description = t.Description ?? string.Empty,
                ServerName = serverName,
                FullName = $"{serverName}.{t.Name}",
                InputSchema = t.JsonSchema.ToString()
            }).ToList();

            activity?.SetTag("mcp.tools.count", toolInfos.Count);
            activity?.SetStatus(ActivityStatusCode.Ok);
            
            _logger.LogInformation("Retrieved {ToolCount} tools from MCP server {ServerName}", toolInfos.Count, serverName);
            return toolInfos;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting tools from MCP server {ServerName}", serverName);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            throw;
        }
    }

    public async Task<IEnumerable<McpToolInfo>> GetAllToolsAsync()
    {
        var allTools = new List<McpToolInfo>();
        
        foreach (var server in _config.Servers.Where(s => s.Enabled && s.IsConfigured()))
        {
            try
            {
                var tools = await GetToolsAsync(server.Name);
                allTools.AddRange(tools);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Could not get tools from MCP server {ServerName}", server.Name);
            }
        }
        
        return allTools;
    }

    public async Task<McpToolResult> CallToolAsync(string serverName, string toolName, Dictionary<string, object>? arguments = null)
    {
        using var activity = _activitySource?.StartActivity($"MCP.CallTool.{serverName}.{toolName}", ActivityKind.Client);
        activity?.SetTag("mcp.server", serverName);
        activity?.SetTag("mcp.tool", toolName);
        
        var startTime = DateTime.UtcNow;
        
        try
        {
            var client = await GetOrCreateClientAsync(serverName);
            if (client == null)
            {
                return new McpToolResult
                {
                    Success = false,
                    Error = $"MCP server '{serverName}' not found or not configured",
                    ServerName = serverName,
                    ToolName = toolName,
                    DurationMs = (int)(DateTime.UtcNow - startTime).TotalMilliseconds
                };
            }

            // Check if tool is allowed
            var serverConfig = _config.Servers.FirstOrDefault(s => s.Name == serverName);
            if (serverConfig?.AllowedTools != null && !serverConfig.AllowedTools.Contains(toolName))
            {
                return new McpToolResult
                {
                    Success = false,
                    Error = $"Tool '{toolName}' is not in the allowed tools list for server '{serverName}'",
                    ServerName = serverName,
                    ToolName = toolName,
                    DurationMs = (int)(DateTime.UtcNow - startTime).TotalMilliseconds
                };
            }

            _logger.LogInformation("Calling MCP tool {ToolName} on server {ServerName} with arguments: {Arguments}",
                toolName, serverName, arguments != null ? JsonSerializer.Serialize(arguments) : "none");

            // Convert arguments to the expected format
            var mcpArguments = arguments ?? new Dictionary<string, object>();

            var result = await client.CallToolAsync(toolName, mcpArguments);
            
            var duration = (int)(DateTime.UtcNow - startTime).TotalMilliseconds;
            
            // Extract content from result
            var content = result.Content?.FirstOrDefault();
            var resultText = content?.Text ?? JsonSerializer.Serialize(result);

            activity?.SetTag("mcp.result.success", !result.IsError);
            activity?.SetTag("mcp.duration_ms", duration);
            activity?.SetStatus(result.IsError ? ActivityStatusCode.Error : ActivityStatusCode.Ok);

            _logger.LogInformation("MCP tool {ToolName} completed in {Duration}ms, success={Success}",
                toolName, duration, !result.IsError);

            return new McpToolResult
            {
                Success = !result.IsError,
                Result = resultText,
                ServerName = serverName,
                ToolName = toolName,
                DurationMs = duration,
                Error = result.IsError ? resultText : null
            };
        }
        catch (Exception ex)
        {
            var duration = (int)(DateTime.UtcNow - startTime).TotalMilliseconds;
            _logger.LogError(ex, "Error calling MCP tool {ToolName} on server {ServerName}", toolName, serverName);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            
            return new McpToolResult
            {
                Success = false,
                Error = ex.Message,
                ServerName = serverName,
                ToolName = toolName,
                DurationMs = duration
            };
        }
    }

    public async Task<McpToolResult> CallToolByFullNameAsync(string fullToolName, Dictionary<string, object>? arguments = null)
    {
        // Parse server.tool format
        var parts = fullToolName.Split('.', 2);
        if (parts.Length != 2)
        {
            return new McpToolResult
            {
                Success = false,
                Error = $"Invalid tool name format. Expected 'server.tool', got '{fullToolName}'",
                ToolName = fullToolName
            };
        }

        return await CallToolAsync(parts[0], parts[1], arguments);
    }

    public async Task<McpConnectionTestResult> TestConnectionAsync(string serverName)
    {
        using var activity = _activitySource?.StartActivity($"MCP.TestConnection.{serverName}", ActivityKind.Client);
        activity?.SetTag("mcp.server", serverName);
        
        var startTime = DateTime.UtcNow;
        
        try
        {
            var serverConfig = _config.Servers.FirstOrDefault(s => s.Name == serverName);
            if (serverConfig == null)
            {
                return new McpConnectionTestResult
                {
                    Success = false,
                    Error = $"Server '{serverName}' not found in configuration",
                    ServerName = serverName,
                    DurationMs = (int)(DateTime.UtcNow - startTime).TotalMilliseconds
                };
            }

            var client = await GetOrCreateClientAsync(serverName);
            if (client == null)
            {
                return new McpConnectionTestResult
                {
                    Success = false,
                    Error = "Failed to create MCP client",
                    ServerName = serverName,
                    DurationMs = (int)(DateTime.UtcNow - startTime).TotalMilliseconds
                };
            }

            // Try to list tools as a connection test
            var tools = await client.ListToolsAsync();
            var duration = (int)(DateTime.UtcNow - startTime).TotalMilliseconds;

            activity?.SetTag("mcp.tools.count", tools.Count);
            activity?.SetStatus(ActivityStatusCode.Ok);

            return new McpConnectionTestResult
            {
                Success = true,
                ServerName = serverName,
                ToolCount = tools.Count,
                DurationMs = duration,
                Message = $"Successfully connected. Found {tools.Count} tools."
            };
        }
        catch (Exception ex)
        {
            var duration = (int)(DateTime.UtcNow - startTime).TotalMilliseconds;
            _logger.LogError(ex, "Connection test failed for MCP server {ServerName}", serverName);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            
            return new McpConnectionTestResult
            {
                Success = false,
                Error = ex.Message,
                ServerName = serverName,
                DurationMs = duration
            };
        }
    }

    public async Task<IEnumerable<McpResourceInfo>> GetResourcesAsync(string serverName)
    {
        using var activity = _activitySource?.StartActivity($"MCP.GetResources.{serverName}", ActivityKind.Client);
        
        try
        {
            var client = await GetOrCreateClientAsync(serverName);
            if (client == null)
            {
                return Enumerable.Empty<McpResourceInfo>();
            }

            var resources = await client.ListResourcesAsync();
            return resources.Select(r => new McpResourceInfo
            {
                Uri = r.Uri,
                Name = r.Name,
                Description = r.Description,
                MimeType = r.MimeType,
                ServerName = serverName
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting resources from MCP server {ServerName}", serverName);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            return Enumerable.Empty<McpResourceInfo>();
        }
    }

    private async Task<IMcpClient?> GetOrCreateClientAsync(string serverName)
    {
        // Check cache first
        if (_clientCache.TryGetValue(serverName, out var cachedClient))
        {
            return cachedClient;
        }

        await _clientCacheLock.WaitAsync();
        try
        {
            // Double-check after acquiring lock
            if (_clientCache.TryGetValue(serverName, out cachedClient))
            {
                return cachedClient;
            }

            var serverConfig = _config.Servers.FirstOrDefault(s => s.Name == serverName && s.Enabled);
            if (serverConfig == null || !serverConfig.IsConfigured())
            {
                _logger.LogWarning("MCP server '{ServerName}' not found or not properly configured", serverName);
                return null;
            }

            IMcpClient client;
            
            switch (serverConfig.Transport.ToLowerInvariant())
            {
                case "http":
                case "sse":
                    client = await CreateHttpClientAsync(serverConfig);
                    break;
                    
                case "stdio":
                    client = await CreateStdioClientAsync(serverConfig);
                    break;
                    
                default:
                    _logger.LogError("Unsupported MCP transport type: {Transport}", serverConfig.Transport);
                    return null;
            }

            _clientCache[serverName] = client;
            _logger.LogInformation("Created MCP client for server {ServerName} using {Transport} transport",
                serverName, serverConfig.Transport);

            return client;
        }
        finally
        {
            _clientCacheLock.Release();
        }
    }

    private async Task<IMcpClient> CreateHttpClientAsync(McpServerConfig serverConfig)
    {
        if (string.IsNullOrEmpty(serverConfig.Endpoint))
        {
            throw new InvalidOperationException($"Endpoint is required for HTTP transport on server {serverConfig.Name}");
        }

        // Build headers dictionary
        var headers = new Dictionary<string, string>();
        
        if (!string.IsNullOrEmpty(serverConfig.Authorization))
        {
            headers["Authorization"] = serverConfig.Authorization;
        }
        
        if (serverConfig.Headers != null)
        {
            foreach (var header in serverConfig.Headers)
            {
                headers[header.Key] = header.Value;
            }
        }

        var options = new SseClientTransportOptions
        {
            Endpoint = new Uri(serverConfig.Endpoint),
            Name = serverConfig.Name,
            AdditionalHeaders = headers.Count > 0 ? headers : null
        };

        var transport = new SseClientTransport(options);
        var client = await McpClientFactory.CreateAsync(transport);

        return client;
    }

    private async Task<IMcpClient> CreateStdioClientAsync(McpServerConfig serverConfig)
    {
        if (string.IsNullOrEmpty(serverConfig.Command))
        {
            throw new InvalidOperationException($"Command is required for stdio transport on server {serverConfig.Name}");
        }

        var options = new StdioClientTransportOptions
        {
            Command = serverConfig.Command,
            Arguments = serverConfig.Arguments?.ToArray() ?? Array.Empty<string>(),
            Name = serverConfig.Name,
            EnvironmentVariables = serverConfig.EnvironmentVariables
        };

        var transport = new StdioClientTransport(options);
        var client = await McpClientFactory.CreateAsync(transport);

        return client;
    }

    public async ValueTask DisposeAsync()
    {
        await _clientCacheLock.WaitAsync();
        try
        {
            foreach (var client in _clientCache.Values)
            {
                if (client is IAsyncDisposable asyncDisposable)
                {
                    await asyncDisposable.DisposeAsync();
                }
                else if (client is IDisposable disposable)
                {
                    disposable.Dispose();
                }
            }
            _clientCache.Clear();
        }
        finally
        {
            _clientCacheLock.Release();
        }
    }
}

#region MCP Models

public class McpServerInfo
{
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Transport { get; set; } = string.Empty;
    public string? Endpoint { get; set; }
    public bool Enabled { get; set; }
    public bool IsConfigured { get; set; }
}

public class McpToolInfo
{
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string ServerName { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public string? InputSchema { get; set; }
}

public class McpToolResult
{
    public bool Success { get; set; }
    public string? Result { get; set; }
    public string? Error { get; set; }
    public string? ServerName { get; set; }
    public string? ToolName { get; set; }
    public int DurationMs { get; set; }
}

public class McpConnectionTestResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public string? Message { get; set; }
    public string? ServerName { get; set; }
    public int ToolCount { get; set; }
    public int DurationMs { get; set; }
}

public class McpResourceInfo
{
    public string Uri { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? MimeType { get; set; }
    public string ServerName { get; set; } = string.Empty;
}

#endregion
