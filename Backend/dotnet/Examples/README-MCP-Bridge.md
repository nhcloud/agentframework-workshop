# MCP Bridge Pattern: Connecting MCP Clients to REST APIs

This guide explains how to expose your **existing REST APIs** (whether .NET 4.8, .NET Core, or any other technology) to MCP clients **without requiring the client to run an executable**.

## ??? Architecture Overview

```
???????????????????????????????????????????????????????????????????????????????????????????
?                                    YOUR INFRASTRUCTURE                                  ?
???????????????????????????????????????????????????????????????????????????????????????????

???????????????????       MCP Protocol      ???????????????????      HTTP/REST      ???????????????????
?   MCP Client    ?  ?????????????????????? ?   MCP Bridge    ? ??????????????????? ?  Your REST API  ?
?                 ?                         ?    Server       ?                     ?                 ?
?  (AI Agent,     ?    stdio or HTTP/SSE    ?  (Translator)   ?   Standard HTTP     ?  (.NET 4.8,     ?
?   Claude,       ?                         ?                 ?   GET/POST/PUT      ?   .NET Core,    ?
?   Copilot,      ?                         ?  Translates:    ?                     ?   Java,         ?
?   Custom App)   ?                         ?  MCP Tool Call  ?                     ?   Python, etc.) ?
?                 ?                         ?       ?         ?                     ?                 ?
?                 ?                         ?  HTTP Request   ?                     ?                 ?
???????????????????                         ???????????????????                     ???????????????????
         ?                                          ?                                       ?
         ?                                          ?                                       ?
         ?                                          ?                                       ?
   AI calls tool:                          Translates to:                           Existing endpoint:
   get_employees()                         GET /api/employees                       Returns JSON
```

## ?? Project Structure

```
??? SampleRestApi/                    # Your existing REST API (simulated)
?   ??? Program.cs                    # API endpoints (runs on port 5001)
?   ??? SampleRestApi.csproj
?
??? SampleMcpBridge/                  # MCP Server that bridges to REST API
?   ??? Program.cs                    # MCP server entry point
?   ??? RestApiClient.cs              # HTTP client for calling REST API
?   ??? RestApiTools.cs               # MCP tools that wrap REST endpoints
?   ??? appsettings.json              # Configuration (REST API URL)
?   ??? SampleMcpBridge.csproj
?
??? README-MCP-Bridge.md              # This file
```

## ?? Quick Start

### Step 1: Start Your REST API

```bash
cd SampleRestApi
dotnet run
# API running at http://localhost:5001
# Swagger UI at http://localhost:5001/swagger
```

### Step 2: Configure MCP Bridge

Edit `SampleMcpBridge/appsettings.json`:
```json
{
  "RestApi": {
    "BaseUrl": "http://localhost:5001"  // Your REST API URL
  }
}
```

### Step 3: Test the MCP Bridge

```bash
cd SampleMcpBridge
dotnet run
# MCP Bridge Server starts, listening on stdio
```

### Step 4: Configure MCP Client

Add to your `config.yml`:
```yaml
mcp:
  servers:
    - name: "my-rest-api"
      transport: "stdio"
      command: "dotnet"
      arguments: ["run", "--project", "SampleMcpBridge/SampleMcpBridge.csproj"]
```

## ?? How It Works

### 1. MCP Tool Definition (RestApiTools.cs)

```csharp
[McpServerToolType]
public class RestApiTools
{
    private readonly RestApiClient _apiClient;

    [McpServerTool]
    [Description("Get a list of all employees")]
    public async Task<string> get_all_employees()
    {
        // This tool call triggers an HTTP request
        return await _apiClient.GetAllEmployeesAsync();
    }

    [McpServerTool]
    [Description("Search employees by name or department")]
    public async Task<string> search_employees(
        [Description("Name to search")] string? name = null,
        [Description("Department filter")] string? department = null)
    {
        return await _apiClient.SearchEmployeesAsync(name, department);
    }
}
```

### 2. REST API Client (RestApiClient.cs)

```csharp
public class RestApiClient
{
    private readonly HttpClient _httpClient;

    public Task<string> GetAllEmployeesAsync() 
        => GetAsStringAsync("/api/employees");

    public Task<string> SearchEmployeesAsync(string? name, string? department)
    {
        var query = BuildQueryString(name, department);
        return GetAsStringAsync($"/api/employees/search{query}");
    }
}
```

### 3. What Happens When AI Calls a Tool

```
1. AI Agent: "Find all employees in Engineering"
              ?
2. MCP Client sends: { tool: "search_employees", args: { department: "Engineering" } }
              ?
3. MCP Bridge receives tool call via MCP protocol
              ?
4. RestApiTools.search_employees() is invoked
              ?
5. RestApiClient sends: GET http://localhost:5001/api/employees/search?department=Engineering
              ?
6. REST API returns: { "employees": [...], "total": 2 }
              ?
7. MCP Bridge returns result to MCP Client
              ?
8. AI Agent receives and interprets the employee data
```

## ?? Available Tools

| MCP Tool | REST Endpoint | Description |
|----------|--------------|-------------|
| `check_api_health` | GET /api/health | Check API status |
| `get_all_employees` | GET /api/employees | List all employees |
| `get_employee` | GET /api/employees/{id} | Get employee by ID |
| `search_employees` | GET /api/employees/search | Search employees |
| `get_all_products` | GET /api/products | List all products |
| `get_product` | GET /api/products/{id} | Get product by ID |
| `get_products_by_category` | GET /api/products/category/{cat} | Products by category |
| `get_all_orders` | GET /api/orders | List all orders |
| `get_order` | GET /api/orders/{id} | Get order by ID |
| `create_order` | POST /api/orders | Create new order |
| `get_inventory` | GET /api/inventory | Get inventory status |
| `update_stock` | PUT /api/inventory/{id}/stock | Update product stock |

## ?? Deployment Options

### Option A: STDIO Transport (Local/Development)

The MCP client spawns the bridge server as a child process:

```yaml
# Client config
mcp:
  servers:
    - name: "my-api-bridge"
      transport: "stdio"
      command: "SampleMcpBridge.exe"  # or "dotnet run"
```

**Pros:** Simple, no network setup
**Cons:** Requires distributing the executable

### Option B: HTTP/SSE Transport (Production/Remote)

Host the MCP Bridge as a web service:

```yaml
# Client config
mcp:
  servers:
    - name: "my-api-bridge"
      transport: "sse"
      endpoint: "https://mcp-bridge.yourcompany.com/mcp/sse"
```

**Pros:** No executable distribution, centralized management
**Cons:** Requires hosting infrastructure

## ?? Security Considerations

### 1. API Authentication

Add authentication headers in `RestApiClient`:

```csharp
builder.Services.AddHttpClient("RestApi", client =>
{
    client.BaseAddress = new Uri(restApiBaseUrl);
    client.DefaultRequestHeaders.Add("Authorization", "Bearer your-api-token");
    client.DefaultRequestHeaders.Add("X-API-Key", "your-api-key");
});
```

### 2. Tool-Level Authorization

Implement authorization in tools:

```csharp
[McpServerTool]
public async Task<string> create_order(int customer_id, string product_ids)
{
    // Check if tool is allowed (e.g., based on MCP client identity)
    if (!IsAuthorized("create_order"))
        return "{\"error\": \"Unauthorized\"}";
    
    return await _apiClient.CreateOrderAsync(customer_id, ParseProductIds(product_ids));
}
```

### 3. Input Validation

Always validate inputs before calling REST API:

```csharp
[McpServerTool]
public async Task<string> get_employee(int employee_id)
{
    if (employee_id <= 0)
        return "{\"error\": \"Invalid employee ID\"}";
    
    return await _apiClient.GetEmployeeAsync(employee_id);
}
```

## ?? Connecting to Your Existing .NET 4.8 API

If your REST API is running on .NET Framework 4.8:

1. **No changes needed to your API!** The MCP Bridge just calls HTTP endpoints.

2. Configure the bridge to point to your API:
   ```json
   {
     "RestApi": {
       "BaseUrl": "http://your-legacy-api:8080"
     }
   }
   ```

3. Create tools for each endpoint you want to expose:
   ```csharp
   [McpServerTool]
   [Description("Get customer by ID from legacy system")]
   public async Task<string> get_customer(int customer_id)
   {
       return await _apiClient.GetAsStringAsync($"/api/v1/customers/{customer_id}");
   }
   ```

## ?? Example Conversation

```
User: "Who works in the Engineering department?"

AI Agent:
  ? Calls MCP tool: search_employees(department="Engineering")
  ? MCP Bridge: GET http://localhost:5001/api/employees/search?department=Engineering
  ? REST API returns: {"employees": [{"name": "Alice", ...}, {"name": "Bob", ...}]}
  
AI Response: "There are 2 people in Engineering:
  - Alice Johnson (Senior Developer)
  - Bob Smith (Tech Lead)"

User: "What products do we have in Electronics?"

AI Agent:
  ? Calls MCP tool: get_products_by_category(category="Electronics")
  ? MCP Bridge: GET http://localhost:5001/api/products/category/Electronics
  ? REST API returns: {"products": [...]}

AI Response: "We have 3 electronics products:
  - Laptop Pro ($1,299.99)
  - Wireless Mouse ($49.99)
  - Monitor 27" ($449.99)"
```

## ?? Adding New Tools

To expose a new REST endpoint:

1. **Add the HTTP call in RestApiClient.cs:**
   ```csharp
   public Task<string> GetCustomerAsync(int id) 
       => GetAsStringAsync($"/api/customers/{id}");
   ```

2. **Add the MCP tool in RestApiTools.cs:**
   ```csharp
   [McpServerTool]
   [Description("Get customer details by ID")]
   public async Task<string> get_customer(
       [Description("Customer ID")] int customer_id)
   {
       return await _apiClient.GetCustomerAsync(customer_id);
   }
   ```

3. **Restart the MCP Bridge** - tools are discovered automatically!

## ?? Summary

| Approach | Executable Required? | Best For |
|----------|---------------------|----------|
| **STDIO Transport** | Yes (client spawns it) | Development, local testing |
| **HTTP/SSE Transport** | No (hosted service) | Production, remote clients |

The MCP Bridge pattern allows you to:
- ? Keep your existing REST APIs unchanged
- ? Expose REST endpoints to AI agents via MCP
- ? Add authentication and authorization
- ? Deploy flexibly (local exe or remote service)
- ? Support any backend technology (.NET 4.8, .NET Core, Java, Python, etc.)
