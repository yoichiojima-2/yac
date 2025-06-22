"""Bridge between MCP tools and LangChain tools."""

from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool
from pydantic import Field, create_model
from ..mcp.client import MCPClient, MCPToolCall


def create_mcp_tool_function(tool_name: str, server_name: str, mcp_client: MCPClient):
    """Create an async function that executes an MCP tool."""

    async def mcp_tool_func(**kwargs: Any) -> str:
        try:
            # Create MCP tool call
            tool_call = MCPToolCall(
                server_name=server_name, name=tool_name, arguments=kwargs
            )

            # Execute the tool
            result = await mcp_client.call_tool(tool_call)

            if result.is_error:
                return f"Error executing {tool_name}: {result.content}"

            return str(result.content)

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    return mcp_tool_func


def json_schema_to_pydantic_fields(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON schema to Pydantic field definitions."""
    fields = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        prop_desc = prop_schema.get("description", "")

        # Map JSON schema types to Python types
        python_type: Any
        if prop_type == "string":
            python_type = str
        elif prop_type == "integer":
            python_type = int
        elif prop_type == "number":
            python_type = float
        elif prop_type == "boolean":
            python_type = bool
        elif prop_type == "array":
            python_type = List[str]  # Simplified for now
        else:
            python_type = Any

        # Create field with proper annotation
        if prop_name in required:
            fields[prop_name] = (python_type, Field(..., description=prop_desc))
        else:
            fields[prop_name] = (python_type, Field(None, description=prop_desc))

    return fields


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
                input_schema = tool_data.get("inputSchema", {})

                # Create tool function
                tool_func = create_mcp_tool_function(tool_name, server, self.mcp_client)

                # Convert input schema to Pydantic fields
                try:
                    fields = json_schema_to_pydantic_fields(input_schema)

                    # Create a Pydantic model for the arguments
                    if fields:
                        args_model = create_model(f"{tool_name}Args", **fields)
                    else:
                        # Tool has no arguments
                        args_model = None

                    # Create a default args schema for tools with no arguments
                    if not args_model:
                        args_model = create_model(f"{tool_name}Args")

                    # Create LangChain StructuredTool
                    langchain_tool = StructuredTool(
                        name=tool_name,
                        description=tool_description,
                        args_schema=args_model,
                        func=tool_func,
                        coroutine=tool_func,
                    )

                    tools.append(langchain_tool)

                except Exception as e:
                    print(f"Warning: Failed to create tool {tool_name}: {e}")
                    continue

        return tools

    async def bind_tools_to_llm(self, llm, server_name: Optional[str] = None):
        """Bind MCP tools to a LangChain LLM."""
        tools = await self.get_langchain_tools(server_name)

        if not tools:
            return llm

        # Bind tools to the LLM
        return llm.bind_tools(tools)
