using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Text.Json;

namespace DotNetAgentFramework.McpServer.Tools;

/// <summary>
/// MCP Tools that expose a remote REST API
/// 
/// This is a template showing how to wrap any REST API as MCP tools.
/// Customize the tool methods to match your specific API endpoints.
/// 
/// Configuration in appsettings.json:
/// {
///   "RemoteApi": {
///     "BaseUrl": "https://your-api.example.com",
///     "AuthToken": "Bearer your-token",
///     "Headers": {
///       "X-Api-Key": "your-key"
///     }
///   }
/// }
/// </summary>
[McpServerToolType]
public class RemoteApiTools
{
    private readonly RemoteApiClient _apiClient;

    public RemoteApiTools(RemoteApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    // ???????????????????????????????????????????????????????????????????????
    // EXAMPLE TOOLS - Customize these for your specific REST API
    // ???????????????????????????????????????????????????????????????????????

    /// <summary>
    /// List all resources from the remote API
    /// </summary>
    [McpServerTool(Name = "list_resources")]
    [Description("List all resources from the remote API with optional filtering")]
    public async Task<string> ListResources(
        [Description("Filter by type (optional)")] string? type = null,
        [Description("Filter by status (optional)")] string? status = null,
        [Description("Maximum number of results")] int? limit = null)
    {
        try
        {
            var queryParams = new Dictionary<string, string>();
            if (!string.IsNullOrEmpty(type)) queryParams["type"] = type;
            if (!string.IsNullOrEmpty(status)) queryParams["status"] = status;
            if (limit.HasValue) queryParams["limit"] = limit.Value.ToString();

            var result = await _apiClient.GetAsync("/api/resources", queryParams);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("list_resources", ex);
        }
    }

    /// <summary>
    /// Get a specific resource by ID
    /// </summary>
    [McpServerTool(Name = "get_resource")]
    [Description("Get detailed information about a specific resource by its ID")]
    public async Task<string> GetResource(
        [Description("The unique resource ID")] string id)
    {
        try
        {
            var result = await _apiClient.GetAsync($"/api/resources/{id}");
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_resource", ex);
        }
    }

    /// <summary>
    /// Create a new resource
    /// </summary>
    [McpServerTool(Name = "create_resource")]
    [Description("Create a new resource in the remote system")]
    public async Task<string> CreateResource(
        [Description("Name of the resource")] string name,
        [Description("Type of resource")] string type,
        [Description("Description (optional)")] string? description = null,
        [Description("Additional properties as JSON (optional)")] string? propertiesJson = null)
    {
        try
        {
            var body = new Dictionary<string, object>
            {
                ["name"] = name,
                ["type"] = type
            };
            
            if (!string.IsNullOrEmpty(description))
                body["description"] = description;
            
            if (!string.IsNullOrEmpty(propertiesJson))
            {
                var properties = JsonSerializer.Deserialize<Dictionary<string, object>>(propertiesJson);
                if (properties != null)
                    body["properties"] = properties;
            }

            var result = await _apiClient.PostAsync("/api/resources", body);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("create_resource", ex);
        }
    }

    /// <summary>
    /// Update an existing resource
    /// </summary>
    [McpServerTool(Name = "update_resource")]
    [Description("Update an existing resource")]
    public async Task<string> UpdateResource(
        [Description("The resource ID to update")] string id,
        [Description("New name (optional)")] string? name = null,
        [Description("New status (optional)")] string? status = null,
        [Description("New description (optional)")] string? description = null)
    {
        try
        {
            var body = new Dictionary<string, object>();
            
            if (!string.IsNullOrEmpty(name)) body["name"] = name;
            if (!string.IsNullOrEmpty(status)) body["status"] = status;
            if (!string.IsNullOrEmpty(description)) body["description"] = description;

            var result = await _apiClient.PutAsync($"/api/resources/{id}", body);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("update_resource", ex);
        }
    }

    /// <summary>
    /// Delete a resource
    /// </summary>
    [McpServerTool(Name = "delete_resource")]
    [Description("Delete a resource by ID")]
    public async Task<string> DeleteResource(
        [Description("The resource ID to delete")] string id)
    {
        try
        {
            var result = await _apiClient.DeleteAsync($"/api/resources/{id}");
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("delete_resource", ex);
        }
    }

    /// <summary>
    /// Search resources
    /// </summary>
    [McpServerTool(Name = "search_resources")]
    [Description("Search for resources using a query")]
    public async Task<string> SearchResources(
        [Description("Search query")] string query,
        [Description("Fields to search in (comma-separated, optional)")] string? fields = null,
        [Description("Maximum results")] int limit = 10)
    {
        try
        {
            var queryParams = new Dictionary<string, string>
            {
                ["q"] = query,
                ["limit"] = limit.ToString()
            };
            
            if (!string.IsNullOrEmpty(fields))
                queryParams["fields"] = fields;

            var result = await _apiClient.GetAsync("/api/resources/search", queryParams);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("search_resources", ex);
        }
    }

    /// <summary>
    /// Execute a custom API call (for advanced use)
    /// </summary>
    [McpServerTool(Name = "custom_api_call")]
    [Description("Execute a custom API call to any endpoint")]
    public async Task<string> CustomApiCall(
        [Description("HTTP method (GET, POST, PUT, DELETE)")] string method,
        [Description("API endpoint path (e.g., /api/custom/endpoint)")] string endpoint,
        [Description("Request body as JSON (for POST/PUT)")] string? bodyJson = null,
        [Description("Query parameters as JSON (e.g., {\"key\":\"value\"})")] string? queryParamsJson = null)
    {
        try
        {
            Dictionary<string, string>? queryParams = null;
            if (!string.IsNullOrEmpty(queryParamsJson))
            {
                queryParams = JsonSerializer.Deserialize<Dictionary<string, string>>(queryParamsJson);
            }

            object? body = null;
            if (!string.IsNullOrEmpty(bodyJson))
            {
                body = JsonSerializer.Deserialize<Dictionary<string, object>>(bodyJson);
            }

            JsonElement? result = method.ToUpperInvariant() switch
            {
                "GET" => await _apiClient.GetAsync(endpoint, queryParams),
                "POST" => await _apiClient.PostAsync(endpoint, body),
                "PUT" => await _apiClient.PutAsync(endpoint, body),
                "DELETE" => await _apiClient.DeleteAsync(endpoint),
                _ => throw new ArgumentException($"Unsupported HTTP method: {method}")
            };

            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("custom_api_call", ex);
        }
    }

    /// <summary>
    /// Check the health/status of the remote API
    /// </summary>
    [McpServerTool(Name = "api_health_check")]
    [Description("Check the health status of the remote API")]
    public async Task<string> ApiHealthCheck()
    {
        try
        {
            // Try common health endpoints
            JsonElement? result = null;
            
            try
            {
                result = await _apiClient.GetAsync("/health");
            }
            catch
            {
                try
                {
                    result = await _apiClient.GetAsync("/api/health");
                }
                catch
                {
                    result = await _apiClient.GetAsync("/status");
                }
            }

            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("api_health_check", ex);
        }
    }

    private static string FormatResponse(JsonElement? response)
    {
        if (response == null)
        {
            return JsonSerializer.Serialize(new { success = false, error = "No response received" });
        }

        return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
    }

    private static string FormatError(string toolName, Exception ex)
    {
        return JsonSerializer.Serialize(new
        {
            success = false,
            tool = toolName,
            error = ex.Message,
            errorType = ex.GetType().Name
        }, new JsonSerializerOptions { WriteIndented = true });
    }
}
