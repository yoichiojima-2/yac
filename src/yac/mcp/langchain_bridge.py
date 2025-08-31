from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool
from pydantic import create_model, BaseModel, Field
from .client import MCPClient


class MCPLangChainBridge:
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def get_langchain_tools(
        self, server_name: Optional[str] = None
    ) -> List[StructuredTool]:
        tools = []
        mcp_tools = await self.mcp_client.list_tools(server_name)

        for server, server_tools in mcp_tools.items():
            for tool_data in server_tools:
                tool_name = tool_data.get("name", "unknown")
                tool_description = tool_data.get(
                    "description", "No description available"
                )

                def make_tool_func(srv, name):
                    async def tool_func(**kwargs: Any) -> str:
                        try:
                            result = await self.mcp_client.call_tool(srv, name, kwargs)
                            return str(result)
                        except Exception as e:
                            return f"Error: {e}"

                    return tool_func

                # Create proper schema from MCP tool inputSchema
                args_schema = self._create_args_schema(tool_name, tool_data)

                tools.append(
                    StructuredTool(
                        name=tool_name,
                        description=tool_description,
                        func=make_tool_func(server, tool_name),
                        args_schema=args_schema,
                    )
                )

        return tools

    def _create_args_schema(
        self, tool_name: str, tool_data: Dict[str, Any]
    ) -> type[BaseModel]:
        """Create Pydantic schema from MCP tool inputSchema."""
        input_schema = tool_data.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        # Create fields dict for create_model
        fields = {}

        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "string")
            prop_description = prop_schema.get("description", "")

            # Map JSON schema types to Python types
            python_type = str  # default
            if prop_type == "string":
                python_type = str
            elif prop_type == "integer":
                python_type = int
            elif prop_type == "number":
                python_type = float
            elif prop_type == "boolean":
                python_type = bool
            elif prop_type == "array":
                python_type = list
            elif prop_type == "object":
                python_type = dict

            # Make optional if not in required list
            if prop_name not in required:
                python_type = Optional[python_type]
                fields[prop_name] = (
                    python_type,
                    Field(default=None, description=prop_description),
                )
            else:
                fields[prop_name] = (python_type, Field(description=prop_description))

        # If no properties defined, create a generic schema
        if not fields:
            fields["args"] = (
                Optional[dict],
                Field(default={}, description="Tool arguments"),
            )

        return create_model(
            f"{tool_name.replace('-', '_').replace(' ', '_')}_Args", **fields
        )
