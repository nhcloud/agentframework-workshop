using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Text.Json;

namespace DotNetAgentFramework.McpServer.Tools;

/// <summary>
/// MCP Tools that expose Demo API endpoints from DemoController (port 8000).
/// These tools can be called by MCP clients (like AI agents) to interact with the Demo API.
/// 
/// Available endpoints:
/// - Weather: /api/demo/weather
/// - Products: /api/demo/products
/// - Orders: /api/demo/orders
/// </summary>
[McpServerToolType]
public class DemoApiTools
{
    private readonly DemoApiClient _apiClient;

    public DemoApiTools(DemoApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    // ???????????????????????????????????????????????????????????????????????????
    // WEATHER TOOLS - /api/demo/weather
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_weather")]
    [Description("Get current weather information for a specific location. Available locations include: Seattle, New York, London, Tokyo, Paris, Sydney, Berlin, Mumbai, San Francisco, Singapore.")]
    public async Task<string> GetWeather(
        [Description("The location to get weather for (e.g., Seattle, Tokyo, London)")] string location)
    {
        try
        {
            var result = await _apiClient.GetWeatherAsync(location);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_weather", ex);
        }
    }

    [McpServerTool(Name = "get_weather_locations")]
    [Description("Get a list of all locations that have weather data available.")]
    public async Task<string> GetWeatherLocations()
    {
        try
        {
            var result = await _apiClient.GetWeatherLocationsAsync();
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_weather_locations", ex);
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // EMPLOYEE TOOLS (Simulated - Demo API doesn't have employee endpoints)
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_all_employees")]
    [Description("Get a list of all employees in the company. Note: Returns simulated data as Demo API focuses on products and orders.")]
    public async Task<string> GetAllEmployees()
    {
        try
        {
            var result = await _apiClient.GetEmployeesAsync();
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_all_employees", ex);
        }
    }

    [McpServerTool(Name = "get_employee")]
    [Description("Get detailed information about a specific employee by their ID. Note: Returns simulated data.")]
    public async Task<string> GetEmployee(
        [Description("The employee ID (e.g., 1, 2, 3)")] int employee_id)
    {
        try
        {
            var result = await _apiClient.GetEmployeeAsync(employee_id);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_employee", ex);
        }
    }

    [McpServerTool(Name = "search_employees")]
    [Description("Search for employees by name and/or department. Note: Returns simulated data.")]
    public async Task<string> SearchEmployees(
        [Description("Part of the employee name to search for (optional)")] string? name = null,
        [Description("Department to filter by (e.g., Engineering, Marketing, Sales, HR)")] string? department = null)
    {
        try
        {
            var result = await _apiClient.SearchEmployeesAsync(name, department);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("search_employees", ex);
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // PRODUCT TOOLS - /api/demo/products
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_all_products")]
    [Description("Get a list of all products in the catalog. Products include electronics and furniture items.")]
    public async Task<string> GetAllProducts()
    {
        try
        {
            var result = await _apiClient.GetProductsAsync();
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_all_products", ex);
        }
    }

    [McpServerTool(Name = "get_product")]
    [Description("Get detailed information about a specific product by its ID.")]
    public async Task<string> GetProduct(
        [Description("The product ID (e.g., 1, 2, 3, 4, 5)")] int product_id)
    {
        try
        {
            var result = await _apiClient.GetProductAsync(product_id);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_product", ex);
        }
    }

    [McpServerTool(Name = "get_products_by_category")]
    [Description("Get all products in a specific category. Available categories: Electronics, Furniture.")]
    public async Task<string> GetProductsByCategory(
        [Description("Product category (e.g., Electronics, Furniture)")] string category)
    {
        try
        {
            var result = await _apiClient.GetProductsAsync(category);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_products_by_category", ex);
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // ORDER TOOLS - /api/demo/orders
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_all_orders")]
    [Description("Get information about orders. Note: Use get_order or get_customer_orders for specific queries.")]
    public async Task<string> GetAllOrders()
    {
        try
        {
            var result = await _apiClient.GetOrdersAsync();
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_all_orders", ex);
        }
    }

    [McpServerTool(Name = "get_order")]
    [Description("Get detailed information about a specific order by its ID.")]
    public async Task<string> GetOrder(
        [Description("The order ID (e.g., 1, 2, 3)")] string order_id)
    {
        try
        {
            var result = await _apiClient.GetOrderAsync(order_id);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_order", ex);
        }
    }

    [McpServerTool(Name = "create_order")]
    [Description("Create a new order for a customer. Requires authorization. Stock will be automatically reduced.")]
    public async Task<string> CreateOrder(
        [Description("Customer ID placing the order (e.g., CUST001, CUST002)")] string customer_id,
        [Description("Product ID to order (1-5)")] int product_id,
        [Description("Quantity to order (default: 1)")] int quantity = 1,
        [Description("Optional notes for the order")] string? notes = null)
    {
        try
        {
            var result = await _apiClient.CreateOrderAsync(customer_id, product_id, quantity, notes);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("create_order", ex);
        }
    }

    [McpServerTool(Name = "get_customer_orders")]
    [Description("Get all orders for a specific customer.")]
    public async Task<string> GetCustomerOrders(
        [Description("Customer ID to get orders for (e.g., CUST001)")] string customer_id)
    {
        try
        {
            var result = await _apiClient.GetCustomerOrdersAsync(customer_id);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_customer_orders", ex);
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // INVENTORY TOOLS (Uses product stock data)
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_inventory")]
    [Description("Get current inventory status for all products, including stock levels.")]
    public async Task<string> GetInventory()
    {
        try
        {
            var result = await _apiClient.GetInventoryAsync();
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("get_inventory", ex);
        }
    }

    [McpServerTool(Name = "update_stock")]
    [Description("Update the stock quantity for a product. Note: Stock is managed automatically via orders in Demo API.")]
    public async Task<string> UpdateStock(
        [Description("The product ID to update")] int product_id,
        [Description("The new stock quantity")] int new_stock)
    {
        try
        {
            var result = await _apiClient.UpdateStockAsync(product_id, new_stock);
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("update_stock", ex);
        }
    }

    // ???????????????????????????????????????????????????????????????????????????
    // HEALTH CHECK
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "health_check")]
    [Description("Check the health and status of the Demo API service. Returns available endpoints.")]
    public async Task<string> HealthCheck()
    {
        try
        {
            var result = await _apiClient.HealthCheckAsync();
            return FormatResponse(result);
        }
        catch (Exception ex)
        {
            return FormatError("health_check", ex);
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
