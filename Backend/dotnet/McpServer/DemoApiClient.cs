using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace DotNetAgentFramework.McpServer;

/// <summary>
/// HTTP client for calling the SampleRestApi endpoints.
/// Note: Despite the name "DemoApiClient", this now calls SampleRestApi on port 5001.
/// </summary>
public class DemoApiClient
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<DemoApiClient> _logger;
    private readonly string _authToken;

    public DemoApiClient(
        IHttpClientFactory httpClientFactory,
        ILogger<DemoApiClient> logger,
        IConfiguration configuration)
    {
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _authToken = configuration["DEMO_API_AUTH_TOKEN"] ?? "Bearer demo-token-12345";
    }

    private HttpClient CreateClient()
    {
        return _httpClientFactory.CreateClient("DemoApi");
    }

    // ???????????????????????????????????????????????????????????????????????????
    // EMPLOYEE ENDPOINTS - SampleRestApi paths
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetEmployeesAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/employees");
        
        var response = await client.GetAsync("/api/employees");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetEmployeeAsync(int id)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/employees/{Id}", id);
        
        var response = await client.GetAsync($"/api/employees/{id}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> SearchEmployeesAsync(string? name = null, string? department = null)
    {
        var client = CreateClient();
        
        var queryParams = new List<string>();
        if (!string.IsNullOrEmpty(name))
            queryParams.Add($"name={Uri.EscapeDataString(name)}");
        if (!string.IsNullOrEmpty(department))
            queryParams.Add($"department={Uri.EscapeDataString(department)}");

        var url = "/api/employees/search";
        if (queryParams.Any())
            url += "?" + string.Join("&", queryParams);

        _logger.LogInformation("Calling SampleRestApi: GET {Url}", url);
        
        var response = await client.GetAsync(url);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // PRODUCT ENDPOINTS - SampleRestApi paths
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetProductsAsync(string? category = null, decimal? minPrice = null, decimal? maxPrice = null)
    {
        var client = CreateClient();
        
        // SampleRestApi uses /api/products for all products
        // and /api/products/category/{category} for filtered
        string url;
        if (!string.IsNullOrEmpty(category))
        {
            url = $"/api/products/category/{Uri.EscapeDataString(category)}";
        }
        else
        {
            url = "/api/products";
        }

        _logger.LogInformation("Calling SampleRestApi: GET {Url}", url);
        
        var response = await client.GetAsync(url);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetProductAsync(int id)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/products/{Id}", id);
        
        var response = await client.GetAsync($"/api/products/{id}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // ORDER ENDPOINTS - SampleRestApi paths
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetOrdersAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/orders");
        
        var response = await client.GetAsync("/api/orders");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> CreateOrderAsync(string customerId, int productId, int quantity, string? notes = null)
    {
        var client = CreateClient();
        
        // SampleRestApi expects customerId as int and productIds as array
        int customerIdInt = 0;
        if (customerId.StartsWith("CUST", StringComparison.OrdinalIgnoreCase))
        {
            int.TryParse(customerId.Replace("CUST", "").Trim('0'), out customerIdInt);
        }
        else
        {
            int.TryParse(customerId, out customerIdInt);
        }

        var orderRequest = new
        {
            customerId = customerIdInt,
            productIds = new List<int> { productId }
        };

        _logger.LogInformation("Calling SampleRestApi: POST /api/orders with {Request}", JsonSerializer.Serialize(orderRequest));
        
        var response = await client.PostAsJsonAsync("/api/orders", orderRequest);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetOrderAsync(string id)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/orders/{Id}", id);
        
        var response = await client.GetAsync($"/api/orders/{Uri.EscapeDataString(id)}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetCustomerOrdersAsync(string customerId)
    {
        var client = CreateClient();
        
        // SampleRestApi doesn't have customer-specific orders endpoint
        // Get all orders (in real app, you'd filter or add the endpoint)
        _logger.LogInformation("Calling SampleRestApi: GET /api/orders (filtering for customer {CustomerId})", customerId);
        
        var response = await client.GetAsync("/api/orders");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // INVENTORY ENDPOINTS - SampleRestApi paths
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetInventoryAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/inventory");
        
        var response = await client.GetAsync("/api/inventory");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> UpdateStockAsync(int productId, int newStock)
    {
        var client = CreateClient();
        
        var request = new { newStock };
        
        _logger.LogInformation("Calling SampleRestApi: PUT /api/inventory/{ProductId}/stock", productId);
        
        var response = await client.PutAsJsonAsync($"/api/inventory/{productId}/stock", request);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // HEALTH CHECK
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> HealthCheckAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling SampleRestApi: GET /api/health");
        
        var response = await client.GetAsync("/api/health");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }
}
