"""
MCP Server - Python Implementation

This is a standalone MCP (Model Context Protocol) server that exposes REST API endpoints as MCP tools.
It connects to a backend REST API (SampleRestApi) and provides MCP-compatible tool interfaces.

Supports both:
- SSE (Server-Sent Events) transport for remote connections
- STDIO transport for local subprocess communication

Run with: python mcp_server.py
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ???????????????????????????????????????????????????????????????????????????
# CONFIGURATION
# ???????????????????????????????????????????????????????????????????????????

class McpServerConfig:
    """Configuration for the MCP Server."""
    
    def __init__(self):
        self.rest_api_base_url = os.getenv("REST_API_BASE_URL", "http://localhost:5001")
        self.rest_api_auth_token = os.getenv("REST_API_AUTH_TOKEN", "Bearer demo-token-12345")
        self.server_name = os.getenv("MCP_SERVER_NAME", "python-mcp-server")
        self.server_version = "1.0.0"


config = McpServerConfig()


# ???????????????????????????????????????????????????????????????????????????
# REST API CLIENT
# ???????????????????????????????????????????????????????????????????????????

class RestApiClient:
    """Client for calling the backend REST API."""
    
    def __init__(self, base_url: str, auth_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = self.auth_token
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get(self, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()
    
    async def post(self, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.post(path, json=data)
        response.raise_for_status()
        return response.json()
    
    async def put(self, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.put(path, json=data)
        response.raise_for_status()
        return response.json()
    
    # Employee APIs
    async def get_all_employees(self) -> Dict[str, Any]:
        return await self.get("/api/employees")
    
    async def get_employee(self, employee_id: int) -> Dict[str, Any]:
        return await self.get(f"/api/employees/{employee_id}")
    
    async def search_employees(self, name: str = None, department: str = None) -> Dict[str, Any]:
        params = {}
        if name:
            params["name"] = name
        if department:
            params["department"] = department
        return await self.get("/api/employees/search", params)
    
    # Product APIs
    async def get_all_products(self) -> Dict[str, Any]:
        return await self.get("/api/products")
    
    async def get_product(self, product_id: int) -> Dict[str, Any]:
        return await self.get(f"/api/products/{product_id}")
    
    async def get_products_by_category(self, category: str) -> Dict[str, Any]:
        return await self.get(f"/api/products/category/{category}")
    
    # Order APIs
    async def get_all_orders(self) -> Dict[str, Any]:
        return await self.get("/api/orders")
    
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        return await self.get(f"/api/orders/{order_id}")
    
    async def create_order(self, customer_id: int, product_ids: List[int]) -> Dict[str, Any]:
        return await self.post("/api/orders", {
            "customer_id": customer_id,
            "product_ids": product_ids
        })
    
    # Inventory APIs
    async def get_inventory(self) -> Dict[str, Any]:
        return await self.get("/api/inventory")
    
    async def update_stock(self, product_id: int, new_stock: int) -> Dict[str, Any]:
        return await self.put(f"/api/inventory/{product_id}/stock", {"new_stock": new_stock})
    
    # Health
    async def check_health(self) -> Dict[str, Any]:
        return await self.get("/api/health")


# Global REST API client
rest_client = RestApiClient(config.rest_api_base_url, config.rest_api_auth_token)


# ???????????????????????????????????????????????????????????????????????????
# MCP TOOL DEFINITIONS
# ???????????????????????????????????????????????????????????????????????????

MCP_TOOLS = [
    {
        "name": "get_all_employees",
        "description": "Get a list of all employees in the company",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_employee",
        "description": "Get details of a specific employee by their ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "integer", "description": "The employee ID"}
            },
            "required": ["employee_id"]
        }
    },
    {
        "name": "search_employees",
        "description": "Search for employees by name and/or department",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to search for"},
                "department": {"type": "string", "description": "Department to filter by"}
            },
            "required": []
        }
    },
    {
        "name": "get_all_products",
        "description": "Get a list of all products in the catalog",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_product",
        "description": "Get details of a specific product by its ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "The product ID"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_products_by_category",
        "description": "Get all products in a specific category",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Product category (e.g., Electronics, Furniture)"}
            },
            "required": ["category"]
        }
    },
    {
        "name": "get_all_orders",
        "description": "Get a list of all orders",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_order",
        "description": "Get details of a specific order by its ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "create_order",
        "description": "Create a new order for a customer",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Customer ID"},
                "product_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of product IDs to order"
                }
            },
            "required": ["customer_id", "product_ids"]
        }
    },
    {
        "name": "get_inventory",
        "description": "Get current inventory status for all products",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "update_stock",
        "description": "Update the stock quantity for a product",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID"},
                "new_stock": {"type": "integer", "description": "New stock quantity"}
            },
            "required": ["product_id", "new_stock"]
        }
    },
    {
        "name": "check_api_health",
        "description": "Check the health status of the REST API",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


# ???????????????????????????????????????????????????????????????????????????
# TOOL EXECUTION
# ???????????????????????????????????????????????????????????????????????????

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute an MCP tool and return the result as JSON string."""
    try:
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        if tool_name == "get_all_employees":
            result = await rest_client.get_all_employees()
        
        elif tool_name == "get_employee":
            employee_id = arguments.get("employee_id")
            if not employee_id:
                return json.dumps({"error": "employee_id is required"})
            result = await rest_client.get_employee(int(employee_id))
        
        elif tool_name == "search_employees":
            name = arguments.get("name")
            department = arguments.get("department")
            result = await rest_client.search_employees(name, department)
        
        elif tool_name == "get_all_products":
            result = await rest_client.get_all_products()
        
        elif tool_name == "get_product":
            product_id = arguments.get("product_id")
            if not product_id:
                return json.dumps({"error": "product_id is required"})
            result = await rest_client.get_product(int(product_id))
        
        elif tool_name == "get_products_by_category":
            category = arguments.get("category")
            if not category:
                return json.dumps({"error": "category is required"})
            result = await rest_client.get_products_by_category(category)
        
        elif tool_name == "get_all_orders":
            result = await rest_client.get_all_orders()
        
        elif tool_name == "get_order":
            order_id = arguments.get("order_id")
            if not order_id:
                return json.dumps({"error": "order_id is required"})
            result = await rest_client.get_order(str(order_id))
        
        elif tool_name == "create_order":
            customer_id = arguments.get("customer_id")
            product_ids = arguments.get("product_ids", [])
            if not customer_id:
                return json.dumps({"error": "customer_id is required"})
            if not product_ids:
                return json.dumps({"error": "product_ids is required"})
            result = await rest_client.create_order(int(customer_id), product_ids)
        
        elif tool_name == "get_inventory":
            result = await rest_client.get_inventory()
        
        elif tool_name == "update_stock":
            product_id = arguments.get("product_id")
            new_stock = arguments.get("new_stock")
            if not product_id:
                return json.dumps({"error": "product_id is required"})
            if new_stock is None:
                return json.dumps({"error": "new_stock is required"})
            result = await rest_client.update_stock(int(product_id), int(new_stock))
        
        elif tool_name == "check_api_health":
            result = await rest_client.check_health()
        
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        
        logger.info(f"Tool {tool_name} executed successfully")
        return json.dumps(result, default=str)
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error executing tool {tool_name}: {e}")
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return json.dumps({"error": str(e)})


# ???????????????????????????????????????????????????????????????????????????
# FASTAPI APPLICATION (SSE Transport)
# ???????????????????????????????????????????????????????????????????????????

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    logger.info(f"Starting Python MCP Server...")
    logger.info(f"REST API URL: {config.rest_api_base_url}")
    yield
    logger.info("Shutting down Python MCP Server...")
    await rest_client.close()


app = FastAPI(
    title="Python MCP Server",
    description="MCP Server that exposes REST API endpoints as MCP tools",
    version=config.server_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToolCallRequest(BaseModel):
    arguments: Dict[str, Any] = {}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "server": config.server_name,
        "version": config.server_version,
        "restApiUrl": config.rest_api_base_url,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    return {"tools": MCP_TOOLS, "total": len(MCP_TOOLS)}


@app.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get details of a specific tool."""
    tool = next((t for t in MCP_TOOLS if t["name"] == tool_name), None)
    if not tool:
        return JSONResponse(status_code=404, content={"error": f"Tool '{tool_name}' not found"})
    return tool


@app.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, request: ToolCallRequest):
    """Call an MCP tool."""
    tool = next((t for t in MCP_TOOLS if t["name"] == tool_name), None)
    if not tool:
        return JSONResponse(status_code=404, content={"error": f"Tool '{tool_name}' not found"})
    
    result = await execute_tool(tool_name, request.arguments)
    
    try:
        parsed_result = json.loads(result)
        return parsed_result
    except:
        return {"result": result}


# ???????????????????????????????????????????????????????????????????????????
# SSE ENDPOINT (For MCP SSE Transport)
# ???????????????????????????????????????????????????????????????????????????

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP protocol."""
    
    async def event_generator():
        # Send server info event
        server_info = {
            "jsonrpc": "2.0",
            "method": "server/info",
            "params": {
                "name": config.server_name,
                "version": config.server_version,
                "capabilities": {
                    "tools": True
                }
            }
        }
        yield f"data: {json.dumps(server_info)}\n\n"
        
        # Keep connection alive
        while True:
            if await request.is_disconnected():
                break
            
            # Send heartbeat
            heartbeat = {
                "jsonrpc": "2.0",
                "method": "heartbeat",
                "params": {"timestamp": datetime.utcnow().isoformat()}
            }
            yield f"data: {json.dumps(heartbeat)}\n\n"
            await asyncio.sleep(30)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ???????????????????????????????????????????????????????????????????????????
# STDIO TRANSPORT (For local MCP communication)
# ???????????????????????????????????????????????????????????????????????????

async def handle_stdio_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a JSON-RPC message from STDIO."""
    method = message.get("method", "")
    params = message.get("params", {})
    msg_id = message.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": config.server_name,
                    "version": config.server_version
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        result = await execute_tool(tool_name, arguments)
        
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
        }
    
    elif method == "notifications/initialized":
        # No response needed for notifications
        return None
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


async def run_stdio_server():
    """Run the MCP server using STDIO transport."""
    logger.info("Starting MCP Server in STDIO mode...")
    
    while True:
        try:
            # Read line from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            # Parse JSON-RPC message
            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                continue
            
            # Handle message
            response = await handle_stdio_message(message)
            
            # Send response (if any)
            if response:
                print(json.dumps(response), flush=True)
        
        except Exception as e:
            logger.error(f"Error in STDIO loop: {e}")


# ???????????????????????????????????????????????????????????????????????????
# MAIN ENTRY POINT
# ???????????????????????????????????????????????????????????????????????????

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Python MCP Server")
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default="http",
        help="Transport mode: 'http' for HTTP/SSE server, 'stdio' for STDIO transport"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5050,
        help="Port for HTTP server (default: 5050)"
    )
    parser.add_argument(
        "--rest-api-url",
        default=None,
        help="Base URL for the REST API (default: http://localhost:5001)"
    )
    
    args = parser.parse_args()
    
    # Override config if provided
    if args.rest_api_url:
        config.rest_api_base_url = args.rest_api_url
        rest_client.base_url = args.rest_api_url
    
    if args.transport == "stdio":
        # Run STDIO transport
        asyncio.run(run_stdio_server())
    else:
        # Run HTTP/SSE server
        import uvicorn
        print(f"Starting Python MCP Server on port {args.port}...")
        print(f"REST API URL: {config.rest_api_base_url}")
        print(f"Tools endpoint: http://localhost:{args.port}/tools")
        print(f"SSE endpoint: http://localhost:{args.port}/sse")
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
