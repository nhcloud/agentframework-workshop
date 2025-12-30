"""
MCP (Model Context Protocol) Client Service for Python.

This service manages connections to MCP servers and provides methods to:
- List configured MCP servers
- Retrieve available tools from MCP servers
- Call MCP tools with arguments

Matches the .NET McpClientService implementation.
"""

import logging
import asyncio
import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import os

logger = logging.getLogger(__name__)


@dataclass
class McpServerConfig:
    """Configuration for an MCP server."""
    name: str
    description: str = ""
    transport: str = "sse"  # "sse" or "stdio"
    endpoint: Optional[str] = None  # For SSE transport
    command: Optional[str] = None  # For STDIO transport
    arguments: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout_seconds: int = 30


@dataclass
class McpServerInfo:
    """Information about a configured MCP server."""
    name: str
    description: str
    transport: str
    endpoint: Optional[str]
    enabled: bool
    is_configured: bool


@dataclass
class McpToolInfo:
    """Information about an MCP tool."""
    name: str
    description: str
    server_name: str
    full_name: str
    input_schema: Optional[str] = None


@dataclass
class McpToolResult:
    """Result from calling an MCP tool."""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    server_name: Optional[str] = None
    tool_name: Optional[str] = None
    duration_ms: int = 0


@dataclass
class McpConnectionTestResult:
    """Result from testing MCP server connection."""
    success: bool
    error: Optional[str] = None
    message: Optional[str] = None
    server_name: Optional[str] = None
    tool_count: int = 0
    duration_ms: int = 0


class McpClientService:
    """
    Service for managing MCP server connections and tool invocations.
    
    Supports both SSE (Server-Sent Events) and STDIO transports.
    Matches the .NET McpClientService implementation.
    """
    
    def __init__(self):
        """Initialize the MCP client service."""
        self._servers: Dict[str, McpServerConfig] = {}
        self._http_client = httpx.AsyncClient(timeout=60.0)
        self._load_default_servers()
        logger.info(f"McpClientService initialized with {len(self._servers)} servers")
    
    def _load_default_servers(self):
        """Load default MCP server configurations."""
        # Remote MCP Bridge (SSE) - .NET SampleMcpBridge
        dotnet_sse_endpoint = os.getenv("MCP_SSE_ENDPOINT", "http://localhost:5050")
        self._servers["remote-mcp-bridge"] = McpServerConfig(
            name="remote-mcp-bridge",
            description="Remote MCP Bridge (SSE) - .NET SampleMcpBridge connecting to SampleRestApi",
            transport="sse",
            endpoint=dotnet_sse_endpoint,
            enabled=True,
            timeout_seconds=30
        )
        
        # Python MCP Server (SSE) - Python equivalent
        python_mcp_endpoint = os.getenv("PYTHON_MCP_ENDPOINT", "http://localhost:5050")
        self._servers["python-mcp-server"] = McpServerConfig(
            name="python-mcp-server",
            description="Python MCP Server (SSE) - Python implementation connecting to sample_rest_api",
            transport="sse",
            endpoint=python_mcp_endpoint,
            enabled=True,
            timeout_seconds=30
        )
        
        # Local MCP Server (STDIO) - can be spawned as subprocess
        self._servers["local-mcp-server"] = McpServerConfig(
            name="local-mcp-server",
            description="Local MCP Server (STDIO) - Bridges to SampleRestApi",
            transport="stdio",
            command="dotnet",
            arguments=["run", "--project", "McpServer/DotNetAgentFramework.McpServer.csproj"],
            environment_variables={
                "DEMO_API_BASE_URL": os.getenv("SAMPLE_REST_API_URL", "http://localhost:5001"),
                "DEMO_API_AUTH_TOKEN": "Bearer demo-token-12345"
            },
            enabled=True
        )
        
        # Python STDIO MCP Server
        self._servers["python-stdio-mcp"] = McpServerConfig(
            name="python-stdio-mcp",
            description="Python MCP Server (STDIO) - Local subprocess communication",
            transport="stdio",
            command="python",
            arguments=["examples/mcp_server.py", "--transport", "stdio"],
            environment_variables={
                "REST_API_BASE_URL": os.getenv("SAMPLE_REST_API_URL", "http://localhost:5001")
            },
            enabled=True
        )
        
        logger.info("Loaded default MCP server configurations")
    
    async def get_configured_servers(self) -> List[McpServerInfo]:
        """Get list of all configured MCP servers."""
        servers = []
        for name, config in self._servers.items():
            servers.append(McpServerInfo(
                name=config.name,
                description=config.description,
                transport=config.transport,
                endpoint=config.endpoint,
                enabled=config.enabled,
                is_configured=True
            ))
        return servers
    
    async def get_tools(self, server_name: str) -> List[McpToolInfo]:
        """
        Get available tools from a specific MCP server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            List of available tools
        """
        if server_name not in self._servers:
            logger.warning(f"MCP server '{server_name}' not found")
            return []
        
        config = self._servers[server_name]
        
        if not config.enabled:
            logger.warning(f"MCP server '{server_name}' is disabled")
            return []
        
        try:
            if config.transport == "sse":
                return await self._get_tools_sse(config)
            else:
                # STDIO transport - return predefined tools
                return self._get_predefined_tools(server_name)
        except Exception as ex:
            logger.error(f"Failed to get tools from {server_name}: {str(ex)}")
            return self._get_predefined_tools(server_name)
    
    async def _get_tools_sse(self, config: McpServerConfig) -> List[McpToolInfo]:
        """Get tools from an SSE MCP server."""
        tools = []
        
        # For SSE servers, we make an HTTP request to get available tools
        base_url = config.endpoint.rstrip("/") if config.endpoint else ""
        # Remove /sse suffix if present
        if base_url.endswith("/sse"):
            base_url = base_url[:-4]
        tools_url = f"{base_url}/tools"
        
        try:
            response = await self._http_client.get(tools_url, timeout=config.timeout_seconds)
            if response.status_code == 200:
                data = response.json()
                for tool in data.get("tools", []):
                    tools.append(McpToolInfo(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        server_name=config.name,
                        full_name=f"{config.name}.{tool.get('name', '')}",
                        input_schema=json.dumps(tool.get("inputSchema")) if tool.get("inputSchema") else None
                    ))
            logger.info(f"Retrieved {len(tools)} tools from {config.name}")
        except Exception as ex:
            logger.warning(f"Failed to fetch tools from {tools_url}: {str(ex)}, using predefined tools")
            # Return predefined tools as fallback
            tools = self._get_predefined_tools(config.name)
        
        return tools
    
    def _get_predefined_tools(self, server_name: str) -> List[McpToolInfo]:
        """Get predefined tools for a server (fallback when live fetch fails)."""
        # These match the tools defined in both .NET and Python MCP servers
        predefined_tools = [
            ("get_all_employees", "Get a list of all employees in the company"),
            ("get_employee", "Get details of a specific employee by their ID"),
            ("search_employees", "Search for employees by name and/or department"),
            ("get_all_products", "Get a list of all products in the catalog"),
            ("get_product", "Get details of a specific product by its ID"),
            ("get_products_by_category", "Get all products in a specific category"),
            ("get_all_orders", "Get a list of all orders"),
            ("get_order", "Get details of a specific order by its ID"),
            ("create_order", "Create a new order for a customer"),
            ("get_inventory", "Get current inventory status for all products"),
            ("update_stock", "Update the stock quantity for a product"),
            ("check_api_health", "Check the health status of the REST API"),
        ]
        
        return [
            McpToolInfo(
                name=name,
                description=desc,
                server_name=server_name,
                full_name=f"{server_name}.{name}"
            )
            for name, desc in predefined_tools
        ]
    
    async def get_all_tools(self) -> List[McpToolInfo]:
        """Get all available tools from all configured MCP servers."""
        all_tools = []
        
        for server_name in self._servers:
            tools = await self.get_tools(server_name)
            all_tools.extend(tools)
        
        return all_tools
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> McpToolResult:
        """
        Call an MCP tool on a specific server.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Optional arguments for the tool
            
        Returns:
            Result from the tool call
        """
        start_time = datetime.utcnow()
        
        if server_name not in self._servers:
            return McpToolResult(
                success=False,
                error=f"MCP server '{server_name}' not found",
                server_name=server_name,
                tool_name=tool_name
            )
        
        config = self._servers[server_name]
        
        if not config.enabled:
            return McpToolResult(
                success=False,
                error=f"MCP server '{server_name}' is disabled",
                server_name=server_name,
                tool_name=tool_name
            )
        
        try:
            if config.transport == "sse":
                result = await self._call_tool_sse(config, tool_name, arguments)
            else:
                result = await self._call_tool_http_fallback(config, tool_name, arguments)
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result.duration_ms = duration
            result.server_name = server_name
            result.tool_name = tool_name
            
            return result
            
        except Exception as ex:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Failed to call tool {tool_name} on {server_name}: {str(ex)}")
            return McpToolResult(
                success=False,
                error=str(ex),
                server_name=server_name,
                tool_name=tool_name,
                duration_ms=duration
            )
    
    async def _call_tool_sse(
        self,
        config: McpServerConfig,
        tool_name: str,
        arguments: Optional[Dict[str, Any]]
    ) -> McpToolResult:
        """Call a tool via SSE transport (HTTP endpoint)."""
        base_url = config.endpoint.rstrip("/") if config.endpoint else ""
        if base_url.endswith("/sse"):
            base_url = base_url[:-4]
        call_url = f"{base_url}/tools/{tool_name}/call"
        
        try:
            response = await self._http_client.post(
                call_url,
                json={"arguments": arguments or {}},
                timeout=config.timeout_seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                return McpToolResult(
                    success=True,
                    result=json.dumps(data) if isinstance(data, dict) else str(data)
                )
            elif response.status_code == 404:
                # Tool not found, try HTTP fallback
                return await self._call_tool_http_fallback(config, tool_name, arguments)
            else:
                return McpToolResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except httpx.ConnectError:
            # MCP server not running, try HTTP fallback
            logger.info(f"MCP server at {base_url} not reachable, trying HTTP fallback")
            return await self._call_tool_http_fallback(config, tool_name, arguments)
        except Exception as ex:
            # Try HTTP fallback (direct REST API call)
            logger.info(f"MCP call failed ({ex}), trying HTTP fallback")
            return await self._call_tool_http_fallback(config, tool_name, arguments)
    
    async def _call_tool_http_fallback(
        self,
        config: McpServerConfig,
        tool_name: str,
        arguments: Optional[Dict[str, Any]]
    ) -> McpToolResult:
        """
        Fallback: Call tool directly via HTTP to SampleRestApi.
        This is used when the MCP server isn't running but SampleRestApi is.
        """
        # Map tool names to SampleRestApi endpoints
        sample_api_url = os.getenv("SAMPLE_REST_API_URL", "http://localhost:5001")
        
        endpoint_map = {
            "get_all_employees": ("GET", "/api/employees", []),
            "get_employee": ("GET", "/api/employees/{employee_id}", ["employee_id"]),
            "search_employees": ("GET", "/api/employees/search", []),
            "get_all_products": ("GET", "/api/products", []),
            "get_product": ("GET", "/api/products/{product_id}", ["product_id"]),
            "get_products_by_category": ("GET", "/api/products/category/{category}", ["category"]),
            "get_all_orders": ("GET", "/api/orders", []),
            "get_order": ("GET", "/api/orders/{order_id}", ["order_id"]),
            "create_order": ("POST", "/api/orders", []),
            "get_inventory": ("GET", "/api/inventory", []),
            "update_stock": ("PUT", "/api/inventory/{product_id}/stock", ["product_id"]),
            "check_api_health": ("GET", "/api/health", []),
        }
        
        if tool_name not in endpoint_map:
            return McpToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )
        
        method, path_template, path_params = endpoint_map[tool_name]
        args = arguments or {}
        
        # Replace path parameters
        path = path_template
        for param in path_params:
            if param in args:
                path = path.replace(f"{{{param}}}", str(args[param]))
        
        url = f"{sample_api_url}{path}"
        
        try:
            if method == "GET":
                # Add remaining args as query params (excluding path params)
                query_params = {k: v for k, v in args.items() if k not in path_params}
                response = await self._http_client.get(url, params=query_params if query_params else None)
            elif method == "POST":
                # Convert snake_case to camelCase for .NET API
                body = {}
                for k, v in args.items():
                    if k not in path_params:
                        # Convert customer_id to customerId, product_ids to productIds
                        camel_key = ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(k.split('_')))
                        body[camel_key] = v
                response = await self._http_client.post(url, json=body)
            elif method == "PUT":
                body = {k: v for k, v in args.items() if k not in path_params}
                # Convert snake_case to camelCase
                camel_body = {}
                for k, v in body.items():
                    camel_key = ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(k.split('_')))
                    camel_body[camel_key] = v
                response = await self._http_client.put(url, json=camel_body)
            else:
                return McpToolResult(success=False, error=f"Unsupported method: {method}")
            
            if response.status_code in (200, 201):
                return McpToolResult(
                    success=True,
                    result=response.text
                )
            else:
                return McpToolResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
                
        except httpx.ConnectError:
            return McpToolResult(
                success=False,
                error=f"Cannot connect to REST API at {sample_api_url}. Is it running?"
            )
        except Exception as ex:
            return McpToolResult(
                success=False,
                error=f"HTTP fallback failed: {str(ex)}"
            )
    
    async def test_connection(self, server_name: str) -> McpConnectionTestResult:
        """
        Test connection to an MCP server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            Connection test result
        """
        start_time = datetime.utcnow()
        
        if server_name not in self._servers:
            return McpConnectionTestResult(
                success=False,
                error=f"MCP server '{server_name}' not found",
                server_name=server_name
            )
        
        config = self._servers[server_name]
        
        try:
            # Try to get tools as a connection test
            tools = await self.get_tools(server_name)
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return McpConnectionTestResult(
                success=True,
                message=f"Connected to {server_name} successfully",
                server_name=server_name,
                tool_count=len(tools),
                duration_ms=duration
            )
        except Exception as ex:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return McpConnectionTestResult(
                success=False,
                error=str(ex),
                server_name=server_name,
                duration_ms=duration
            )
    
    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()
