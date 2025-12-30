"""
MCP (Model Context Protocol) Router for Python.

This router provides API endpoints for managing MCP servers and tools.
Matches the .NET McpController implementation.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


# Request/Response Models
class McpToolCallRequest(BaseModel):
    """Request to call an MCP tool."""
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


class McpSimulateRequest(BaseModel):
    """Request to simulate an MCP operation."""
    operation: str
    arguments: Optional[Dict[str, Any]] = None


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# ???????????????????????????????????????????????????????????????????????????
# MCP SERVER MANAGEMENT ENDPOINTS
# ???????????????????????????????????????????????????????????????????????????

@router.get("/servers")
async def get_servers(request: Request) -> Dict[str, Any]:
    """
    Get list of all configured MCP servers.
    
    Returns information about each server including:
    - Name and description
    - Transport type (SSE or STDIO)
    - Connection endpoint
    - Enabled status
    """
    try:
        mcp_service = request.app.state.mcp_client_service
        servers = await mcp_service.get_configured_servers()
        
        return {
            "servers": [
                {
                    "name": s.name,
                    "description": s.description,
                    "transport": s.transport,
                    "endpoint": s.endpoint,
                    "enabled": s.enabled,
                    "isConfigured": s.is_configured
                }
                for s in servers
            ],
            "total": len(servers)
        }
    except Exception as ex:
        logger.error(f"Error getting MCP servers: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve MCP servers")


@router.get("/servers/{server_name}")
async def get_server(server_name: str, request: Request) -> Dict[str, Any]:
    """Get details for a specific MCP server."""
    try:
        mcp_service = request.app.state.mcp_client_service
        servers = await mcp_service.get_configured_servers()
        
        server = next((s for s in servers if s.name == server_name), None)
        if not server:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
        
        return {
            "name": server.name,
            "description": server.description,
            "transport": server.transport,
            "endpoint": server.endpoint,
            "enabled": server.enabled,
            "isConfigured": server.is_configured
        }
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error getting MCP server {server_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve MCP server")


@router.post("/servers/{server_name}/test")
async def test_server_connection(server_name: str, request: Request) -> Dict[str, Any]:
    """
    Test connection to an MCP server.
    
    Returns connection status, available tools count, and latency.
    """
    try:
        mcp_service = request.app.state.mcp_client_service
        result = await mcp_service.test_connection(server_name)
        
        return {
            "success": result.success,
            "serverName": result.server_name,
            "message": result.message,
            "error": result.error,
            "toolCount": result.tool_count,
            "durationMs": result.duration_ms
        }
    except Exception as ex:
        logger.error(f"Error testing MCP server {server_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to test MCP server connection")


# ???????????????????????????????????????????????????????????????????????????
# MCP TOOLS ENDPOINTS
# ???????????????????????????????????????????????????????????????????????????

@router.get("/tools")
async def get_all_tools(request: Request) -> Dict[str, Any]:
    """
    Get all available tools from all configured MCP servers.
    
    Returns a combined list of tools from all enabled servers.
    """
    try:
        mcp_service = request.app.state.mcp_client_service
        tools = await mcp_service.get_all_tools()
        
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "serverName": t.server_name,
                    "fullName": t.full_name,
                    "source": "mcp",
                    "inputSchema": t.input_schema
                }
                for t in tools
            ],
            "total": len(tools)
        }
    except Exception as ex:
        logger.error(f"Error getting MCP tools: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve MCP tools")


@router.get("/servers/{server_name}/tools")
async def get_server_tools(server_name: str, request: Request) -> Dict[str, Any]:
    """
    Get available tools from a specific MCP server.
    
    Returns list of tools with their names, descriptions, and input schemas.
    """
    try:
        mcp_service = request.app.state.mcp_client_service
        tools = await mcp_service.get_tools(server_name)
        
        return {
            "serverName": server_name,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "serverName": t.server_name,
                    "fullName": t.full_name,
                    "source": "mcp",
                    "inputSchema": t.input_schema
                }
                for t in tools
            ],
            "total": len(tools)
        }
    except Exception as ex:
        logger.error(f"Error getting tools from server {server_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve server tools")


@router.post("/servers/{server_name}/tools/{tool_name}/call")
async def call_tool(
    server_name: str,
    tool_name: str,
    request: Request,
    body: Optional[McpToolCallRequest] = None
) -> Dict[str, Any]:
    """
    Call a specific MCP tool on a server.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        body: Optional arguments for the tool
        
    Returns:
        Tool execution result
    """
    try:
        mcp_service = request.app.state.mcp_client_service
        
        arguments = body.arguments if body else None
        result = await mcp_service.call_tool(server_name, tool_name, arguments)
        
        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "serverName": result.server_name,
            "toolName": result.tool_name,
            "durationMs": result.duration_ms
        }
    except Exception as ex:
        logger.error(f"Error calling tool {tool_name} on {server_name}: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Failed to call tool: {str(ex)}")


# ???????????????????????????????????????????????????????????????????????????
# DEMO/SIMULATION ENDPOINTS
# ???????????????????????????????????????????????????????????????????????????

@router.post("/demo/simulate")
async def simulate_mcp_call(body: McpSimulateRequest, request: Request) -> Dict[str, Any]:
    """
    Simulate an MCP tool call using local data.
    
    This endpoint demonstrates MCP-style tool calling patterns
    without requiring an actual MCP server connection.
    
    Supported operations:
    - get_products: List products with optional category filter
    - get_product: Get product by ID
    - create_order: Create a new order
    - get_order: Get order by ID
    - get_customer_orders: Get orders for a customer
    - get_employees: List employees
    - get_employee: Get employee by ID
    - search_employees: Search employees by name/department
    """
    try:
        operation = body.operation
        args = body.arguments or {}
        
        # Simulated data (matching SampleRestApi)
        products = [
            {"id": 1, "name": "Laptop Pro", "category": "Electronics", "price": 1299.99, "stock": 50},
            {"id": 2, "name": "Wireless Mouse", "category": "Electronics", "price": 49.99, "stock": 200},
            {"id": 3, "name": "Office Chair", "category": "Furniture", "price": 399.99, "stock": 30},
            {"id": 4, "name": "Standing Desk", "category": "Furniture", "price": 599.99, "stock": 25},
            {"id": 5, "name": "Monitor 27\"", "category": "Electronics", "price": 349.99, "stock": 75}
        ]
        
        orders = [
            {"id": "ORD-20240101-0001", "customerId": 1, "productIds": [1, 2], "totalAmount": 1349.98, "status": "Delivered"},
            {"id": "ORD-20240102-0002", "customerId": 2, "productIds": [3], "totalAmount": 399.99, "status": "Shipped"},
            {"id": "ORD-20240103-0003", "customerId": 3, "productIds": [4, 5], "totalAmount": 1049.98, "status": "Processing"}
        ]
        
        employees = [
            {"id": 1, "name": "Alice Johnson", "email": "alice@company.com", "department": "Engineering", "title": "Senior Developer"},
            {"id": 2, "name": "Bob Smith", "email": "bob@company.com", "department": "Engineering", "title": "Tech Lead"},
            {"id": 3, "name": "Carol Williams", "email": "carol@company.com", "department": "Marketing", "title": "Marketing Manager"},
            {"id": 4, "name": "David Brown", "email": "david@company.com", "department": "Sales", "title": "Sales Representative"},
            {"id": 5, "name": "Eva Martinez", "email": "eva@company.com", "department": "HR", "title": "HR Director"}
        ]
        
        # Product operations
        if operation == "get_products" or operation == "get_all_products":
            category = args.get("category")
            if category:
                filtered = [p for p in products if p["category"].lower() == category.lower()]
                return {"success": True, "data": {"products": filtered, "total": len(filtered)}, "operation": operation}
            return {"success": True, "data": {"products": products, "total": len(products)}, "operation": operation}
        
        elif operation == "get_product":
            product_id = args.get("id") or args.get("product_id")
            if not product_id:
                return {"success": False, "error": "Product ID required", "operation": operation}
            product = next((p for p in products if p["id"] == int(product_id)), None)
            if not product:
                return {"success": False, "error": f"Product {product_id} not found", "operation": operation}
            return {"success": True, "data": product, "operation": operation}
        
        elif operation == "get_products_by_category":
            category = args.get("category")
            if not category:
                return {"success": False, "error": "Category required", "operation": operation}
            filtered = [p for p in products if p["category"].lower() == category.lower()]
            return {"success": True, "data": {"products": filtered, "total": len(filtered)}, "operation": operation}
        
        # Order operations
        elif operation == "create_order":
            customer_id = args.get("customerId") or args.get("customer_id")
            product_id = args.get("productId") or args.get("product_id")
            quantity = args.get("quantity", 1)
            
            if not customer_id or not product_id:
                return {"success": False, "error": "customerId and productId required", "operation": operation}
            
            product = next((p for p in products if p["id"] == int(product_id)), None)
            if not product:
                return {"success": False, "error": f"Product {product_id} not found", "operation": operation}
            
            new_order = {
                "id": f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{len(orders) + 1:04d}",
                "customerId": customer_id,
                "productIds": [int(product_id)],
                "totalAmount": product["price"] * quantity,
                "status": "Pending",
                "createdAt": datetime.utcnow().isoformat()
            }
            return {"success": True, "data": new_order, "operation": operation}
        
        elif operation == "get_order":
            order_id = args.get("id") or args.get("order_id")
            if not order_id:
                return {"success": False, "error": "Order ID required", "operation": operation}
            order = next((o for o in orders if o["id"] == str(order_id)), None)
            if not order:
                return {"success": False, "error": f"Order {order_id} not found", "operation": operation}
            return {"success": True, "data": order, "operation": operation}
        
        elif operation == "get_all_orders":
            return {"success": True, "data": {"orders": orders, "total": len(orders)}, "operation": operation}
        
        elif operation == "get_customer_orders":
            customer_id = args.get("customerId") or args.get("customer_id")
            if not customer_id:
                return {"success": False, "error": "customerId required", "operation": operation}
            customer_orders = [o for o in orders if str(o["customerId"]) == str(customer_id)]
            return {"success": True, "data": {"orders": customer_orders, "total": len(customer_orders)}, "operation": operation}
        
        # Employee operations
        elif operation == "get_employees" or operation == "get_all_employees":
            return {"success": True, "data": {"employees": employees, "total": len(employees)}, "operation": operation}
        
        elif operation == "get_employee":
            employee_id = args.get("id") or args.get("employee_id")
            if not employee_id:
                return {"success": False, "error": "Employee ID required", "operation": operation}
            employee = next((e for e in employees if e["id"] == int(employee_id)), None)
            if not employee:
                return {"success": False, "error": f"Employee {employee_id} not found", "operation": operation}
            return {"success": True, "data": employee, "operation": operation}
        
        elif operation == "search_employees":
            name = args.get("name")
            department = args.get("department")
            results = employees.copy()
            
            if name:
                results = [e for e in results if name.lower() in e["name"].lower()]
            if department:
                results = [e for e in results if e["department"].lower() == department.lower()]
            
            return {"success": True, "data": {"employees": results, "total": len(results)}, "operation": operation}
        
        # Inventory operations
        elif operation == "get_inventory":
            inventory = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "stock": p["stock"],
                    "status": "In Stock" if p["stock"] > 10 else "Low Stock" if p["stock"] > 0 else "Out of Stock"
                }
                for p in products
            ]
            return {"success": True, "data": {"inventory": inventory, "total": len(inventory)}, "operation": operation}
        
        # Health check
        elif operation == "check_api_health" or operation == "health_check":
            return {
                "success": True,
                "data": {"status": "healthy", "timestamp": datetime.utcnow().isoformat()},
                "operation": operation
            }
        
        else:
            return {"success": False, "error": f"Unknown operation: {operation}", "operation": operation}
    
    except Exception as ex:
        logger.error(f"Error in MCP simulation: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(ex)}")


@router.get("/health")
async def mcp_health(request: Request) -> Dict[str, Any]:
    """Check MCP service health and available servers."""
    try:
        mcp_service = request.app.state.mcp_client_service
        servers = await mcp_service.get_configured_servers()
        
        return {
            "status": "healthy",
            "service": "MCP Client Service",
            "timestamp": datetime.utcnow().isoformat(),
            "serverCount": len(servers),
            "servers": [
                {"name": s.name, "enabled": s.enabled, "transport": s.transport}
                for s in servers
            ]
        }
    except Exception as ex:
        logger.error(f"MCP health check failed: {str(ex)}")
        return {
            "status": "unhealthy",
            "error": str(ex),
            "timestamp": datetime.utcnow().isoformat()
        }
