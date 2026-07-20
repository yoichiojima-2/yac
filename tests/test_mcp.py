"""Tests for MCP functionality."""

from typing import Optional

import pytest
from unittest.mock import Mock, patch, AsyncMock
from yac.mcp.config import (
    MCPServerConfig,
    MCPTransport,
    MCPToolCall,
    MCPToolResult,
)
from yac.mcp.client import MCPClient
from yac.mcp.defaults import (
    get_default_mcp_servers,
    get_optional_mcp_servers,
)
from yac.mcp.langchain_bridge import MCPLangChainBridge


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

    def test_stdio_config_requires_command(self):
        with pytest.raises(ValueError, match="requires command"):
            MCPServerConfig(name="test-server", transport=MCPTransport.STDIO)

    def test_http_config_requires_url(self):
        with pytest.raises(ValueError, match="requires url"):
            MCPServerConfig(name="test-server", transport=MCPTransport.HTTP)

    def test_invalid_transport_value(self):
        with pytest.raises(ValueError):
            MCPTransport("invalid")


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
        assert client.sessions == {}
        assert client.tools_cache == {}

    @pytest.mark.asyncio
    async def test_add_invalid_server(self):
        client = MCPClient()
        config = MCPServerConfig(
            name="invalid-server",
            transport=MCPTransport.STDIO,
            command=["nonexistent-command-xyz-12345"],
        )

        # Should return False for servers that fail to connect
        result = await client.add_server(config)
        assert not result
        assert "invalid-server" not in client.sessions

    @pytest.mark.asyncio
    async def test_call_tool_no_server(self):
        client = MCPClient()

        with pytest.raises(ValueError, match="not connected"):
            await client.call_tool("nonexistent", "test_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_delegates_to_session(self):
        client = MCPClient()
        mock_session = Mock()
        mock_session.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "ok"}]}
        )
        client.sessions["test-server"] = mock_session

        result = await client.call_tool("test-server", "test_tool", {"a": 1})

        mock_session.call_tool.assert_awaited_once_with("test_tool", {"a": 1})
        assert result == {"content": [{"type": "text", "text": "ok"}]}

    @pytest.mark.asyncio
    async def test_remove_server(self):
        client = MCPClient()
        mock_session = Mock()
        mock_session.close = AsyncMock()
        client.sessions["test-server"] = mock_session
        client.tools_cache["test-server"] = [{"name": "test_tool"}]

        result = await client.remove_server("test-server")
        assert result
        assert "test-server" not in client.sessions
        assert "test-server" not in client.tools_cache
        mock_session.close.assert_awaited_once()

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

    @pytest.mark.asyncio
    async def test_list_tools_filters_by_server(self):
        client = MCPClient()
        client.tools_cache = {
            "server-a": [{"name": "tool_a"}],
            "server-b": [{"name": "tool_b"}],
        }

        assert await client.list_tools("server-a") == {"server-a": [{"name": "tool_a"}]}
        assert await client.list_tools("unknown") == {}
        assert await client.list_tools() == client.tools_cache

    @pytest.mark.asyncio
    async def test_get_all_tools_annotates_server_name(self):
        client = MCPClient()
        client.tools_cache = {
            "server-a": [{"name": "tool_a"}],
            "server-b": [{"name": "tool_b"}],
        }

        all_tools = await client.get_all_tools()
        assert {(t["name"], t["server_name"]) for t in all_tools} == {
            ("tool_a", "server-a"),
            ("tool_b", "server-b"),
        }

    @pytest.mark.asyncio
    async def test_close_all(self):
        client = MCPClient()
        mock_session = Mock()
        mock_session.close = AsyncMock()
        client.sessions["test-server"] = mock_session
        client.tools_cache["test-server"] = []

        await client.close_all()

        mock_session.close.assert_awaited_once()
        assert client.sessions == {}
        assert client.tools_cache == {}


class TestMCPDefaults:
    """Test default MCP server configurations."""

    def test_get_default_servers(self):
        servers = get_default_mcp_servers()
        for name in ["filesystem", "fetch", "git", "bash", "puppeteer"]:
            assert name in servers

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
        assert "param" in tool.args_schema.model_fields

    def test_args_schema_required_vs_optional(self):
        bridge = MCPLangChainBridge(Mock(spec=MCPClient))
        schema = bridge._create_args_schema(
            "test_tool",
            {
                "inputSchema": {
                    "properties": {
                        "name": {"type": "string", "description": "A name"},
                        "age": {"type": "integer", "description": "An age"},
                    },
                    "required": ["name"],
                }
            },
        )

        fields = schema.model_fields
        assert set(fields) == {"name", "age"}

        # Required field: bare type, no default
        assert fields["name"].annotation is str
        assert fields["name"].is_required()

        # Optional field: Optional type with None default
        assert fields["age"].annotation == Optional[int]
        assert not fields["age"].is_required()
        assert fields["age"].default is None

    def test_args_schema_type_mapping(self):
        bridge = MCPLangChainBridge(Mock(spec=MCPClient))
        properties = {
            "text": {"type": "string"},
            "count": {"type": "integer"},
            "price": {"type": "number"},
            "active": {"type": "boolean"},
            "items": {"type": "array"},
            "meta": {"type": "object"},
        }
        schema = bridge._create_args_schema(
            "test_tool",
            {"inputSchema": {"properties": properties, "required": list(properties)}},
        )

        fields = schema.model_fields
        assert fields["text"].annotation is str
        assert fields["count"].annotation is int
        assert fields["price"].annotation is float
        assert fields["active"].annotation is bool
        assert fields["items"].annotation is list
        assert fields["meta"].annotation is dict

    def test_args_schema_without_properties_gets_fallback(self):
        bridge = MCPLangChainBridge(Mock(spec=MCPClient))
        schema = bridge._create_args_schema("test_tool", {"inputSchema": {}})

        fields = schema.model_fields
        assert set(fields) == {"args"}
        assert not fields["args"].is_required()

    @pytest.mark.asyncio
    async def test_tool_ainvoke_returns_mcp_result(self):
        """Tools must be built as coroutines: ainvoke returns the MCP result,
        not an un-awaited coroutine object."""
        client = Mock(spec=MCPClient)
        client.list_tools = AsyncMock(
            return_value={
                "srv": [
                    {
                        "name": "echo",
                        "description": "echo back",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    }
                ]
            }
        )
        client.call_tool = AsyncMock(return_value="echoed: hi")

        bridge = MCPLangChainBridge(client)
        tools = await bridge.get_langchain_tools()
        assert len(tools) == 1

        result = await tools[0].ainvoke({"text": "hi"})
        assert result == "echoed: hi"
        client.call_tool.assert_awaited_once_with("srv", "echo", {"text": "hi"})


if __name__ == "__main__":
    pytest.main([__file__])
