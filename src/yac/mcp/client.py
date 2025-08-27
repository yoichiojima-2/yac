"""MCP Client for managing connections to MCP servers."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from .config import MCPServerConfig, MCPTransport
from .simple_session import SimpleSession

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for managing MCP server connections."""

    def __init__(self):
        self.sessions: Dict[str, SimpleSession] = {}
        self.tools_cache: Dict[str, List[Dict[str, Any]]] = {}

    async def add_server(self, config: MCPServerConfig) -> bool:
        """Add and connect to an MCP server."""
        try:
            session = SimpleSession()
            success = await session.connect(config)
            
            if success:
                self.sessions[config.name] = session
                # Cache tools for this server
                await self._cache_server_tools(config.name)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add MCP server {config.name}: {e}")
            return False

    async def remove_server(self, name: str) -> bool:
        """Remove and disconnect from an MCP server."""
        if name in self.sessions:
            try:
                await self.sessions[name].close()
                del self.sessions[name]
                if name in self.tools_cache:
                    del self.tools_cache[name]
                return True
            except Exception as e:
                logger.error(f"Failed to remove MCP server {name}: {e}")
        return False

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a specific server."""
        if server_name not in self.sessions:
            raise ValueError(f"Server {server_name} not connected")
        
        session = self.sessions[server_name]
        return await session.call_tool(tool_name, arguments)

    async def list_tools(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """List available tools from servers."""
        if server_name:
            if server_name in self.tools_cache:
                return {server_name: self.tools_cache[server_name]}
            return {}
        
        return self.tools_cache.copy()

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected servers."""
        all_tools = []
        for server_name, tools in self.tools_cache.items():
            for tool in tools:
                tool_with_server = tool.copy()
                tool_with_server['server_name'] = server_name
                all_tools.append(tool_with_server)
        return all_tools

    async def _cache_server_tools(self, server_name: str):
        """Cache tools for a specific server."""
        try:
            session = self.sessions[server_name]
            tools = await session.list_tools()
            self.tools_cache[server_name] = tools
        except Exception as e:
            logger.error(f"Failed to cache tools for {server_name}: {e}")
            self.tools_cache[server_name] = []

    async def close_all(self):
        """Close all server connections."""
        for session in self.sessions.values():
            try:
                await session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
        self.sessions.clear()
        self.tools_cache.clear()