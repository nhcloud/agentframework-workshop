using System.ComponentModel;
using ModelContextProtocol.Server;

namespace SampleMcpBridge;

/// <summary>
/// MCP Tools that expose REST API endpoints.
/// Each method here becomes an MCP tool that AI agents can call.
/// The [McpServerToolType] attribute registers this class with the MCP server.
/// 
/// IMPORTANT: The get_weather tool below is the SAME functionality as the local
/// WeatherTool (Agents/Tools/WeatherTool.cs), but exposed via MCP over REST API.
/// This demonstrates how the same tool can be:
/// 1. LOCAL (WeatherTool) - Called directly by the agent in-process
/// 2. REMOTE (get_weather via MCP) - Called via MCP protocol over HTTP/SSE
/// </summary>
[McpServerToolType]
public class RestApiTools
{
    private readonly RestApiClient _apiClient;

    public RestApiTools(RestApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    // ???????????????????????????????????????????????????????????????????????????
    // WEATHER TOOL (Same as local WeatherTool but via MCP)
    // This demonstrates LOCAL vs REMOTE tool pattern
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool]
    [Description("Get the weather for a given location. This is the SAME functionality as the local WeatherTool but exposed via MCP/REST API. Use this to demonstrate remote tool calling.")]
    public async Task<string> get_weather(
        [Description("The location to get the weather for (e.g., Seattle, Tokyo, London, New York)")] string location)
    {
        try
        {
            return await _apiClient.GetWeatherAsync(location);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get weather for {location}: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Get a list of all locations that have weather data available")]
    public async Task<string> get_weather_locations()
    {
        try
        {
            return await _apiClient.GetWeatherLocationsAsync();
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get weather locations: {ex.Message}\"}}";
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // HEALTH CHECK
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool]
    [Description("Check the health status of the REST API and see available endpoints")]
    public async Task<string> check_api_health()
    {
        try
        {
            return await _apiClient.GetHealthAsync();
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"API health check failed: {ex.Message}\"}}";
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // EMPLOYEE TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool]
    [Description("Get a list of all employees in the company")]
    public async Task<string> get_all_employees()
    {
        try
        {
            return await _apiClient.GetAllEmployeesAsync();
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get employees: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Get details of a specific employee by their ID")]
    public async Task<string> get_employee(
        [Description("The employee ID (e.g., 1, 2, 3)")] int employee_id)
    {
        try
        {
            return await _apiClient.GetEmployeeAsync(employee_id);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get employee {employee_id}: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Search for employees by name and/or department")]
    public async Task<string> search_employees(
        [Description("Part of the employee name to search for (optional)")] string? name = null,
        [Description("Department to filter by (e.g., Engineering, Marketing, Sales, HR)")] string? department = null)
    {
        try
        {
            return await _apiClient.SearchEmployeesAsync(name, department);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to search employees: {ex.Message}\"}}";
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // PRODUCT TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool]
    [Description("Get a list of all products in the catalog")]
    public async Task<string> get_all_products()
    {
        try
        {
            return await _apiClient.GetAllProductsAsync();
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get products: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Get details of a specific product by its ID")]
    public async Task<string> get_product(
        [Description("The product ID (e.g., 1, 2, 3)")] int product_id)
    {
        try
        {
            return await _apiClient.GetProductAsync(product_id);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get product {product_id}: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Get all products in a specific category")]
    public async Task<string> get_products_by_category(
        [Description("Product category (e.g., Electronics, Furniture)")] string category)
    {
        try
        {
            return await _apiClient.GetProductsByCategoryAsync(category);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get products in category {category}: {ex.Message}\"}}";
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // ORDER TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool]
    [Description("Get a list of all orders")]
    public async Task<string> get_all_orders()
    {
        try
        {
            return await _apiClient.GetAllOrdersAsync();
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get orders: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Get details of a specific order by its ID")]
    public async Task<string> get_order(
        [Description("The order ID (e.g., 1, 2, 3)")] int order_id)
    {
        try
        {
            return await _apiClient.GetOrderAsync(order_id.ToString());
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get order {order_id}: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Get all orders for a specific customer")]
    public async Task<string> get_customer_orders(
        [Description("The customer ID (e.g., CUST001)")] string customer_id)
    {
        try
        {
            return await _apiClient.GetCustomerOrdersAsync(customer_id);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get orders for customer {customer_id}: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Create a new order for a customer")]
    public async Task<string> create_order(
        [Description("The customer ID placing the order (e.g., CUST001)")] string customer_id,
        [Description("The product ID to order")] int product_id,
        [Description("Quantity to order (default: 1)")] int quantity = 1)
    {
        try
        {
            // For simplicity, we'll create an order with a single product
            return await _apiClient.CreateOrderAsync(int.Parse(customer_id.Replace("CUST", "")), new List<int> { product_id });
        }
        catch (FormatException)
        {
            return $"{{\"error\": \"Invalid customer_id format. Use format like 'CUST001' or just a number.\"}}";
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to create order: {ex.Message}\"}}";
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // INVENTORY TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool]
    [Description("Get the current inventory status of all products")]
    public async Task<string> get_inventory()
    {
        try
        {
            return await _apiClient.GetInventoryAsync();
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to get inventory: {ex.Message}\"}}";
        }
    }

    [McpServerTool]
    [Description("Update the stock quantity for a product")]
    public async Task<string> update_stock(
        [Description("The product ID to update")] int product_id,
        [Description("The new stock quantity")] int new_stock)
    {
        try
        {
            return await _apiClient.UpdateStockAsync(product_id, new_stock);
        }
        catch (Exception ex)
        {
            return $"{{\"error\": \"Failed to update stock for product {product_id}: {ex.Message}\"}}";
        }
    }
}
