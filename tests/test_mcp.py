"""Tests for MCP functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from yet_claude_code.mcp.config import (
    MCPServerConfig,
    MCPTransport,
    MCPToolCall,
    MCPToolResult,
)
from yet_claude_code.mcp.client import MCPClient
from yet_claude_code.mcp.defaults import (
    get_default_mcp_servers,
    get_optional_mcp_servers,
)
from yet_claude_code.mcp.langchain_bridge import (
    MCPLangChainBridge,
    json_schema_to_pydantic_fields,
)


class TestMCPServerConfig:
    """Test MCP server configuration."""

    def test_stdio_config_creation(self):
        config = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command=["python", "-m", "test_server"],
        )
        assert config.name == "test-server"
        assert config.transport == MCPTransport.STDIO
        assert config.command == ["python", "-m", "test_server"]
        assert config.url is None

    def test_http_config_creation(self):
        config = MCPServerConfig(
            name="test-server", transport=MCPTransport.HTTP, url="http://localhost:8080"
        )
        assert config.name == "test-server"
        assert config.transport == MCPTransport.HTTP
        assert config.url == "http://localhost:8080"
        assert config.command is None

    def test_config_with_env_vars(self):
        config = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command=["test"],
            env={"API_KEY": "secret"},
        )
        assert config.env == {"API_KEY": "secret"}


class TestMCPToolCall:
    """Test MCP tool call data structures."""

    def test_tool_call_creation(self):
        call = MCPToolCall(
            server_name="test-server", name="test_tool", arguments={"param1": "value1"}
        )
        assert call.server_name == "test-server"
        assert call.name == "test_tool"
        assert call.arguments == {"param1": "value1"}


class TestMCPToolResult:
    """Test MCP tool result data structures."""

    def test_successful_result(self):
        result = MCPToolResult(content="success", is_error=False)
        assert result.content == "success"
        assert not result.is_error

    def test_error_result(self):
        result = MCPToolResult(content="error message", is_error=True)
        assert result.content == "error message"
        assert result.is_error


class TestMCPClient:
    """Test MCP client functionality."""

    def test_client_initialization(self):
        client = MCPClient()
        assert client.servers == {}
        assert client.sessions == {}
        assert client.processes == {}

    @pytest.mark.asyncio
    async def test_add_invalid_server(self):
        client = MCPClient()
        config = MCPServerConfig(
            name="invalid-server",
            transport=MCPTransport.STDIO,
            command=["nonexistent-command"],
        )

        # Should return False for invalid servers
        result = await client.add_server(config)
        assert not result
        assert (
            "invalid-server" in client.servers
        )  # Config is stored even if connection fails

    @pytest.mark.asyncio
    async def test_call_tool_no_server(self):
        client = MCPClient()
        tool_call = MCPToolCall(
            server_name="nonexistent", name="test_tool", arguments={}
        )

        result = await client.call_tool(tool_call)
        assert result.is_error
        assert "not connected" in result.content

    @pytest.mark.asyncio
    async def test_remove_nonexistent_server(self):
        client = MCPClient()
        result = await client.remove_server("nonexistent")
        assert not result

    @pytest.mark.asyncio
    async def test_list_tools_empty(self):
        client = MCPClient()
        tools = await client.list_tools()
        assert tools == {}


class TestMCPDefaults:
    """Test default MCP server configurations."""

    def test_get_default_servers(self):
        servers = get_default_mcp_servers()
        assert "filesystem" in servers
        assert "fetch" in servers
        assert "puppeteer" in servers

        # Check filesystem server config
        fs_server = servers["filesystem"]
        assert fs_server.name == "filesystem"
        assert fs_server.transport == MCPTransport.STDIO
        assert "npx" in fs_server.command[0]

    @patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"})
    def test_get_default_servers_with_brave(self):
        servers = get_default_mcp_servers()
        assert "brave-search" in servers
        brave_server = servers["brave-search"]
        assert brave_server.env == {"BRAVE_API_KEY": "test-key"}

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    def test_get_optional_servers_with_github(self):
        servers = get_optional_mcp_servers()
        assert "github" in servers
        github_server = servers["github"]
        assert github_server.env == {"GITHUB_TOKEN": "test-token"}

    def test_get_optional_servers_always_available(self):
        servers = get_optional_mcp_servers()
        # These should always be present regardless of env vars
        assert "sqlite" in servers
        assert "memory" in servers
        assert "desktop-commander" in servers


class TestMCPLangChainBridge:
    """Test MCP LangChain bridge functionality."""

    def test_json_schema_to_pydantic_simple(self):
        schema = {
            "properties": {
                "name": {"type": "string", "description": "A name"},
                "age": {"type": "integer", "description": "An age"},
            },
            "required": ["name"],
        }

        fields = json_schema_to_pydantic_fields(schema)
        assert len(fields) == 2
        assert "name" in fields
        assert "age" in fields

        # Required field should not have None default
        name_field = fields["name"]
        assert name_field[0] is str

        # Optional field should have None default
        age_field = fields["age"]
        assert age_field[0] is int

    def test_json_schema_to_pydantic_types(self):
        schema = {
            "properties": {
                "text": {"type": "string"},
                "count": {"type": "integer"},
                "price": {"type": "number"},
                "active": {"type": "boolean"},
                "items": {"type": "array"},
            }
        }

        fields = json_schema_to_pydantic_fields(schema)
        assert fields["text"][0] is str
        assert fields["count"][0] is int
        assert fields["price"][0] is float
        assert fields["active"][0] is bool
        from typing import List

        assert fields["items"][0] == List[str]  # Simplified to List[str]

    @pytest.mark.asyncio
    async def test_bridge_initialization(self):
        mock_client = Mock(spec=MCPClient)
        bridge = MCPLangChainBridge(mock_client)
        assert bridge.mcp_client == mock_client

    @pytest.mark.asyncio
    async def test_get_langchain_tools_empty(self):
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value={})

        bridge = MCPLangChainBridge(mock_client)
        tools = await bridge.get_langchain_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_get_langchain_tools_with_tools(self):
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(
            return_value={
                "test-server": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "properties": {
                                "param": {
                                    "type": "string",
                                    "description": "A parameter",
                                }
                            },
                            "required": ["param"],
                        },
                    }
                ]
            }
        )

        bridge = MCPLangChainBridge(mock_client)
        tools = await bridge.get_langchain_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_bind_tools_to_llm_no_tools(self):
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value={})
        mock_llm = Mock()

        bridge = MCPLangChainBridge(mock_client)
        result = await bridge.bind_tools_to_llm(mock_llm)

        # Should return original LLM if no tools
        assert result == mock_llm

    @pytest.mark.asyncio
    async def test_bind_tools_to_llm_with_tools(self):
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(
            return_value={
                "test-server": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {},
                    }
                ]
            }
        )
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value="bound_llm")

        bridge = MCPLangChainBridge(mock_client)
        result = await bridge.bind_tools_to_llm(mock_llm)

        # Should call bind_tools on LLM
        mock_llm.bind_tools.assert_called_once()
        assert result == "bound_llm"


if __name__ == "__main__":
    pytest.main([__file__])
