using DotNetAgentFramework.Services;
using DotNetAgentFramework.Agents.Tools;
using DotNetAgentFramework.Configuration;
using Microsoft.AspNetCore.Mvc;
using System.ComponentModel;
using System.Reflection;

namespace DotNetAgentFramework.Controllers;

/// <summary>
/// Tools Controller - Provides access to all available tools (local, local MCP, remote MCP)
/// Used by the frontend to display and select tools for agent requests
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class ToolsController : ControllerBase
{
    private readonly IMcpClientService _mcpClientService;
    private readonly IOptions<McpConfig> _mcpConfig;
    private readonly ILogger<ToolsController> _logger;

    public ToolsController(
        IMcpClientService mcpClientService,
        IOptions<McpConfig> mcpConfig,
        ILogger<ToolsController> logger)
    {
        _mcpClientService = mcpClientService;
        _mcpConfig = mcpConfig;
        _logger = logger;
    }

    /// <summary>
    /// Get all available tools from all sources (local, local MCP, remote MCP)
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(ToolsResponse), 200)]
    public async Task<ActionResult<ToolsResponse>> GetAllTools()
    {
        try
        {
            var allTools = new List<ToolInfo>();

            // 1. Get local coded tools (like WeatherTool)
            var localTools = GetLocalTools();
            allTools.AddRange(localTools);
            _logger.LogInformation("Found {Count} local tools", localTools.Count);

            // 2. Get MCP tools from all configured servers
            try
            {
                var mcpTools = await _mcpClientService.GetAllToolsAsync();
                var mcpServers = _mcpConfig.Value.Servers.ToDictionary(s => s.Name, s => s);
                
                foreach (var mcpTool in mcpTools)
                {
                    // Get server transport type for better categorization
                    var transport = mcpServers.TryGetValue(mcpTool.ServerName, out var serverConfig) 
                        ? serverConfig.Transport 
                        : "unknown";
                    
                    allTools.Add(new ToolInfo
                    {
                        Name = mcpTool.Name,
                        FullName = mcpTool.FullName,
                        Description = mcpTool.Description,
                        Source = "mcp",
                        ServerName = mcpTool.ServerName,
                        Transport = transport,
                        Category = GetMcpToolCategory(mcpTool.ServerName, transport),
                        InputSchema = mcpTool.InputSchema,
                        Enabled = true
                    });
                }
                _logger.LogInformation("Found {Count} MCP tools", mcpTools.Count());
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to get MCP tools");
            }

            // Group tools by source/category
            var groupedTools = allTools
                .GroupBy(t => t.Category)
                .Select(g => new ToolCategory
                {
                    Name = g.Key,
                    DisplayName = GetCategoryDisplayName(g.Key),
                    Tools = g.ToList(),
                    Count = g.Count()
                })
                .OrderBy(c => GetCategoryOrder(c.Name))
                .ToList();

            // Get MCP server status info
            var serverStatus = await GetMcpServerStatusAsync();

            return Ok(new ToolsResponse
            {
                Success = true,
                Tools = allTools,
                Categories = groupedTools,
                TotalCount = allTools.Count,
                LocalCount = allTools.Count(t => t.Source == "local"),
                McpCount = allTools.Count(t => t.Source == "mcp"),
                McpStdioCount = allTools.Count(t => t.Source == "mcp" && t.Transport == "stdio"),
                McpSseCount = allTools.Count(t => t.Source == "mcp" && (t.Transport == "sse" || t.Transport == "http")),
                ServerStatus = serverStatus,
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting all tools");
            return StatusCode(500, new ToolsResponse
            {
                Success = false,
                Message = "Error retrieving tools",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Get only local coded tools
    /// </summary>
    [HttpGet("local")]
    [ProducesResponseType(typeof(ToolsResponse), 200)]
    public ActionResult<ToolsResponse> GetLocalToolsOnly()
    {
        try
        {
            var localTools = GetLocalTools();

            return Ok(new ToolsResponse
            {
                Success = true,
                Tools = localTools,
                TotalCount = localTools.Count,
                LocalCount = localTools.Count,
                McpCount = 0,
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting local tools");
            return StatusCode(500, new ToolsResponse
            {
                Success = false,
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Get MCP tools from all servers or a specific server
    /// </summary>
    [HttpGet("mcp")]
    [ProducesResponseType(typeof(ToolsResponse), 200)]
    public async Task<ActionResult<ToolsResponse>> GetMcpTools([FromQuery] string? serverName = null, [FromQuery] string? transport = null)
    {
        try
        {
            var mcpTools = new List<ToolInfo>();
            var mcpServers = _mcpConfig.Value.Servers.ToDictionary(s => s.Name, s => s);

            if (!string.IsNullOrEmpty(serverName))
            {
                var tools = await _mcpClientService.GetToolsAsync(serverName);
                var serverTransport = mcpServers.TryGetValue(serverName, out var serverConfig) 
                    ? serverConfig.Transport 
                    : "unknown";
                    
                foreach (var tool in tools)
                {
                    mcpTools.Add(new ToolInfo
                    {
                        Name = tool.Name,
                        FullName = tool.FullName,
                        Description = tool.Description,
                        Source = "mcp",
                        ServerName = tool.ServerName,
                        Transport = serverTransport,
                        Category = GetMcpToolCategory(tool.ServerName, serverTransport),
                        InputSchema = tool.InputSchema,
                        Enabled = true
                    });
                }
            }
            else
            {
                var tools = await _mcpClientService.GetAllToolsAsync();
                foreach (var tool in tools)
                {
                    var serverTransport = mcpServers.TryGetValue(tool.ServerName, out var serverConfig) 
                        ? serverConfig.Transport 
                        : "unknown";
                    
                    // Filter by transport if specified
                    if (!string.IsNullOrEmpty(transport) && 
                        !serverTransport.Equals(transport, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                    
                    mcpTools.Add(new ToolInfo
                    {
                        Name = tool.Name,
                        FullName = tool.FullName,
                        Description = tool.Description,
                        Source = "mcp",
                        ServerName = tool.ServerName,
                        Transport = serverTransport,
                        Category = GetMcpToolCategory(tool.ServerName, serverTransport),
                        InputSchema = tool.InputSchema,
                        Enabled = true
                    });
                }
            }

            return Ok(new ToolsResponse
            {
                Success = true,
                Tools = mcpTools,
                TotalCount = mcpTools.Count,
                LocalCount = 0,
                McpCount = mcpTools.Count,
                McpStdioCount = mcpTools.Count(t => t.Transport == "stdio"),
                McpSseCount = mcpTools.Count(t => t.Transport == "sse" || t.Transport == "http"),
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting MCP tools");
            return StatusCode(500, new ToolsResponse
            {
                Success = false,
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Get MCP server configurations and status
    /// </summary>
    [HttpGet("mcp/servers")]
    [ProducesResponseType(typeof(McpServersResponse), 200)]
    public async Task<ActionResult<McpServersResponse>> GetMcpServers()
    {
        try
        {
            var servers = await _mcpClientService.GetConfiguredServersAsync();
            var serverList = servers.ToList();
            
            return Ok(new McpServersResponse
            {
                Success = true,
                Servers = serverList.Select(s => new McpServerStatus
                {
                    Name = s.Name,
                    Description = s.Description,
                    Transport = s.Transport,
                    Endpoint = s.Endpoint,
                    Enabled = s.Enabled,
                    IsConfigured = s.IsConfigured
                }).ToList(),
                TotalCount = serverList.Count,
                EnabledCount = serverList.Count(s => s.Enabled),
                StdioCount = serverList.Count(s => s.Transport.Equals("stdio", StringComparison.OrdinalIgnoreCase)),
                SseCount = serverList.Count(s => s.Transport.Equals("sse", StringComparison.OrdinalIgnoreCase) || 
                                                   s.Transport.Equals("http", StringComparison.OrdinalIgnoreCase)),
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting MCP servers");
            return StatusCode(500, new McpServersResponse
            {
                Success = false,
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Call a specific tool
    /// </summary>
    [HttpPost("call")]
    [ProducesResponseType(typeof(ToolCallResponse), 200)]
    public async Task<ActionResult<ToolCallResponse>> CallTool([FromBody] ToolCallRequest request)
    {
        try
        {
            if (string.IsNullOrEmpty(request.ToolName))
            {
                return BadRequest(new ToolCallResponse
                {
                    Success = false,
                    Error = "Tool name is required"
                });
            }

            _logger.LogInformation("Calling tool: {ToolName} from source: {Source}", request.ToolName, request.Source);

            object? result;
            var startTime = DateTime.UtcNow;

            if (request.Source == "local")
            {
                // Call local tool
                result = await CallLocalToolAsync(request.ToolName, request.Arguments);
            }
            else if (request.Source == "mcp")
            {
                // Call MCP tool
                if (string.IsNullOrEmpty(request.ServerName))
                {
                    // Try to parse from full name (server.tool)
                    var parts = request.ToolName.Split('.', 2);
                    if (parts.Length == 2)
                    {
                        request.ServerName = parts[0];
                        request.ToolName = parts[1];
                    }
                    else
                    {
                        return BadRequest(new ToolCallResponse
                        {
                            Success = false,
                            Error = "Server name is required for MCP tools"
                        });
                    }
                }

                var mcpResult = await _mcpClientService.CallToolAsync(
                    request.ServerName, 
                    request.ToolName, 
                    request.Arguments);
                
                return Ok(new ToolCallResponse
                {
                    Success = mcpResult.Success,
                    Result = mcpResult.Result,
                    Error = mcpResult.Error,
                    ToolName = request.ToolName,
                    Source = "mcp",
                    ServerName = request.ServerName,
                    DurationMs = mcpResult.DurationMs
                });
            }
            else
            {
                return BadRequest(new ToolCallResponse
                {
                    Success = false,
                    Error = $"Unknown tool source: {request.Source}"
                });
            }

            var duration = (int)(DateTime.UtcNow - startTime).TotalMilliseconds;

            return Ok(new ToolCallResponse
            {
                Success = true,
                Result = result?.ToString(),
                ToolName = request.ToolName,
                Source = request.Source,
                DurationMs = duration
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling tool {ToolName}", request.ToolName);
            return StatusCode(500, new ToolCallResponse
            {
                Success = false,
                Error = ex.Message,
                ToolName = request.ToolName
            });
        }
    }

    #region Private Methods

    private List<ToolInfo> GetLocalTools()
    {
        var tools = new List<ToolInfo>();

        // Scan for tool classes in the Agents.Tools namespace
        var toolTypes = Assembly.GetExecutingAssembly()
            .GetTypes()
            .Where(t => t.Namespace == "DotNetAgentFramework.Agents.Tools" && t.IsClass && !t.IsAbstract);

        foreach (var toolType in toolTypes)
        {
            var methods = toolType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Where(m => !m.IsSpecialName && m.DeclaringType == toolType);

            foreach (var method in methods)
            {
                var description = method.GetCustomAttribute<DescriptionAttribute>()?.Description 
                    ?? $"{method.Name} from {toolType.Name}";

                var parameters = method.GetParameters()
                    .Select(p => new ToolParameter
                    {
                        Name = p.Name ?? "param",
                        Type = p.ParameterType.Name,
                        Description = p.GetCustomAttribute<DescriptionAttribute>()?.Description ?? "",
                        Required = !p.HasDefaultValue
                    })
                    .ToList();

                tools.Add(new ToolInfo
                {
                    Name = method.Name,
                    FullName = $"{toolType.Name}.{method.Name}",
                    Description = description,
                    Source = "local",
                    Category = "local",
                    Transport = "native",
                    ClassName = toolType.Name,
                    Parameters = parameters,
                    Enabled = true
                });
            }
        }

        return tools;
    }

    private async Task<object?> CallLocalToolAsync(string toolName, Dictionary<string, object>? arguments)
    {
        // Find the tool class and method
        var toolTypes = Assembly.GetExecutingAssembly()
            .GetTypes()
            .Where(t => t.Namespace == "DotNetAgentFramework.Agents.Tools" && t.IsClass && !t.IsAbstract);

        foreach (var toolType in toolTypes)
        {
            var method = toolType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .FirstOrDefault(m => m.Name == toolName || $"{toolType.Name}.{m.Name}" == toolName);

            if (method != null)
            {
                // Create instance of the tool class
                var instance = Activator.CreateInstance(toolType);
                
                // Build parameters
                var methodParams = method.GetParameters();
                var invokeArgs = new object?[methodParams.Length];
                
                for (int i = 0; i < methodParams.Length; i++)
                {
                    var param = methodParams[i];
                    if (arguments != null && arguments.TryGetValue(param.Name!, out var argValue))
                    {
                        invokeArgs[i] = Convert.ChangeType(argValue, param.ParameterType);
                    }
                    else if (param.HasDefaultValue)
                    {
                        invokeArgs[i] = param.DefaultValue;
                    }
                    else
                    {
                        throw new ArgumentException($"Missing required parameter: {param.Name}");
                    }
                }

                // Invoke the method
                var result = method.Invoke(instance, invokeArgs);
                
                // Handle async methods
                if (result is Task task)
                {
                    await task;
                    var resultProperty = task.GetType().GetProperty("Result");
                    return resultProperty?.GetValue(task);
                }
                
                return result;
            }
        }

        throw new ArgumentException($"Tool not found: {toolName}");
    }

    private async Task<List<McpServerStatus>> GetMcpServerStatusAsync()
    {
        var statusList = new List<McpServerStatus>();
        
        foreach (var server in _mcpConfig.Value.Servers)
        {
            var status = new McpServerStatus
            {
                Name = server.Name,
                Description = server.Description,
                Transport = server.Transport,
                Endpoint = server.Endpoint,
                Enabled = server.Enabled,
                IsConfigured = server.IsConfigured()  // Call the method
            };
            
            // Try to get connection status
            if (server.Enabled && server.IsConfigured())
            {
                try
                {
                    var testResult = await _mcpClientService.TestConnectionAsync(server.Name);
                    status.IsConnected = testResult.Success;
                    status.ToolCount = testResult.ToolCount;
                    status.ConnectionMessage = testResult.Message ?? testResult.Error;
                }
                catch (Exception ex)
                {
                    status.IsConnected = false;
                    status.ConnectionMessage = ex.Message;
                }
            }
            
            statusList.Add(status);
        }
        
        return statusList;
    }

    private static string GetMcpToolCategory(string serverName, string transport)
    {
        // Categorize based on server name first for more specific categorization
        // Then fall back to transport type
        return serverName switch
        {
            "local-mcp-server" => "mcp-local",
            "remote-mcp-bridge" => "mcp-remote",
            "sample-rest-api-bridge" => "mcp-remote",
            _ when transport?.ToLowerInvariant() == "stdio" => "mcp-local",
            _ when transport?.ToLowerInvariant() == "sse" || transport?.ToLowerInvariant() == "http" => "mcp-remote",
            _ => "mcp-external"
        };
    }

    private static string GetCategoryDisplayName(string category)
    {
        return category switch
        {
            "local" => "?? Local Tools (Native)",
            "mcp-local" => "?? Local MCP (STDIO)",
            "mcp-remote" => "?? Remote MCP (SSE/HTTP)",
            "mcp-stdio" => "?? MCP Server (STDIO)",
            "mcp-sse" => "?? MCP Server (SSE/HTTP)",
            "mcp-bridge" => "?? MCP Bridge",
            "mcp-github" => "?? GitHub MCP",
            "mcp-slack" => "?? Slack MCP",
            "mcp-database" => "??? Database MCP",
            "mcp-external" => "?? External MCP",
            _ => category
        };
    }

    private static int GetCategoryOrder(string category)
    {
        return category switch
        {
            "local" => 0,        // Native local tools first
            "mcp-local" => 1,    // Local MCP (STDIO) second
            "mcp-stdio" => 1,    // Same priority
            "mcp-remote" => 2,   // Remote MCP (SSE) third
            "mcp-sse" => 2,      // Same priority
            "mcp-bridge" => 3,
            _ => 10
        };
    }

    #endregion
}

#region Models

public class ToolsResponse
{
    public bool Success { get; set; }
    public List<ToolInfo> Tools { get; set; } = new();
    public List<ToolCategory>? Categories { get; set; }
    public int TotalCount { get; set; }
    public int LocalCount { get; set; }
    public int McpCount { get; set; }
    public int McpStdioCount { get; set; }
    public int McpSseCount { get; set; }
    public List<McpServerStatus>? ServerStatus { get; set; }
    public string? Message { get; set; }
    public string? Error { get; set; }
    public DateTime Timestamp { get; set; }
}

public class ToolInfo
{
    public string Name { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Source { get; set; } = string.Empty; // "local" or "mcp"
    public string Category { get; set; } = string.Empty;
    public string Transport { get; set; } = string.Empty; // "native", "stdio", "sse", "http"
    public string? ServerName { get; set; }
    public string? ClassName { get; set; }
    public string? InputSchema { get; set; }
    public List<ToolParameter>? Parameters { get; set; }
    public bool Enabled { get; set; } = true;
}

public class ToolParameter
{
    public string Name { get; set; } = string.Empty;
    public string Type { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public bool Required { get; set; }
}

public class ToolCategory
{
    public string Name { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public List<ToolInfo> Tools { get; set; } = new();
    public int Count { get; set; }
}

public class ToolCallRequest
{
    public string ToolName { get; set; } = string.Empty;
    public string Source { get; set; } = "local"; // "local" or "mcp"
    public string? ServerName { get; set; }
    public Dictionary<string, object>? Arguments { get; set; }
}

public class ToolCallResponse
{
    public bool Success { get; set; }
    public string? Result { get; set; }
    public string? Error { get; set; }
    public string? ToolName { get; set; }
    public string? Source { get; set; }
    public string? ServerName { get; set; }
    public int DurationMs { get; set; }
}

public class McpServersResponse
{
    public bool Success { get; set; }
    public List<McpServerStatus> Servers { get; set; } = new();
    public int TotalCount { get; set; }
    public int EnabledCount { get; set; }
    public int StdioCount { get; set; }
    public int SseCount { get; set; }
    public string? Error { get; set; }
    public DateTime Timestamp { get; set; }
}

public class McpServerStatus
{
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Transport { get; set; } = string.Empty;
    public string? Endpoint { get; set; }
    public bool Enabled { get; set; }
    public bool IsConfigured { get; set; }
    public bool IsConnected { get; set; }
    public int ToolCount { get; set; }
    public string? ConnectionMessage { get; set; }
}

#endregion
