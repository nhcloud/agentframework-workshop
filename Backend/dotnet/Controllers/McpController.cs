using DotNetAgentFramework.Services;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;

namespace DotNetAgentFramework.Controllers;

/// <summary>
/// MCP (Model Context Protocol) Controller
/// Provides endpoints for managing MCP server connections and calling MCP tools
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class McpController : ControllerBase
{
    private readonly IMcpClientService _mcpClientService;
    private readonly ILogger<McpController> _logger;

    public McpController(
        IMcpClientService mcpClientService,
        ILogger<McpController> logger)
    {
        _mcpClientService = mcpClientService;
        _logger = logger;
    }

    /// <summary>
    /// Get all configured MCP servers
    /// </summary>
    [HttpGet("servers")]
    [ProducesResponseType(typeof(McpApiResponse<IEnumerable<McpServerInfo>>), 200)]
    public async Task<ActionResult<McpApiResponse<IEnumerable<McpServerInfo>>>> GetServers()
    {
        try
        {
            var servers = await _mcpClientService.GetConfiguredServersAsync();
            
            return Ok(new McpApiResponse<IEnumerable<McpServerInfo>>
            {
                Success = true,
                Data = servers,
                Message = $"Found {servers.Count()} configured MCP servers",
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting MCP servers");
            return StatusCode(500, new McpApiResponse<IEnumerable<McpServerInfo>>
            {
                Success = false,
                Message = "Error retrieving MCP servers",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Get available tools from a specific MCP server
    /// </summary>
    [HttpGet("servers/{serverName}/tools")]
    [ProducesResponseType(typeof(McpApiResponse<IEnumerable<McpToolInfo>>), 200)]
    [ProducesResponseType(404)]
    public async Task<ActionResult<McpApiResponse<IEnumerable<McpToolInfo>>>> GetServerTools(string serverName)
    {
        try
        {
            var tools = await _mcpClientService.GetToolsAsync(serverName);
            
            return Ok(new McpApiResponse<IEnumerable<McpToolInfo>>
            {
                Success = true,
                Data = tools,
                Message = $"Found {tools.Count()} tools on server '{serverName}'",
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting tools from MCP server {ServerName}", serverName);
            return StatusCode(500, new McpApiResponse<IEnumerable<McpToolInfo>>
            {
                Success = false,
                Message = $"Error retrieving tools from server '{serverName}'",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Get all available tools from all configured MCP servers
    /// </summary>
    [HttpGet("tools")]
    [ProducesResponseType(typeof(McpApiResponse<IEnumerable<McpToolInfo>>), 200)]
    public async Task<ActionResult<McpApiResponse<IEnumerable<McpToolInfo>>>> GetAllTools()
    {
        try
        {
            var tools = await _mcpClientService.GetAllToolsAsync();
            
            var groupedByServer = tools.GroupBy(t => t.ServerName)
                .Select(g => new { Server = g.Key, ToolCount = g.Count() })
                .ToList();

            return Ok(new McpApiResponse<IEnumerable<McpToolInfo>>
            {
                Success = true,
                Data = tools,
                Message = $"Found {tools.Count()} tools across {groupedByServer.Count} servers",
                Timestamp = DateTime.UtcNow,
                Metadata = new Dictionary<string, object>
                {
                    ["toolsByServer"] = groupedByServer
                }
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting all MCP tools");
            return StatusCode(500, new McpApiResponse<IEnumerable<McpToolInfo>>
            {
                Success = false,
                Message = "Error retrieving MCP tools",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Call a tool on an MCP server
    /// </summary>
    [HttpPost("servers/{serverName}/tools/{toolName}/call")]
    [ProducesResponseType(typeof(McpApiResponse<McpToolResult>), 200)]
    [ProducesResponseType(400)]
    public async Task<ActionResult<McpApiResponse<McpToolResult>>> CallTool(
        string serverName,
        string toolName,
        [FromBody] McpCallToolRequest? request = null)
    {
        try
        {
            _logger.LogInformation("Calling MCP tool {ToolName} on server {ServerName}", toolName, serverName);
            
            var result = await _mcpClientService.CallToolAsync(serverName, toolName, request?.Arguments);
            
            return Ok(new McpApiResponse<McpToolResult>
            {
                Success = result.Success,
                Data = result,
                Message = result.Success ? "Tool executed successfully" : "Tool execution failed",
                Error = result.Error,
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling MCP tool {ToolName} on server {ServerName}", toolName, serverName);
            return StatusCode(500, new McpApiResponse<McpToolResult>
            {
                Success = false,
                Message = "Error calling MCP tool",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Call a tool using full name (server.tool format)
    /// </summary>
    [HttpPost("tools/call")]
    [ProducesResponseType(typeof(McpApiResponse<McpToolResult>), 200)]
    [ProducesResponseType(400)]
    public async Task<ActionResult<McpApiResponse<McpToolResult>>> CallToolByFullName(
        [FromBody] McpCallToolByFullNameRequest request)
    {
        if (string.IsNullOrEmpty(request.ToolName))
        {
            return BadRequest(new McpApiResponse<McpToolResult>
            {
                Success = false,
                Message = "Tool name is required",
                Timestamp = DateTime.UtcNow
            });
        }

        try
        {
            _logger.LogInformation("Calling MCP tool by full name: {ToolName}", request.ToolName);
            
            var result = await _mcpClientService.CallToolByFullNameAsync(request.ToolName, request.Arguments);
            
            return Ok(new McpApiResponse<McpToolResult>
            {
                Success = result.Success,
                Data = result,
                Message = result.Success ? "Tool executed successfully" : "Tool execution failed",
                Error = result.Error,
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling MCP tool by full name: {ToolName}", request.ToolName);
            return StatusCode(500, new McpApiResponse<McpToolResult>
            {
                Success = false,
                Message = "Error calling MCP tool",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Test connection to an MCP server
    /// </summary>
    [HttpGet("servers/{serverName}/test")]
    [ProducesResponseType(typeof(McpApiResponse<McpConnectionTestResult>), 200)]
    public async Task<ActionResult<McpApiResponse<McpConnectionTestResult>>> TestConnection(string serverName)
    {
        try
        {
            _logger.LogInformation("Testing connection to MCP server: {ServerName}", serverName);
            
            var result = await _mcpClientService.TestConnectionAsync(serverName);
            
            return Ok(new McpApiResponse<McpConnectionTestResult>
            {
                Success = result.Success,
                Data = result,
                Message = result.Success ? "Connection successful" : "Connection failed",
                Error = result.Error,
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error testing connection to MCP server {ServerName}", serverName);
            return StatusCode(500, new McpApiResponse<McpConnectionTestResult>
            {
                Success = false,
                Message = "Error testing MCP connection",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Get resources from an MCP server
    /// </summary>
    [HttpGet("servers/{serverName}/resources")]
    [ProducesResponseType(typeof(McpApiResponse<IEnumerable<McpResourceInfo>>), 200)]
    public async Task<ActionResult<McpApiResponse<IEnumerable<McpResourceInfo>>>> GetResources(string serverName)
    {
        try
        {
            var resources = await _mcpClientService.GetResourcesAsync(serverName);
            
            return Ok(new McpApiResponse<IEnumerable<McpResourceInfo>>
            {
                Success = true,
                Data = resources,
                Message = $"Found {resources.Count()} resources on server '{serverName}'",
                Timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting resources from MCP server {ServerName}", serverName);
            return StatusCode(500, new McpApiResponse<IEnumerable<McpResourceInfo>>
            {
                Success = false,
                Message = $"Error retrieving resources from server '{serverName}'",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    /// <summary>
    /// Demo endpoint: Simulate calling the local Demo API through MCP-like interface
    /// This demonstrates how an agent could interact with REST endpoints as if they were MCP tools
    /// </summary>
    [HttpPost("demo/simulate")]
    [ProducesResponseType(typeof(McpApiResponse<object>), 200)]
    public async Task<ActionResult<McpApiResponse<object>>> SimulateMcpCall([FromBody] McpDemoSimulateRequest request)
    {
        try
        {
            _logger.LogInformation("Simulating MCP call to Demo API: {Operation}", request.Operation);

            object? result = request.Operation.ToLowerInvariant() switch
            {
                "get_products" => await SimulateGetProducts(request.Arguments),
                "get_product" => await SimulateGetProduct(request.Arguments),
                "create_order" => await SimulateCreateOrder(request.Arguments),
                "get_order" => await SimulateGetOrder(request.Arguments),
                _ => throw new ArgumentException($"Unknown operation: {request.Operation}")
            };

            return Ok(new McpApiResponse<object>
            {
                Success = true,
                Data = result,
                Message = $"Successfully executed operation: {request.Operation}",
                Timestamp = DateTime.UtcNow,
                Metadata = new Dictionary<string, object>
                {
                    ["operation"] = request.Operation,
                    ["simulatedMcp"] = true
                }
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error simulating MCP call: {Operation}", request.Operation);
            return StatusCode(500, new McpApiResponse<object>
            {
                Success = false,
                Message = $"Error executing operation: {request.Operation}",
                Error = ex.Message,
                Timestamp = DateTime.UtcNow
            });
        }
    }

    #region Demo Simulation Methods

    private Task<object> SimulateGetProducts(Dictionary<string, object>? arguments)
    {
        // Simulate querying the local "database"
        var products = new List<object>
        {
            new { id = 1, name = "Laptop Pro", category = "Electronics", price = 1299.99m, stock = 50 },
            new { id = 2, name = "Wireless Mouse", category = "Electronics", price = 49.99m, stock = 200 },
            new { id = 3, name = "Office Chair", category = "Furniture", price = 399.99m, stock = 30 }
        };

        // Apply category filter if provided
        if (arguments?.TryGetValue("category", out var category) == true && category != null)
        {
            var categoryStr = category.ToString();
            products = products.Where(p => 
            {
                var dict = (IDictionary<string, object>)p;
                return dict["category"]?.ToString()?.Equals(categoryStr, StringComparison.OrdinalIgnoreCase) == true;
            }).ToList();
        }

        return Task.FromResult<object>(new
        {
            success = true,
            products,
            count = products.Count,
            source = "simulated_local_database"
        });
    }

    private Task<object> SimulateGetProduct(Dictionary<string, object>? arguments)
    {
        if (arguments?.TryGetValue("id", out var idObj) != true)
        {
            throw new ArgumentException("Product ID is required");
        }

        var id = Convert.ToInt32(idObj);
        
        // Simulate product lookup
        var product = id switch
        {
            1 => new { id = 1, name = "Laptop Pro", category = "Electronics", price = 1299.99m, stock = 50, description = "High-performance laptop" },
            2 => new { id = 2, name = "Wireless Mouse", category = "Electronics", price = 49.99m, stock = 200, description = "Ergonomic wireless mouse" },
            3 => new { id = 3, name = "Office Chair", category = "Furniture", price = 399.99m, stock = 30, description = "Comfortable office chair" },
            _ => (object?)null
        };

        if (product == null)
        {
            throw new KeyNotFoundException($"Product with ID {id} not found");
        }

        return Task.FromResult<object>(new
        {
            success = true,
            product,
            source = "simulated_local_database"
        });
    }

    private Task<object> SimulateCreateOrder(Dictionary<string, object>? arguments)
    {
        if (arguments == null)
        {
            throw new ArgumentException("Order details are required");
        }

        var customerId = arguments.TryGetValue("customerId", out var cid) ? cid?.ToString() : "UNKNOWN";
        var productId = arguments.TryGetValue("productId", out var pid) ? Convert.ToInt32(pid) : 0;
        var quantity = arguments.TryGetValue("quantity", out var qty) ? Convert.ToInt32(qty) : 1;

        // Simulate order creation
        var orderId = new Random().Next(1000, 9999);
        var totalAmount = productId switch
        {
            1 => 1299.99m * quantity,
            2 => 49.99m * quantity,
            3 => 399.99m * quantity,
            _ => 0m
        };

        return Task.FromResult<object>(new
        {
            success = true,
            order = new
            {
                id = orderId,
                customerId,
                productId,
                quantity,
                status = "Processing",
                orderDate = DateTime.UtcNow,
                totalAmount
            },
            source = "simulated_local_database"
        });
    }

    private Task<object> SimulateGetOrder(Dictionary<string, object>? arguments)
    {
        if (arguments?.TryGetValue("id", out var idObj) != true)
        {
            throw new ArgumentException("Order ID is required");
        }

        var id = Convert.ToInt32(idObj);

        // Simulate order lookup
        return Task.FromResult<object>(new
        {
            success = true,
            order = new
            {
                id,
                customerId = "CUST001",
                productId = 1,
                quantity = 1,
                status = "Completed",
                orderDate = DateTime.UtcNow.AddDays(-3),
                totalAmount = 1299.99m
            },
            source = "simulated_local_database"
        });
    }

    #endregion
}

#region MCP Request/Response Models

public class McpApiResponse<T>
{
    public bool Success { get; set; }
    public T? Data { get; set; }
    public string Message { get; set; } = string.Empty;
    public string? Error { get; set; }
    public DateTime Timestamp { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
}

public class McpCallToolRequest
{
    public Dictionary<string, object>? Arguments { get; set; }
}

public class McpCallToolByFullNameRequest
{
    public string ToolName { get; set; } = string.Empty;
    public Dictionary<string, object>? Arguments { get; set; }
}

public class McpDemoSimulateRequest
{
    /// <summary>
    /// Operation to execute: get_products, get_product, create_order, get_order
    /// </summary>
    public string Operation { get; set; } = string.Empty;
    
    /// <summary>
    /// Arguments for the operation
    /// </summary>
    public Dictionary<string, object>? Arguments { get; set; }
}

#endregion
