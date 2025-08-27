"""Bridge between MCP tools and LangChain tools."""

from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool
from pydantic import Field, create_model
from .client import MCPClient


def create_mcp_tool_function(tool_name: str, server_name: str, mcp_client: MCPClient):
    """Create an async function that executes an MCP tool."""

    async def mcp_tool_func(**kwargs: Any) -> str:
        try:
            # Execute the tool
            result = await mcp_client.call_tool(server_name, tool_name, kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    return mcp_tool_func


class MCPLangChainBridge:
    """Bridge that converts MCP tools to LangChain tools."""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def get_langchain_tools(
        self, server_name: Optional[str] = None
    ) -> List[StructuredTool]:
        """Convert MCP tools to LangChain tools."""
        tools = []

        # Get tools from MCP servers
        mcp_tools = await self.mcp_client.list_tools(server_name)

        for server, server_tools in mcp_tools.items():
            for tool_data in server_tools:
                # Extract tool information
                tool_name = tool_data.get("name", "unknown")
                tool_description = tool_data.get(
                    "description", "No description available"
                )

                # Create tool function
                tool_func = create_mcp_tool_function(tool_name, server, self.mcp_client)

                # Create LangChain tool
                langchain_tool = StructuredTool(
                    name=tool_name,
                    description=tool_description,
                    func=tool_func,
                )
                tools.append(langchain_tool)

        return tools

    async def bind_tools_to_llm(self, llm):
        """Bind MCP tools to a LangChain LLM."""
        tools = await self.get_langchain_tools()
        if tools:
            return llm.bind_tools(tools)
        return llm