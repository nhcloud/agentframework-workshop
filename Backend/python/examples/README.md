# Python MCP Examples

Python equivalents of the .NET MCP examples.

## Architecture

```
???????????????????????????????????????????????????????????????????????
?         sample_rest_api.py (Port 5001)                              ?
?  - /api/employees    - /api/products                                ?
?  - /api/orders       - /api/inventory                               ?
?  (Your business REST API)                                           ?
??????????????????????????????????????????????????????????????????????
                        ?
                        ? HTTP calls
                        ?
??????????????????????????????????????????????????????????????????????
?              mcp_server.py (Port 5050)                              ?
?  - /tools           - List available MCP tools                      ?
?  - /tools/{name}/call - Execute MCP tool                           ?
?  - /sse             - SSE transport endpoint                        ?
?  - STDIO mode       - For subprocess communication                  ?
??????????????????????????????????????????????????????????????????????
                        ?
                        ? MCP Protocol
                        ?
??????????????????????????????????????????????????????????????????????
?         Agent Framework (main.py - Port 8000)                       ?
?  - McpClientService connects to MCP servers                         ?
?  - AI agents can call MCP tools                                     ?
??????????????????????????????????????????????????????????????????????
```

## Quick Start

### Terminal 1: Start Sample REST API (Port 5001)

```bash
cd Backend/python/examples
python sample_rest_api.py
```

Or with uvicorn:
```bash
uvicorn sample_rest_api:app --port 5001 --reload
```

**Endpoints:**
- Swagger UI: http://localhost:5001/swagger
- Health: http://localhost:5001/api/health
- Employees: http://localhost:5001/api/employees
- Products: http://localhost:5001/api/products
- Orders: http://localhost:5001/api/orders
- Inventory: http://localhost:5001/api/inventory

### Terminal 2: Start MCP Server (Port 5050)

```bash
cd Backend/python/examples
python mcp_server.py --port 5050
```

Or specify a different REST API URL:
```bash
python mcp_server.py --port 5050 --rest-api-url http://localhost:5001
```

**Endpoints:**
- Health: http://localhost:5050/health
- Tools List: http://localhost:5050/tools
- Tool Call: POST http://localhost:5050/tools/{tool_name}/call
- SSE: http://localhost:5050/sse

### Terminal 3: Start Agent Framework (Port 8000)

```bash
cd Backend/python
uvicorn main:app --port 8000
```

## Test the MCP Stack

```bash
# 1. Check REST API
curl http://localhost:5001/api/employees

# 2. Check MCP Server tools
curl http://localhost:5050/tools

# 3. Call MCP tool
curl -X POST http://localhost:5050/tools/get_all_employees/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {}}'

# 4. Call tool with arguments
curl -X POST http://localhost:5050/tools/search_employees/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"department": "Engineering"}}'

# 5. Create an order
curl -X POST http://localhost:5050/tools/create_order/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"customer_id": 1, "product_ids": [1, 2]}}'
```

## Available MCP Tools

| Tool Name | Description |
|-----------|-------------|
| `get_all_employees` | Get a list of all employees |
| `get_employee` | Get employee by ID |
| `search_employees` | Search employees by name/department |
| `get_all_products` | Get a list of all products |
| `get_product` | Get product by ID |
| `get_products_by_category` | Get products by category |
| `get_all_orders` | Get a list of all orders |
| `get_order` | Get order by ID |
| `create_order` | Create a new order |
| `get_inventory` | Get inventory status |
| `update_stock` | Update product stock |
| `check_api_health` | Check REST API health |

## STDIO Transport Mode

The MCP Server supports STDIO transport for subprocess communication:

```bash
python mcp_server.py --transport stdio
```

Example JSON-RPC messages:

```json
// Initialize
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}

// List tools
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

// Call tool
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_all_employees", "arguments": {}}}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REST_API_BASE_URL` | `http://localhost:5001` | Base URL for REST API |
| `REST_API_AUTH_TOKEN` | `Bearer demo-token-12345` | Auth token |
| `MCP_SERVER_NAME` | `python-mcp-server` | Server name |

## Comparison with .NET

| .NET Component | Python Equivalent |
|----------------|-------------------|
| `Examples/SampleRestApi/` | `examples/sample_rest_api.py` |
| `Examples/SampleMcpBridge/` | `examples/mcp_server.py` (HTTP mode) |
| `McpServer/` | `examples/mcp_server.py` (STDIO mode) |
