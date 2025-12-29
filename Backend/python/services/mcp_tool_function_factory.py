"""
MCP Tool Function Factory for Python.

This factory creates callable function wrappers for MCP tools,
enabling LLM-driven function calling where the model decides when to call tools.

Matches the .NET McpToolFunctionFactory implementation.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass

from .mcp_client_service import McpClientService, McpToolInfo

logger = logging.getLogger(__name__)


@dataclass
class SelectedToolInfo:
    """Information about a selected tool."""
    name: str
    source: str  # "mcp" or "local"
    server_name: Optional[str] = None
    full_name: Optional[str] = None
    transport: Optional[str] = None
    description: Optional[str] = None


@dataclass
class McpToolFunction:
    """Wrapper for an MCP tool as a callable function."""
    name: str
    description: str
    server_name: str
    invoke: Callable[[Optional[Dict[str, Any]]], Awaitable[str]]
    parameters: Optional[Dict[str, Any]] = None


class McpToolFunctionFactory:
    """
    Factory for creating callable function wrappers around MCP tools.
    
    This allows MCP tools to be used with LLM function calling,
    enabling the model to decide when to call tools (enterprise-style).
    """
    
    # Tool descriptions for common tools
    TOOL_DESCRIPTIONS = {
        "get_all_employees": "Get a list of all employees in the system. Returns employee names, IDs, departments, and contact information.",
        "get_employee": "Get details for a specific employee by their ID. Requires an 'employee_id' parameter.",
        "search_employees": "Search for employees by name, department, or other criteria. Accepts 'name' and 'department' parameters.",
        "get_all_products": "Get a list of all products in the catalog. Returns product names, prices, and availability.",
        "get_product": "Get details for a specific product by its ID. Requires a 'product_id' parameter.",
        "get_products_by_category": "Get all products in a specific category. Requires a 'category' parameter.",
        "get_all_orders": "Get a list of all orders. Returns order details including status and items.",
        "get_order": "Get details for a specific order by its ID. Requires an 'order_id' parameter.",
        "create_order": "Create a new order. Requires 'customer_id' and 'product_id' parameters.",
        "get_customer_orders": "Get all orders for a specific customer. Requires a 'customer_id' parameter.",
        "get_weather": "Get current weather information for a location. Requires a 'location' parameter.",
        "get_weather_locations": "Get a list of available weather locations.",
        "get_inventory": "Get current inventory/stock levels for products.",
        "update_stock": "Update the stock level for a product. Requires 'product_id' and 'new_stock' parameters.",
        "check_api_health": "Check the health status of the API.",
    }
    
    def __init__(self, mcp_client_service: McpClientService):
        """
        Initialize the factory.
        
        Args:
            mcp_client_service: Service for calling MCP tools
        """
        self._mcp_client = mcp_client_service
        logger.info("McpToolFunctionFactory initialized")
    
    async def create_functions(
        self,
        selected_tools: List[SelectedToolInfo]
    ) -> List[McpToolFunction]:
        """
        Create callable function wrappers for selected MCP tools.
        
        Args:
            selected_tools: List of tools to create functions for
            
        Returns:
            List of McpToolFunction wrappers
        """
        functions = []
        
        for tool in selected_tools:
            # Skip local tools - they're handled by the agent
            if tool.source == "local":
                logger.debug(f"Skipping local tool {tool.name} - handled by agent")
                continue
            
            if tool.source != "mcp" or not tool.server_name:
                logger.warning(f"Invalid MCP tool configuration for {tool.name}")
                continue
            
            try:
                function = self._create_mcp_tool_function(tool)
                functions.append(function)
                logger.info(f"Created function wrapper for MCP tool: {tool.server_name}.{tool.name}")
            except Exception as ex:
                logger.error(f"Failed to create function for MCP tool {tool.name}: {str(ex)}")
        
        return functions
    
    async def create_functions_from_server(
        self,
        server_name: str
    ) -> List[McpToolFunction]:
        """
        Create function wrappers for all tools from a specific MCP server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            List of McpToolFunction wrappers
        """
        functions = []
        
        try:
            tools = await self._mcp_client.get_tools(server_name)
            
            for tool in tools:
                selected_tool = SelectedToolInfo(
                    name=tool.name,
                    source="mcp",
                    server_name=server_name,
                    full_name=tool.full_name,
                    description=tool.description
                )
                
                function = self._create_mcp_tool_function(selected_tool)
                functions.append(function)
                logger.debug(f"Created function for {tool.name} from server {server_name}")
            
        except Exception as ex:
            logger.error(f"Failed to create functions from server {server_name}: {str(ex)}")
        
        return functions
    
    def _create_mcp_tool_function(self, tool: SelectedToolInfo) -> McpToolFunction:
        """
        Create a single MCP tool function wrapper.
        
        Args:
            tool: Tool information
            
        Returns:
            McpToolFunction wrapper
        """
        tool_name = tool.name
        server_name = tool.server_name
        description = tool.description or self.TOOL_DESCRIPTIONS.get(
            tool_name,
            f"Execute the {tool_name} operation via MCP."
        )
        
        # Create the async invoker function
        async def invoke(args: Optional[Dict[str, Any]] = None) -> str:
            logger.info(
                f"Function invoking MCP tool: {server_name}.{tool_name} "
                f"with args: {json.dumps(args) if args else 'none'}"
            )
            
            try:
                result = await self._mcp_client.call_tool(server_name, tool_name, args)
                
                if result.success:
                    logger.info(
                        f"MCP tool {tool_name} succeeded: {len(result.result or '')} chars"
                    )
                    return result.result or "Tool executed successfully but returned no data."
                else:
                    logger.warning(f"MCP tool {tool_name} failed: {result.error}")
                    return f"Error: {result.error}"
                    
            except Exception as ex:
                logger.error(f"Exception calling MCP tool {tool_name}: {str(ex)}")
                return f"Error calling tool: {str(ex)}"
        
        return McpToolFunction(
            name=tool_name,
            description=description,
            server_name=server_name,
            invoke=invoke,
            parameters=self._get_tool_parameters(tool_name)
        )
    
    def _get_tool_parameters(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get parameter schema for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Parameter schema dict or None
        """
        # Define parameter schemas for known tools
        schemas = {
            "get_employee": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "integer", "description": "The employee ID"}
                },
                "required": ["employee_id"]
            },
            "search_employees": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to search for"},
                    "department": {"type": "string", "description": "Department to filter by"}
                }
            },
            "get_product": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID"}
                },
                "required": ["product_id"]
            },
            "get_products_by_category": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Product category"}
                },
                "required": ["category"]
            },
            "get_order": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID"}
                },
                "required": ["order_id"]
            },
            "create_order": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer ID"},
                    "product_id": {"type": "integer", "description": "Product ID"},
                    "quantity": {"type": "integer", "description": "Quantity to order", "default": 1}
                },
                "required": ["customer_id", "product_id"]
            },
            "get_customer_orders": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer ID"}
                },
                "required": ["customer_id"]
            },
            "get_weather": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location for weather"}
                },
                "required": ["location"]
            },
            "update_stock": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                    "new_stock": {"type": "integer", "description": "New stock quantity"}
                },
                "required": ["product_id", "new_stock"]
            }
        }
        
        return schemas.get(tool_name)
    
    def get_tool_for_openai(self, function: McpToolFunction) -> Dict[str, Any]:
        """
        Convert an MCP tool function to OpenAI function calling format.
        
        Args:
            function: McpToolFunction to convert
            
        Returns:
            OpenAI tool definition dict
        """
        return {
            "type": "function",
            "function": {
                "name": function.name,
                "description": function.description,
                "parameters": function.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    def get_tools_for_openai(self, functions: List[McpToolFunction]) -> List[Dict[str, Any]]:
        """
        Convert multiple MCP tool functions to OpenAI function calling format.
        
        Args:
            functions: List of McpToolFunctions
            
        Returns:
            List of OpenAI tool definitions
        """
        return [self.get_tool_for_openai(f) for f in functions]
