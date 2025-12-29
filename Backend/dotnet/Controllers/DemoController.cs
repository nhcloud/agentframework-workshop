using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using System.Text.Json;

namespace DotNetAgentFramework.Controllers;

/// <summary>
/// Demo Controller for MCP Server demonstration
/// Contains sample REST endpoints that can be exposed via MCP
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class DemoController : ControllerBase
{
    private readonly ILogger<DemoController> _logger;
    
    // Simulated in-memory database
    private static readonly List<DemoProduct> _products = new()
    {
        new DemoProduct { Id = 1, Name = "Laptop Pro", Category = "Electronics", Price = 1299.99m, Stock = 50, Description = "High-performance laptop for professionals" },
        new DemoProduct { Id = 2, Name = "Wireless Mouse", Category = "Electronics", Price = 49.99m, Stock = 200, Description = "Ergonomic wireless mouse with long battery life" },
        new DemoProduct { Id = 3, Name = "Office Chair", Category = "Furniture", Price = 399.99m, Stock = 30, Description = "Comfortable ergonomic office chair" },
        new DemoProduct { Id = 4, Name = "Standing Desk", Category = "Furniture", Price = 599.99m, Stock = 25, Description = "Adjustable height standing desk" },
        new DemoProduct { Id = 5, Name = "Monitor 27\"", Category = "Electronics", Price = 349.99m, Stock = 75, Description = "4K Ultra HD monitor with HDR support" }
    };
    
    private static readonly List<DemoOrder> _orders = new()
    {
        new DemoOrder { Id = 1, CustomerId = "CUST001", ProductId = 1, Quantity = 1, Status = "Completed", OrderDate = DateTime.UtcNow.AddDays(-5), TotalAmount = 1299.99m },
        new DemoOrder { Id = 2, CustomerId = "CUST002", ProductId = 2, Quantity = 3, Status = "Shipped", OrderDate = DateTime.UtcNow.AddDays(-2), TotalAmount = 149.97m },
        new DemoOrder { Id = 3, CustomerId = "CUST001", ProductId = 5, Quantity = 2, Status = "Processing", OrderDate = DateTime.UtcNow.AddDays(-1), TotalAmount = 699.98m }
    };

    // Simulated weather data for demo purposes
    private static readonly Dictionary<string, WeatherData> _weatherData = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Seattle"] = new WeatherData { Location = "Seattle", Temperature = 15, Condition = "Cloudy", Humidity = 75, WindSpeed = 12, Unit = "Celsius" },
        ["New York"] = new WeatherData { Location = "New York", Temperature = 22, Condition = "Sunny", Humidity = 55, WindSpeed = 8, Unit = "Celsius" },
        ["London"] = new WeatherData { Location = "London", Temperature = 12, Condition = "Rainy", Humidity = 85, WindSpeed = 15, Unit = "Celsius" },
        ["Tokyo"] = new WeatherData { Location = "Tokyo", Temperature = 28, Condition = "Partly Cloudy", Humidity = 65, WindSpeed = 6, Unit = "Celsius" },
        ["Paris"] = new WeatherData { Location = "Paris", Temperature = 18, Condition = "Sunny", Humidity = 60, WindSpeed = 10, Unit = "Celsius" },
        ["Sydney"] = new WeatherData { Location = "Sydney", Temperature = 25, Condition = "Clear", Humidity = 50, WindSpeed = 14, Unit = "Celsius" },
        ["Berlin"] = new WeatherData { Location = "Berlin", Temperature = 14, Condition = "Overcast", Humidity = 70, WindSpeed = 18, Unit = "Celsius" },
        ["Mumbai"] = new WeatherData { Location = "Mumbai", Temperature = 32, Condition = "Hot and Humid", Humidity = 80, WindSpeed = 5, Unit = "Celsius" },
        ["San Francisco"] = new WeatherData { Location = "San Francisco", Temperature = 17, Condition = "Foggy", Humidity = 78, WindSpeed = 11, Unit = "Celsius" },
        ["Singapore"] = new WeatherData { Location = "Singapore", Temperature = 30, Condition = "Tropical", Humidity = 85, WindSpeed = 7, Unit = "Celsius" }
    };

    public DemoController(ILogger<DemoController> logger)
    {
        _logger = logger;
    }

    // ???????????????????????????????????????????????????????????????????????????
    // WEATHER API
    // This endpoint demonstrates the same functionality as the local WeatherTool
    // but exposed as a REST API that can be called via MCP
    // ???????????????????????????????????????????????????????????????????????????

    /// <summary>
    /// Get weather information for a location.
    /// This is the same functionality as the local WeatherTool but exposed via REST API.
    /// Demonstrates how the same tool can be available locally AND via MCP.
    /// </summary>
    /// <param name="location">The location to get weather for (e.g., Seattle, Tokyo, London)</param>
    /// <returns>Weather information for the specified location</returns>
    [HttpGet("weather")]
    [ProducesResponseType(typeof(DemoApiResponse<WeatherData>), 200)]
    public ActionResult<DemoApiResponse<WeatherData>> GetWeather([FromQuery] string location)
    {
        _logger.LogInformation("GetWeather called for location: {Location}", location);

        if (string.IsNullOrWhiteSpace(location))
        {
            return BadRequest(new DemoApiResponse<WeatherData>
            {
                Success = false,
                Message = "Location parameter is required",
                Timestamp = DateTime.UtcNow
            });
        }

        // Try to find exact match first, then partial match
        WeatherData? weather = null;
        
        if (_weatherData.TryGetValue(location, out var exactMatch))
        {
            weather = exactMatch;
        }
        else
        {
            // Try partial match
            var partialMatch = _weatherData.Keys
                .FirstOrDefault(k => k.Contains(location, StringComparison.OrdinalIgnoreCase) ||
                                     location.Contains(k, StringComparison.OrdinalIgnoreCase));
            
            if (partialMatch != null)
            {
                weather = _weatherData[partialMatch];
            }
        }

        if (weather != null)
        {
            return Ok(new DemoApiResponse<WeatherData>
            {
                Success = true,
                Data = weather,
                Message = $"Weather data for {weather.Location}",
                Timestamp = DateTime.UtcNow,
                Metadata = new Dictionary<string, object>
                {
                    ["source"] = "demo-api",
                    ["cached"] = true,
                    ["lastUpdated"] = DateTime.UtcNow.AddMinutes(-5).ToString("O")
                }
            });
        }

        // Return simulated weather for unknown locations
        var simulatedWeather = new WeatherData
        {
            Location = location,
            Temperature = 15,
            Condition = "Cloudy",
            Humidity = 70,
            WindSpeed = 10,
            Unit = "Celsius"
        };

        return Ok(new DemoApiResponse<WeatherData>
        {
            Success = true,
            Data = simulatedWeather,
            Message = $"Simulated weather data for {location} (location not in database)",
            Timestamp = DateTime.UtcNow,
            Metadata = new Dictionary<string, object>
            {
                ["source"] = "demo-api",
                ["simulated"] = true,
                ["note"] = "This is simulated data. Known locations: Seattle, New York, London, Tokyo, Paris, Sydney, Berlin, Mumbai, San Francisco, Singapore"
            }
        });
    }

    /// <summary>
    /// Get list of all locations with available weather data
    /// </summary>
    [HttpGet("weather/locations")]
    [ProducesResponseType(typeof(DemoApiResponse<List<string>>), 200)]
    public ActionResult<DemoApiResponse<List<string>>> GetWeatherLocations()
    {
        _logger.LogInformation("GetWeatherLocations called");

        return Ok(new DemoApiResponse<List<string>>
        {
            Success = true,
            Data = _weatherData.Keys.OrderBy(k => k).ToList(),
            Message = $"Found {_weatherData.Count} locations with weather data",
            Timestamp = DateTime.UtcNow
        });
    }

    // ???????????????????????????????????????????????????????????????????????????
    // PRODUCTS API
    // ???????????????????????????????????????????????????????????????????????????

    /// <summary>
    /// Get all products or filter by category
    /// This endpoint demonstrates a GET operation that can be exposed via MCP
    /// </summary>
    /// <param name="category">Optional category filter</param>
    /// <param name="minPrice">Optional minimum price filter</param>
    /// <param name="maxPrice">Optional maximum price filter</param>
    /// <returns>List of products matching the criteria</returns>
    [HttpGet("products")]
    [ProducesResponseType(typeof(DemoApiResponse<List<DemoProduct>>), 200)]
    public ActionResult<DemoApiResponse<List<DemoProduct>>> GetProducts(
        [FromQuery] string? category = null,
        [FromQuery] decimal? minPrice = null,
        [FromQuery] decimal? maxPrice = null)
    {
        var authHeader = Request.Headers.Authorization.FirstOrDefault();
        _logger.LogInformation("GetProducts called with category={Category}, minPrice={MinPrice}, maxPrice={MaxPrice}, Auth={Auth}",
            category, minPrice, maxPrice, authHeader?.Substring(0, Math.Min(20, authHeader?.Length ?? 0)));

        var products = _products.AsEnumerable();

        if (!string.IsNullOrEmpty(category))
        {
            products = products.Where(p => p.Category.Equals(category, StringComparison.OrdinalIgnoreCase));
        }

        if (minPrice.HasValue)
        {
            products = products.Where(p => p.Price >= minPrice.Value);
        }

        if (maxPrice.HasValue)
        {
            products = products.Where(p => p.Price <= maxPrice.Value);
        }

        var result = products.ToList();

        return Ok(new DemoApiResponse<List<DemoProduct>>
        {
            Success = true,
            Data = result,
            Message = $"Found {result.Count} products",
            Timestamp = DateTime.UtcNow,
            Metadata = new Dictionary<string, object>
            {
                ["totalCount"] = result.Count,
                ["filters"] = new { category, minPrice, maxPrice }
            }
        });
    }

    /// <summary>
    /// Get a specific product by ID
    /// </summary>
    /// <param name="id">Product ID</param>
    /// <returns>Product details</returns>
    [HttpGet("products/{id}")]
    [ProducesResponseType(typeof(DemoApiResponse<DemoProduct>), 200)]
    [ProducesResponseType(404)]
    public ActionResult<DemoApiResponse<DemoProduct>> GetProduct(int id)
    {
        var authHeader = Request.Headers.Authorization.FirstOrDefault();
        _logger.LogInformation("GetProduct called with id={Id}, Auth={Auth}", 
            id, authHeader?.Substring(0, Math.Min(20, authHeader?.Length ?? 0)));

        var product = _products.FirstOrDefault(p => p.Id == id);

        if (product == null)
        {
            return NotFound(new DemoApiResponse<DemoProduct>
            {
                Success = false,
                Message = $"Product with ID {id} not found",
                Timestamp = DateTime.UtcNow
            });
        }

        return Ok(new DemoApiResponse<DemoProduct>
        {
            Success = true,
            Data = product,
            Message = "Product found",
            Timestamp = DateTime.UtcNow
        });
    }

    /// <summary>
    /// Create a new order
    /// This endpoint demonstrates a POST operation that can be exposed via MCP
    /// </summary>
    /// <param name="request">Order creation request</param>
    /// <returns>Created order details</returns>
    [HttpPost("orders")]
    [ProducesResponseType(typeof(DemoApiResponse<DemoOrder>), 201)]
    [ProducesResponseType(400)]
    public ActionResult<DemoApiResponse<DemoOrder>> CreateOrder([FromBody] CreateOrderRequest request)
    {
        var authHeader = Request.Headers.Authorization.FirstOrDefault();
        _logger.LogInformation("CreateOrder called with ProductId={ProductId}, Quantity={Quantity}, CustomerId={CustomerId}, Auth={Auth}",
            request.ProductId, request.Quantity, request.CustomerId, authHeader?.Substring(0, Math.Min(20, authHeader?.Length ?? 0)));

        // Validate authorization (demo purposes - just check header exists)
        if (string.IsNullOrEmpty(authHeader))
        {
            return Unauthorized(new DemoApiResponse<DemoOrder>
            {
                Success = false,
                Message = "Authorization header is required",
                Timestamp = DateTime.UtcNow
            });
        }

        // Validate product exists
        var product = _products.FirstOrDefault(p => p.Id == request.ProductId);
        if (product == null)
        {
            return BadRequest(new DemoApiResponse<DemoOrder>
            {
                Success = false,
                Message = $"Product with ID {request.ProductId} not found",
                Timestamp = DateTime.UtcNow
            });
        }

        // Validate stock
        if (product.Stock < request.Quantity)
        {
            return BadRequest(new DemoApiResponse<DemoOrder>
            {
                Success = false,
                Message = $"Insufficient stock. Available: {product.Stock}, Requested: {request.Quantity}",
                Timestamp = DateTime.UtcNow
            });
        }

        // Create order
        var newOrder = new DemoOrder
        {
            Id = _orders.Max(o => o.Id) + 1,
            CustomerId = request.CustomerId,
            ProductId = request.ProductId,
            Quantity = request.Quantity,
            Status = "Processing",
            OrderDate = DateTime.UtcNow,
            TotalAmount = product.Price * request.Quantity,
            Notes = request.Notes
        };

        _orders.Add(newOrder);

        // Update stock (in-memory simulation)
        product.Stock -= request.Quantity;

        _logger.LogInformation("Order {OrderId} created successfully for customer {CustomerId}", newOrder.Id, newOrder.CustomerId);

        return CreatedAtAction(nameof(GetOrder), new { id = newOrder.Id }, new DemoApiResponse<DemoOrder>
        {
            Success = true,
            Data = newOrder,
            Message = "Order created successfully",
            Timestamp = DateTime.UtcNow,
            Metadata = new Dictionary<string, object>
            {
                ["productName"] = product.Name,
                ["remainingStock"] = product.Stock
            }
        });
    }

    /// <summary>
    /// Get order by ID
    /// </summary>
    /// <param name="id">Order ID</param>
    /// <returns>Order details</returns>
    [HttpGet("orders/{id}")]
    [ProducesResponseType(typeof(DemoApiResponse<DemoOrder>), 200)]
    [ProducesResponseType(404)]
    public ActionResult<DemoApiResponse<DemoOrder>> GetOrder(int id)
    {
        var authHeader = Request.Headers.Authorization.FirstOrDefault();
        _logger.LogInformation("GetOrder called with id={Id}, Auth={Auth}", 
            id, authHeader?.Substring(0, Math.Min(20, authHeader?.Length ?? 0)));

        var order = _orders.FirstOrDefault(o => o.Id == id);

        if (order == null)
        {
            return NotFound(new DemoApiResponse<DemoOrder>
            {
                Success = false,
                Message = $"Order with ID {id} not found",
                Timestamp = DateTime.UtcNow
            });
        }

        var product = _products.FirstOrDefault(p => p.Id == order.ProductId);

        return Ok(new DemoApiResponse<DemoOrder>
        {
            Success = true,
            Data = order,
            Message = "Order found",
            Timestamp = DateTime.UtcNow,
            Metadata = new Dictionary<string, object>
            {
                ["productName"] = product?.Name ?? "Unknown"
            }
        });
    }

    /// <summary>
    /// Get orders for a specific customer
    /// </summary>
    /// <param name="customerId">Customer ID</param>
    /// <returns>List of orders for the customer</returns>
    [HttpGet("orders/customer/{customerId}")]
    [ProducesResponseType(typeof(DemoApiResponse<List<DemoOrder>>), 200)]
    public ActionResult<DemoApiResponse<List<DemoOrder>>> GetCustomerOrders(string customerId)
    {
        var authHeader = Request.Headers.Authorization.FirstOrDefault();
        _logger.LogInformation("GetCustomerOrders called with customerId={CustomerId}, Auth={Auth}", 
            customerId, authHeader?.Substring(0, Math.Min(20, authHeader?.Length ?? 0)));

        var orders = _orders.Where(o => o.CustomerId.Equals(customerId, StringComparison.OrdinalIgnoreCase)).ToList();

        return Ok(new DemoApiResponse<List<DemoOrder>>
        {
            Success = true,
            Data = orders,
            Message = $"Found {orders.Count} orders for customer {customerId}",
            Timestamp = DateTime.UtcNow
        });
    }

    /// <summary>
    /// Health check endpoint for MCP server
    /// </summary>
    [HttpGet("health")]
    [ProducesResponseType(typeof(object), 200)]
    public ActionResult GetHealth()
    {
        return Ok(new
        {
            status = "healthy",
            service = "DemoController",
            timestamp = DateTime.UtcNow,
            version = "1.0.0",
            endpoints = new[]
            {
                new { method = "GET", path = "/api/demo/weather", description = "Get weather for a location (same as local WeatherTool)" },
                new { method = "GET", path = "/api/demo/weather/locations", description = "List all locations with weather data" },
                new { method = "GET", path = "/api/demo/products", description = "List products with optional filters" },
                new { method = "GET", path = "/api/demo/products/{id}", description = "Get product by ID" },
                new { method = "POST", path = "/api/demo/orders", description = "Create a new order" },
                new { method = "GET", path = "/api/demo/orders/{id}", description = "Get order by ID" },
                new { method = "GET", path = "/api/demo/orders/customer/{customerId}", description = "Get customer orders" }
            }
        });
    }
}

#region Demo Models

public class DemoProduct
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Category { get; set; } = string.Empty;
    public decimal Price { get; set; }
    public int Stock { get; set; }
    public string Description { get; set; } = string.Empty;
}

public class DemoOrder
{
    public int Id { get; set; }
    public string CustomerId { get; set; } = string.Empty;
    public int ProductId { get; set; }
    public int Quantity { get; set; }
    public string Status { get; set; } = string.Empty;
    public DateTime OrderDate { get; set; }
    public decimal TotalAmount { get; set; }
    public string? Notes { get; set; }
}

public class CreateOrderRequest
{
    public string CustomerId { get; set; } = string.Empty;
    public int ProductId { get; set; }
    public int Quantity { get; set; } = 1;
    public string? Notes { get; set; }
}

public class WeatherData
{
    public string Location { get; set; } = string.Empty;
    public int Temperature { get; set; }
    public string Condition { get; set; } = string.Empty;
    public int Humidity { get; set; }
    public int WindSpeed { get; set; }
    public string Unit { get; set; } = "Celsius";
}

public class DemoApiResponse<T>
{
    public bool Success { get; set; }
    public T? Data { get; set; }
    public string Message { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
}

#endregion
