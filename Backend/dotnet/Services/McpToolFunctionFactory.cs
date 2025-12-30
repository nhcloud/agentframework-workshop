using Microsoft.Extensions.AI;
using System.ComponentModel;
using System.Text.Json;

namespace DotNetAgentFramework.Services;

/// <summary>
/// Factory for creating AIFunction wrappers around MCP tools.
/// This allows MCP tools to be used with Microsoft.Extensions.AI function calling,
/// enabling the LLM to decide when to call tools (enterprise-style).
/// </summary>
public interface IMcpToolFunctionFactory
{
    /// <summary>
    /// Create AIFunction wrappers for the specified MCP tools
    /// </summary>
    Task<IList<AIFunction>> CreateFunctionsAsync(IEnumerable<SelectedToolInfo> selectedTools, CancellationToken ct = default);
    
    /// <summary>
    /// Create AIFunction wrappers for all tools from a specific MCP server
    /// </summary>
    Task<IList<AIFunction>> CreateFunctionsFromServerAsync(string serverName, CancellationToken ct = default);
}

public class McpToolFunctionFactory : IMcpToolFunctionFactory
{
    private readonly IMcpClientService _mcpClientService;
    private readonly ILogger<McpToolFunctionFactory> _logger;

    public McpToolFunctionFactory(
        IMcpClientService mcpClientService,
        ILogger<McpToolFunctionFactory> logger)
    {
        _mcpClientService = mcpClientService;
        _logger = logger;
    }

    public async Task<IList<AIFunction>> CreateFunctionsAsync(IEnumerable<SelectedToolInfo> selectedTools, CancellationToken ct = default)
    {
        var functions = new List<AIFunction>();
        
        foreach (var tool in selectedTools)
        {
            // Skip local tools - they're already registered with the agent
            if (tool.Source == "local")
            {
                _logger.LogDebug("Skipping local tool {Tool} - handled by agent", tool.Name);
                continue;
            }

            if (tool.Source != "mcp" || string.IsNullOrEmpty(tool.ServerName))
            {
                _logger.LogWarning("Invalid MCP tool configuration for {Tool}", tool.Name);
                continue;
            }

            try
            {
                var function = CreateMcpToolFunction(tool);
                functions.Add(function);
                _logger.LogInformation("Created AIFunction wrapper for MCP tool: {Server}.{Tool}", 
                    tool.ServerName, tool.Name);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to create AIFunction for MCP tool {Tool}", tool.Name);
            }
        }

        return await Task.FromResult(functions);
    }

    public async Task<IList<AIFunction>> CreateFunctionsFromServerAsync(string serverName, CancellationToken ct = default)
    {
        var functions = new List<AIFunction>();
        
        try
        {
            var tools = await _mcpClientService.GetToolsAsync(serverName);
            
            foreach (var tool in tools)
            {
                var selectedTool = new SelectedToolInfo
                {
                    Name = tool.Name,
                    FullName = tool.FullName,
                    Source = "mcp",
                    ServerName = serverName,
                    Transport = "sse" // default
                };

                var function = CreateMcpToolFunction(selectedTool, tool.Description, tool.InputSchema);
                functions.Add(function);
                _logger.LogDebug("Created AIFunction for {Tool} from server {Server}", tool.Name, serverName);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create AIFunctions from server {Server}", serverName);
        }

        return functions;
    }

    /// <summary>
    /// Create an AIFunction that wraps an MCP tool call
    /// </summary>
    private AIFunction CreateMcpToolFunction(SelectedToolInfo tool, string? description = null, string? inputSchema = null)
    {
        var toolName = tool.Name;
        var serverName = tool.ServerName!;
        var toolDescription = description ?? GetToolDescription(toolName);

        // Create a delegate that calls the MCP tool
        Func<Dictionary<string, object?>?, Task<string>> toolInvoker = async (args) =>
        {
            _logger.LogInformation("AIFunction invoking MCP tool: {Server}.{Tool} with args: {Args}",
                serverName, toolName, args != null ? JsonSerializer.Serialize(args) : "none");

            try
            {
                // Convert nullable dict to non-nullable for MCP service
                var mcpArgs = args?.Where(kvp => kvp.Value != null)
                    .ToDictionary(kvp => kvp.Key, kvp => kvp.Value!);

                var result = await _mcpClientService.CallToolAsync(serverName, toolName, mcpArgs);

                if (result.Success)
                {
                    _logger.LogInformation("MCP tool {Tool} succeeded: {Length} chars", 
                        toolName, result.Result?.Length ?? 0);
                    return result.Result ?? "Tool executed successfully but returned no data.";
                }
                else
                {
                    _logger.LogWarning("MCP tool {Tool} failed: {Error}", toolName, result.Error);
                    return $"Error: {result.Error}";
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Exception calling MCP tool {Tool}", toolName);
                return $"Error calling tool: {ex.Message}";
            }
        };

        // Build the AIFunction with proper metadata
        // Use AIFunctionFactory to create a properly typed function
        var function = AIFunctionFactory.Create(
            method: async (string? argsJson) =>
            {
                Dictionary<string, object?>? args = null;
                if (!string.IsNullOrEmpty(argsJson))
                {
                    try
                    {
                        args = JsonSerializer.Deserialize<Dictionary<string, object?>>(argsJson);
                    }
                    catch
                    {
                        // If not JSON, treat as a single parameter
                        args = new Dictionary<string, object?> { ["input"] = argsJson };
                    }
                }
                return await toolInvoker(args);
            },
            name: toolName,
            description: toolDescription
        );

        return function;
    }

    /// <summary>
    /// Get a description for a tool based on its name
    /// </summary>
    private static string GetToolDescription(string toolName)
    {
        return toolName.ToLowerInvariant() switch
        {
            "get_all_employees" => "Get a list of all employees in the system. Returns employee names, IDs, departments, and contact information.",
            "get_employee" => "Get details for a specific employee by their ID. Requires an 'id' parameter.",
            "search_employees" => "Search for employees by name, department, or other criteria. Requires a 'query' parameter.",
            "get_all_products" => "Get a list of all products in the catalog. Returns product names, prices, and availability.",
            "get_product" => "Get details for a specific product by its ID. Requires an 'id' parameter.",
            "get_products_by_category" => "Get all products in a specific category. Requires a 'category' parameter.",
            "get_all_orders" => "Get a list of all orders. Returns order details including status and items.",
            "get_order" => "Get details for a specific order by its ID. Requires an 'id' parameter.",
            "create_order" => "Create a new order. Requires order details as parameters.",
            "get_customer_orders" => "Get all orders for a specific customer. Requires a 'customerId' parameter.",
            "get_weather" => "Get current weather information for a location. Requires a 'location' parameter.",
            "get_weather_locations" => "Get a list of available weather locations.",
            "get_inventory" => "Get current inventory/stock levels for products.",
            "update_stock" => "Update the stock level for a product. Requires 'productId' and 'quantity' parameters.",
            "check_api_health" => "Check the health status of the API.",
            _ => $"Execute the {toolName} operation via MCP."
        };
    }
}
