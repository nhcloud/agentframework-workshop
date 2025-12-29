using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Text.Json;

namespace DotNetAgentFramework.McpServer.Tools;

/// <summary>
/// MCP Tools that expose SampleRestApi endpoints.
/// These tools can be called by MCP clients (like AI agents) to interact with the SampleRestApi.
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
    // EMPLOYEE TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_all_employees")]
    [Description("Get a list of all employees in the company.")]
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
    [Description("Get detailed information about a specific employee by their ID.")]
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
    [Description("Search for employees by name and/or department.")]
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
    // PRODUCT TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_all_products")]
    [Description("Get a list of all products in the catalog.")]
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
        [Description("The product ID (e.g., 1, 2, 3)")] int product_id)
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
    [Description("Get all products in a specific category.")]
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
    // ORDER TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_all_orders")]
    [Description("Get a list of all orders.")]
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
        [Description("The order ID (e.g., ORD-20240101-0001)")] string order_id)
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
    [Description("Create a new order for a customer.")]
    public async Task<string> CreateOrder(
        [Description("Customer ID placing the order (e.g., 1, 2, 3)")] string customer_id,
        [Description("Product ID to order")] int product_id,
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
        [Description("Customer ID to get orders for")] string customer_id)
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
    // INVENTORY TOOLS
    // ???????????????????????????????????????????????????????????????????????????

    [McpServerTool(Name = "get_inventory")]
    [Description("Get current inventory status for all products.")]
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
    [Description("Update the stock quantity for a product.")]
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
    [Description("Check the health and status of the SampleRestApi service.")]
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
