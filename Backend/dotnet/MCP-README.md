# MCP (Model Context Protocol) Integration

This project includes MCP (Model Context Protocol) support for connecting AI agents to external tools and data sources.

## Overview

MCP is a standardized protocol that allows AI models to:
- Call external tools/functions
- Access resources (files, databases, APIs)
- Maintain context across interactions

## Components

### 1. MCP Client (Main Project)

The main project includes an MCP client that can connect to external MCP servers.

**Files:**
- `Services/McpClientService.cs` - MCP client service implementation
- `Controllers/McpController.cs` - REST API for MCP management
- `Configuration/McpConfig.cs` - Configuration models

**Features:**
- Connect to multiple MCP servers (stdio, HTTP/SSE transports)
- List and call tools from MCP servers
- Test server connections
- Access server resources

### 2. MCP Server (Separate Project)

A standalone MCP server that exposes REST APIs as MCP tools.

**Location:** `McpServer/`

**Files:**
- `Program.cs` - Server entry point
- `DemoApiClient.cs` - HTTP client for Demo API
- `RemoteApiClient.cs` - Generic HTTP client for any remote REST API
- `Tools/DemoApiTools.cs` - Demo API MCP tool definitions
- `Tools/RemoteApiTools.cs` - Generic remote API MCP tool definitions

## Exposing Your Remote REST APIs as MCP Tools

There are **two approaches** to expose your remote REST APIs via MCP:

### Approach 1: Use the Built-in MCP Server (Recommended)

The MCP Server project includes a generic `RemoteApiClient` and `RemoteApiTools` that can wrap **any REST API**.

#### Step 1: Configure your API in `config.yml`

```yaml
mcp:
  servers:
    - name: "my-remote-api"
      description: "My Remote REST API"
      transport: "stdio"
      command: "dotnet"
      arguments:
        - "run"
        - "--project"
        - "McpServer/DotNetAgentFramework.McpServer.csproj"
      enabled: true
      environmentVariables:
        REMOTE_API_BASE_URL: "https://your-api.example.com"
        REMOTE_API_AUTH_TOKEN: "Bearer your-token"
```

#### Step 2: Or configure in `McpServer/appsettings.json`

```json
{
  "RemoteApi": {
    "BaseUrl": "https://your-api.example.com",
    "AuthToken": "Bearer your-token",
    "Headers": {
      "X-Api-Key": "your-api-key",
      "X-Client-Id": "mcp-server"
    }
  }
}
```

#### Available Generic Tools

The `RemoteApiTools` provides these generic tools:

| Tool | Description |
|------|-------------|
| `list_resources` | GET /api/resources with query params |
| `get_resource` | GET /api/resources/{id} |
| `create_resource` | POST /api/resources |
| `update_resource` | PUT /api/resources/{id} |
| `delete_resource` | DELETE /api/resources/{id} |
| `search_resources` | GET /api/resources/search |
| `custom_api_call` | Execute any HTTP method to any endpoint |
| `api_health_check` | Check API health status |

### Approach 2: Create Custom MCP Tools

For specific APIs with custom logic, create dedicated tool classes:

#### Step 1: Create a new tool file in `McpServer/Tools/`

```csharp
using ModelContextProtocol.Server;
using System.ComponentModel;

namespace DotNetAgentFramework.McpServer.Tools;

[McpServerToolType]
public class MyCustomApiTools
{
    private readonly RemoteApiClient _apiClient;

    public MyCustomApiTools(RemoteApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    [McpServerTool(Name = "get_users")]
    [Description("Get list of users from my API")]
    public async Task<string> GetUsers(
        [Description("Department filter")] string? department = null)
    {
        var queryParams = new Dictionary<string, string>();
        if (!string.IsNullOrEmpty(department))
            queryParams["department"] = department;

        var result = await _apiClient.GetAsync("/api/users", queryParams);
        return JsonSerializer.Serialize(result);
    }

    [McpServerTool(Name = "create_ticket")]
    [Description("Create a support ticket")]
    public async Task<string> CreateTicket(
        [Description("Ticket title")] string title,
        [Description("Ticket description")] string description,
        [Description("Priority (low/medium/high)")] string priority = "medium")
    {
        var body = new { title, description, priority };
        var result = await _apiClient.PostAsync("/api/tickets", body);
        return JsonSerializer.Serialize(result);
    }
}
```

#### Step 2: Register the client in `Program.cs`

The tools are automatically discovered via assembly scanning.

### Approach 3: Connect to an Existing MCP Server

If your API already has an MCP server endpoint:

```yaml
mcp:
  servers:
    - name: "existing-mcp-server"
      transport: "sse"
      endpoint: "https://your-api.example.com/mcp/sse"
      authorization: "Bearer your-token"
      enabled: true
```

## Configuration Reference

### `config.yml` - MCP Server Configuration

```yaml
mcp:
  enabled: true
  defaultTimeoutSeconds: 30
  servers:
    - name: "server-name"           # Unique identifier
      description: "Description"     # Human-readable description
      transport: "stdio"             # "stdio" or "sse"
      
      # For stdio transport:
      command: "dotnet"              # Executable
      arguments:                     # Command arguments
        - "run"
        - "--project"
        - "path/to/project.csproj"
      environmentVariables:          # Env vars for the process
        API_KEY: "value"
      
      # For SSE transport:
      endpoint: "http://..."         # MCP server URL
      authorization: "Bearer ..."    # Auth header
      headers:                       # Additional headers
        X-Custom: "value"
      
      # Common options:
      enabled: true                  # Enable/disable
      timeoutSeconds: 30             # Operation timeout
      allowedTools:                  # Tool whitelist (optional)
        - "tool_1"
        - "tool_2"
```

### `McpServer/appsettings.json` - Server Settings

```json
{
  "DEMO_API_BASE_URL": "http://localhost:8000",
  "DEMO_API_AUTH_TOKEN": "Bearer demo-token",
  
  "RemoteApi": {
    "BaseUrl": "https://your-api.example.com",
    "AuthToken": "Bearer your-token",
    "Headers": {
      "X-Api-Key": "key",
      "X-Custom-Header": "value"
    }
  }
}
```

## Usage Examples

### 1. Start the Main API

```bash
cd Backend/dotnet
dotnet run
```

### 2. Start the MCP Server Manually (for testing)

```bash
cd Backend/dotnet/McpServer
dotnet run
```

### 3. Call MCP Tools via REST API

```bash
# List configured servers
curl http://localhost:8000/api/mcp/servers

# Get tools from a server
curl http://localhost:8000/api/mcp/servers/my-remote-api/tools

# Call a tool
curl -X POST http://localhost:8000/api/mcp/servers/my-remote-api/tools/list_resources/call \
  -H "Content-Type: application/json" \
  -d '{"arguments":{"type":"user","limit":10}}'

# Use custom_api_call for any endpoint
curl -X POST http://localhost:8000/api/mcp/servers/my-remote-api/tools/custom_api_call/call \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {
      "method": "GET",
      "endpoint": "/api/v2/special-endpoint",
      "queryParamsJson": "{\"filter\":\"active\"}"
    }
  }'
```

### 4. Use the MCP Simulation Endpoint

```bash
curl -X POST http://localhost:8000/api/mcp/demo/simulate \
  -H "Content-Type: application/json" \
  -d '{"operation":"get_products","arguments":{"category":"Electronics"}}'
```

## Architecture

```
???????????????????????????????????????????????????????????????
?                    Main API Server                          ?
?  ???????????????????????????????????????????????????????  ?
?  ?              MCP Client Service                      ?  ?
?  ?  - Connects to MCP servers                          ?  ?
?  ?  - Routes tool calls                                ?  ?
?  ???????????????????????????????????????????????????????  ?
???????????????????????????????????????????????????????????????
                           ?
           ?????????????????????????????????
           ?               ?               ?
           ?               ?               ?
???????????????????? ???????????????? ????????????????????
? MCP Server       ? ? External MCP ? ? Third-party MCP  ?
? (Your REST API)  ? ? (SSE/HTTP)   ? ? (npx servers)    ?
?                  ? ?              ? ?                  ?
? RemoteApiTools   ? ? Direct MCP   ? ? GitHub, Slack,   ?
? ?                ? ? Connection   ? ? Postgres, etc.   ?
? RemoteApiClient  ? ???????????????? ????????????????????
? ?                ?
? Your REST API    ?
????????????????????
```

## Summary

| Scenario | Solution |
|----------|----------|
| Wrap any REST API quickly | Use `RemoteApiTools` with `custom_api_call` |
| Create specific tools for your API | Add custom tool class in `McpServer/Tools/` |
| Connect to existing MCP server | Use SSE transport with endpoint URL |
| Use community MCP servers | Use npx with official packages |
