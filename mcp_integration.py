"""
n8n MCP Integration for LiveKit Agents

Integrates Model Context Protocol (MCP) tools from n8n workflows into LiveKit voice agents.
This allows the AI agent to execute n8n workflows during phone conversations.

Features:
- Automatic tool discovery from n8n MCP endpoint
- Persistent SSE connection to n8n server
- Dynamic tool registration with LiveKit agents
- Error handling and logging

Author: Gagan Thakur/Sambhav Tech
"""

import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client
from livekit.agents.llm import function_tool

logger = logging.getLogger("mcp-integration")

# Global MCP integration instance to maintain connection
_mcp_integration: Optional['MCPToolsIntegration'] = None


class MCPToolsIntegration:
    """Integrates MCP server tools with LiveKit agents."""
    
    def __init__(self, mcp_url: str):
        """Initialize MCP integration.
        
        Args:
            mcp_url: The full MCP endpoint URL (e.g., https://n8n.tinysaas.fun/mcp/abc123)
        """
        self.mcp_url = mcp_url
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[ClientSession] = None
        self._client_context = None
        self._session_context = None
        
    async def connect(self):
        """Connect to the MCP server using SSE."""
        try:
            logger.info(f"Connecting to n8n MCP server at {self.mcp_url}...")
            
            # Use SSE client for n8n's HTTP-based MCP endpoint
            self._client_context = sse_client(self.mcp_url)
            read, write = await self._client_context.__aenter__()
            
            logger.info("Creating client session...")
            self._session_context = ClientSession(read, write)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session
            logger.info("Initializing session...")
            await self.session.initialize()
            logger.info(f"Successfully connected to n8n MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}", exc_info=True)
            raise
        
    async def fetch_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        try:
            if not self.session:
                await self.connect()
            
            # List available tools
            response = await self.session.list_tools()
            tools = response.tools if hasattr(response, 'tools') else (response.content or [])
            
            logger.info(f"Fetched {len(tools)} tools from MCP server")
            
            # Store tools for later use
            for tool in tools:
                self.tools[tool.name] = {
                    "name": tool.name,
                    "description": tool.description if hasattr(tool, 'description') else "",
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
                
            return [self.tools[tool.name] for tool in tools]
        except Exception as e:
            logger.error(f"Failed to fetch MCP tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            if not self.session:
                await self.connect()
                
            result = await self.session.call_tool(tool_name, arguments)
            logger.info(f"Called tool {tool_name} successfully")
            
            # Extract text content from result
            if result.content:
                return "\n".join([
                    item.text if hasattr(item, 'text') else str(item)
                    for item in result.content
                ])
            return str(result)
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return f"Error calling tool: {str(e)}"
    
    # Regex for validating tool/parameter names: only alphanumeric and underscores
    _SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    # Map JSON schema types to Python types
    _TYPE_MAP: Dict[str, type] = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    def _validate_identifier(self, name: str) -> str:
        """Validate that a name is a safe Python identifier.

        Raises ValueError if the name contains characters that could
        enable code injection.
        """
        if not self._SAFE_IDENTIFIER_RE.match(name):
            raise ValueError(f"Unsafe identifier rejected: {name!r}")
        return name

    def create_livekit_tool(self, tool_def: Dict[str, Any]) -> Callable:
        """Create a LiveKit function tool from an MCP tool definition.

        Uses a closure-based factory instead of ``exec()`` to avoid
        code-injection risks from untrusted tool/parameter names.

        Args:
            tool_def: MCP tool definition

        Returns:
            LiveKit function tool
        """
        tool_name = self._validate_identifier(tool_def["name"])
        tool_description = tool_def.get("description", "")
        input_schema = tool_def.get("inputSchema", {})

        # Extract and validate properties from the input schema
        properties = input_schema.get("properties", {})
        param_names: List[str] = []

        annotations: Dict[str, type] = {}
        for param_name, param_def in properties.items():
            param_name = self._validate_identifier(param_name)
            param_type = param_def.get("type", "string")
            py_type = self._TYPE_MAP.get(param_type, str)
            annotations[param_name] = py_type
            param_names.append(param_name)

        # Capture references for the closure
        call_impl = self.call_tool
        captured_tool_name = tool_name
        captured_param_names = list(param_names)

        async def _mcp_tool_wrapper(**kwargs: Any) -> str:
            args = {k: v for k, v in kwargs.items() if k in captured_param_names and v is not None}
            return await call_impl(captured_tool_name, args)

        # Set metadata so LiveKit/LLM can discover the function correctly
        _mcp_tool_wrapper.__name__ = tool_name
        _mcp_tool_wrapper.__qualname__ = tool_name
        _mcp_tool_wrapper.__doc__ = tool_description
        _mcp_tool_wrapper.__annotations__ = {**annotations, "return": str}

        # Decorate with function_tool
        return function_tool(_mcp_tool_wrapper)
    
    async def get_livekit_tools(self) -> List[Callable]:
        """Get all MCP tools as LiveKit function tools.
        
        Returns:
            List of LiveKit function tools
        """
        tools_list = await self.fetch_tools()
        livekit_tools = []
        
        for tool_def in tools_list:
            try:
                livekit_tool = self.create_livekit_tool(tool_def)
                livekit_tools.append(livekit_tool)
                logger.info(f"Created LiveKit tool: {tool_def['name']}")
            except Exception as e:
                logger.error(f"Failed to create tool {tool_def.get('name')}: {e}")
        
        return livekit_tools
    
    async def close(self):
        """Close the MCP session."""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._client_context:
                await self._client_context.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error closing MCP connection: {e}")


async def load_mcp_tools(mcp_url: str = None) -> List[Callable]:
    """Load MCP tools from the configured n8n server.
    
    This maintains a persistent connection to the MCP server.
    
    Args:
        mcp_url: Optional full MCP endpoint URL. If not provided, uses N8N_MCP_URL env var.
                 Should be the full URL (e.g., "https://n8n.tinysaas.fun/mcp/abc123")
        
    Returns:
        List of LiveKit function tools
    """
    global _mcp_integration
    
    # Get MCP URL from parameter or environment
    url = mcp_url or os.getenv("N8N_MCP_URL")
    
    if not url:
        logger.warning("No MCP URL configured (set N8N_MCP_URL or config), skipping MCP tools")
        return []
    
    # Check if we need to reconnect (different URL)
    if _mcp_integration is not None and _mcp_integration.mcp_url != url:
        logger.info(f"MCP URL changed from {_mcp_integration.mcp_url} to {url}, reconnecting...")
        await _mcp_integration.close()
        _mcp_integration = None

    # Create or reuse the integration instance
    if _mcp_integration is None:
        _mcp_integration = MCPToolsIntegration(url)
    
    tools = await _mcp_integration.get_livekit_tools()
    return tools


def get_mcp_integration() -> Optional[MCPToolsIntegration]:
    """Get the global MCP integration instance."""
    return _mcp_integration
