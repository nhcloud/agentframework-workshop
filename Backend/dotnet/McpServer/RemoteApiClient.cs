using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace DotNetAgentFramework.McpServer;

/// <summary>
/// Generic HTTP client for calling remote REST APIs
/// Configure via appsettings.json or environment variables
/// </summary>
public class RemoteApiClient
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<RemoteApiClient> _logger;
    private readonly string _baseUrl;
    private readonly string? _authToken;
    private readonly Dictionary<string, string> _defaultHeaders;

    public RemoteApiClient(
        IHttpClientFactory httpClientFactory,
        ILogger<RemoteApiClient> logger,
        IConfiguration configuration)
    {
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        
        // Load configuration
        _baseUrl = configuration["RemoteApi:BaseUrl"] ?? 
                   configuration["REMOTE_API_BASE_URL"] ?? 
                   throw new InvalidOperationException("RemoteApi:BaseUrl is required");
        
        _authToken = configuration["RemoteApi:AuthToken"] ?? 
                     configuration["REMOTE_API_AUTH_TOKEN"];
        
        _defaultHeaders = new Dictionary<string, string>();
        
        // Load custom headers from configuration
        var headersSection = configuration.GetSection("RemoteApi:Headers");
        if (headersSection.Exists())
        {
            foreach (var header in headersSection.GetChildren())
            {
                _defaultHeaders[header.Key] = header.Value ?? "";
            }
        }
    }

    private HttpClient CreateClient()
    {
        var client = _httpClientFactory.CreateClient("RemoteApi");
        client.BaseAddress = new Uri(_baseUrl);
        client.DefaultRequestHeaders.Add("Accept", "application/json");
        
        if (!string.IsNullOrEmpty(_authToken))
        {
            client.DefaultRequestHeaders.Add("Authorization", _authToken);
        }
        
        foreach (var header in _defaultHeaders)
        {
            client.DefaultRequestHeaders.Add(header.Key, header.Value);
        }
        
        return client;
    }

    /// <summary>
    /// Generic GET request
    /// </summary>
    public async Task<JsonElement?> GetAsync(string endpoint, Dictionary<string, string>? queryParams = null)
    {
        var client = CreateClient();
        
        var url = endpoint;
        if (queryParams?.Any() == true)
        {
            var queryString = string.Join("&", queryParams.Select(kvp => 
                $"{Uri.EscapeDataString(kvp.Key)}={Uri.EscapeDataString(kvp.Value)}"));
            url = $"{endpoint}?{queryString}";
        }

        _logger.LogInformation("Calling Remote API: GET {Url}", url);
        
        var response = await client.GetAsync(url);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    /// <summary>
    /// Generic POST request
    /// </summary>
    public async Task<JsonElement?> PostAsync(string endpoint, object? body = null)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Remote API: POST {Endpoint}", endpoint);
        
        HttpResponseMessage response;
        if (body != null)
        {
            response = await client.PostAsJsonAsync(endpoint, body);
        }
        else
        {
            response = await client.PostAsync(endpoint, null);
        }
        
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    /// <summary>
    /// Generic PUT request
    /// </summary>
    public async Task<JsonElement?> PutAsync(string endpoint, object? body = null)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Remote API: PUT {Endpoint}", endpoint);
        
        HttpResponseMessage response;
        if (body != null)
        {
            response = await client.PutAsJsonAsync(endpoint, body);
        }
        else
        {
            response = await client.PutAsync(endpoint, null);
        }
        
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    /// <summary>
    /// Generic DELETE request
    /// </summary>
    public async Task<JsonElement?> DeleteAsync(string endpoint)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Remote API: DELETE {Endpoint}", endpoint);
        
        var response = await client.DeleteAsync(endpoint);
        response.EnsureSuccessStatusCode();
        
        var content = await response.Content.ReadAsStringAsync();
        if (string.IsNullOrEmpty(content))
        {
            return JsonSerializer.Deserialize<JsonElement>("{\"success\": true}");
        }
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }
}
