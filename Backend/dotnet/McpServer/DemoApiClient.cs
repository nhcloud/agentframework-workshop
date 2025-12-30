using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace DotNetAgentFramework.McpServer;

/// <summary>
/// HTTP client for calling the Demo API endpoints on the main DotNetAgentFramework API (port 8000).
/// This calls /api/demo/* endpoints defined in DemoController.
/// 
/// For SampleRestApi (port 5001) which has /api/employees, /api/products, etc.,
/// use RemoteApiClient instead.
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
    // WEATHER ENDPOINTS - /api/demo/weather
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetWeatherAsync(string location)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/weather?location={Location}", location);
        
        var response = await client.GetAsync($"/api/demo/weather?location={Uri.EscapeDataString(location)}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetWeatherLocationsAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/weather/locations");
        
        var response = await client.GetAsync("/api/demo/weather/locations");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // PRODUCT ENDPOINTS - /api/demo/products
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetProductsAsync(string? category = null, decimal? minPrice = null, decimal? maxPrice = null)
    {
        var client = CreateClient();
        
        var queryParams = new List<string>();
        if (!string.IsNullOrEmpty(category))
            queryParams.Add($"category={Uri.EscapeDataString(category)}");
        if (minPrice.HasValue)
            queryParams.Add($"minPrice={minPrice.Value}");
        if (maxPrice.HasValue)
            queryParams.Add($"maxPrice={maxPrice.Value}");

        var url = "/api/demo/products";
        if (queryParams.Any())
            url += "?" + string.Join("&", queryParams);

        _logger.LogInformation("Calling Demo API: GET {Url}", url);
        
        var response = await client.GetAsync(url);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetProductAsync(int id)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/products/{Id}", id);
        
        var response = await client.GetAsync($"/api/demo/products/{id}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // ORDER ENDPOINTS - /api/demo/orders
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetOrdersAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/orders (not available - returning empty)");
        
        // Note: DemoController doesn't have a "get all orders" endpoint
        // Return a simulated response
        return JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
        {
            success = true,
            message = "Orders list not available via Demo API. Use get_order or get_customer_orders instead.",
            data = new object[] { }
        }));
    }

    public async Task<JsonElement?> CreateOrderAsync(string customerId, int productId, int quantity, string? notes = null)
    {
        var client = CreateClient();
        
        var orderRequest = new
        {
            customerId,
            productId,
            quantity,
            notes
        };

        _logger.LogInformation("Calling Demo API: POST /api/demo/orders with {Request}", JsonSerializer.Serialize(orderRequest));
        
        var response = await client.PostAsJsonAsync("/api/demo/orders", orderRequest);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetOrderAsync(string id)
    {
        var client = CreateClient();
        
        // DemoController uses int for order ID
        if (!int.TryParse(id.Replace("ORD-", "").Split('-').LastOrDefault() ?? id, out var orderId))
        {
            int.TryParse(id, out orderId);
        }
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/orders/{Id}", orderId);
        
        var response = await client.GetAsync($"/api/demo/orders/{orderId}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public async Task<JsonElement?> GetCustomerOrdersAsync(string customerId)
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/orders/customer/{CustomerId}", customerId);
        
        var response = await client.GetAsync($"/api/demo/orders/customer/{Uri.EscapeDataString(customerId)}");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    // ???????????????????????????????????????????????????????????????????????????
    // EMPLOYEE ENDPOINTS - Not available in DemoController
    // These return simulated data since DemoController doesn't have employee endpoints
    // ???????????????????????????????????????????????????????????????????????????

    public Task<JsonElement?> GetEmployeesAsync()
    {
        _logger.LogInformation("GetEmployees called - DemoController doesn't have employee endpoints, returning simulated data");
        
        var result = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
        {
            success = true,
            message = "Employee data simulated (not available in Demo API)",
            employees = new[]
            {
                new { id = 1, name = "Alice Johnson", email = "alice@demo.com", department = "Engineering", title = "Senior Developer" },
                new { id = 2, name = "Bob Smith", email = "bob@demo.com", department = "Engineering", title = "Tech Lead" },
                new { id = 3, name = "Carol Williams", email = "carol@demo.com", department = "Marketing", title = "Marketing Manager" }
            },
            total = 3
        }));
        
        return Task.FromResult<JsonElement?>(result);
    }

    public Task<JsonElement?> GetEmployeeAsync(int id)
    {
        _logger.LogInformation("GetEmployee called for id {Id} - DemoController doesn't have employee endpoints, returning simulated data", id);
        
        var employees = new Dictionary<int, object>
        {
            [1] = new { id = 1, name = "Alice Johnson", email = "alice@demo.com", department = "Engineering", title = "Senior Developer" },
            [2] = new { id = 2, name = "Bob Smith", email = "bob@demo.com", department = "Engineering", title = "Tech Lead" },
            [3] = new { id = 3, name = "Carol Williams", email = "carol@demo.com", department = "Marketing", title = "Marketing Manager" }
        };

        if (employees.TryGetValue(id, out var employee))
        {
            var result = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
            {
                success = true,
                data = employee
            }));
            return Task.FromResult<JsonElement?>(result);
        }

        var notFound = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
        {
            success = false,
            error = $"Employee with ID {id} not found"
        }));
        return Task.FromResult<JsonElement?>(notFound);
    }

    public Task<JsonElement?> SearchEmployeesAsync(string? name = null, string? department = null)
    {
        _logger.LogInformation("SearchEmployees called - DemoController doesn't have employee endpoints, returning simulated data");
        
        var result = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
        {
            success = true,
            message = $"Employee search simulated (name={name}, department={department})",
            employees = new[]
            {
                new { id = 1, name = "Alice Johnson", email = "alice@demo.com", department = "Engineering", title = "Senior Developer" }
            },
            total = 1
        }));
        
        return Task.FromResult<JsonElement?>(result);
    }

    // ???????????????????????????????????????????????????????????????????????????
    // INVENTORY ENDPOINTS - Not available in DemoController
    // Use product stock data instead
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> GetInventoryAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("GetInventory called - using product stock data from /api/demo/products");
        
        // Get products and extract inventory info
        var response = await client.GetAsync("/api/demo/products");
        response.EnsureSuccessStatusCode();
        
        var products = await response.Content.ReadFromJsonAsync<JsonElement>();
        
        // Transform products to inventory format
        if (products.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Array)
        {
            var inventory = data.EnumerateArray().Select(p => new
            {
                id = p.GetProperty("id").GetInt32(),
                name = p.GetProperty("name").GetString(),
                stock = p.GetProperty("stock").GetInt32(),
                status = p.GetProperty("stock").GetInt32() > 10 ? "In Stock" : 
                         p.GetProperty("stock").GetInt32() > 0 ? "Low Stock" : "Out of Stock"
            }).ToArray();

            return JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
            {
                success = true,
                inventory,
                total = inventory.Length
            }));
        }
        
        return products;
    }

    public Task<JsonElement?> UpdateStockAsync(int productId, int newStock)
    {
        _logger.LogInformation("UpdateStock called - DemoController doesn't have stock update endpoint");
        
        var result = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(new
        {
            success = false,
            error = "Stock update not available in Demo API. The stock is managed automatically when orders are created."
        }));
        
        return Task.FromResult<JsonElement?>(result);
    }

    // ???????????????????????????????????????????????????????????????????????????
    // HEALTH CHECK
    // ???????????????????????????????????????????????????????????????????????????

    public async Task<JsonElement?> HealthCheckAsync()
    {
        var client = CreateClient();
        
        _logger.LogInformation("Calling Demo API: GET /api/demo/health");
        
        var response = await client.GetAsync("/api/demo/health");
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }
}
