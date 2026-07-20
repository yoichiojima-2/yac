"""Integration tests for MCP server connections and functionality."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from yac.mcp.client import MCPClient
from yac.mcp.config import MCPServerConfig, MCPTransport
from yac.mcp.defaults import get_default_mcp_servers
from yac.mcp.simple_session import SimpleClientSession

INIT_RESPONSE = b'{"jsonrpc": "2.0", "id": 2, "result": {"capabilities": {}}}\n'
TOOLS_RESPONSE = (
    b'{"jsonrpc": "2.0", "id": 3, "result": {"tools": '
    b'[{"name": "demo_tool", "description": "A demo tool", "inputSchema": {}}]}}\n'
)


def make_mock_process(readline_side_effect):
    """Build a mock subprocess that speaks newline-delimited JSON-RPC."""
    process = Mock()
    process.stdin = Mock()
    process.stdin.write = Mock()
    process.stdin.drain = AsyncMock()
    process.stdout = Mock()
    process.stdout.readline = AsyncMock(side_effect=readline_side_effect)
    process.stdout.read = AsyncMock(return_value=b"")
    return process


class TestMCPIntegration:
    """Test MCP server connections and tool execution."""

    @pytest.mark.asyncio
    async def test_server_connection_and_tool_caching(self):
        """A successful handshake registers the session and caches its tools."""
        client = MCPClient()
        config = MCPServerConfig(
            name="test_filesystem",
            transport=MCPTransport.STDIO,
            command=["fake-server"],
        )

        mock_process = make_mock_process([INIT_RESPONSE, TOOLS_RESPONSE])
        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            success = await client.add_server(config)

        assert success
        assert "test_filesystem" in client.sessions
        tools = await client.list_tools("test_filesystem")
        assert [t["name"] for t in tools["test_filesystem"]] == ["demo_tool"]

    @pytest.mark.asyncio
    async def test_server_connection_timeout(self):
        """Server connections that never respond fail gracefully."""
        client = MCPClient()
        config = MCPServerConfig(
            name="test_timeout",
            transport=MCPTransport.STDIO,
            command=["fake-server"],
        )

        mock_process = make_mock_process(asyncio.TimeoutError())
        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            success = await client.add_server(config)

        assert not success
        assert "test_timeout" not in client.sessions

    @pytest.mark.asyncio
    async def test_call_tool_propagates_session_error(self):
        """Errors raised by the session surface to the caller."""
        client = MCPClient()

        mock_session = Mock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("File not found"))
        client.sessions["test_server"] = mock_session

        with pytest.raises(Exception, match="File not found"):
            await client.call_tool(
                "test_server", "read_file", {"path": "nonexistent.txt"}
            )

    @pytest.mark.asyncio
    async def test_default_servers_configuration(self):
        """Default server configurations are valid."""
        servers = get_default_mcp_servers()

        # Check that all expected servers are present
        expected_servers = ["filesystem", "fetch", "git", "bash", "puppeteer"]
        for server_name in expected_servers:
            assert server_name in servers
            config = servers[server_name]
            assert config.name == server_name
            assert config.transport == MCPTransport.STDIO
            assert config.command is not None
            assert len(config.command) > 0

    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Responses split across the readline buffer are reassembled."""
        large_data = "x" * 10000
        payload = (
            json.dumps(
                {"jsonrpc": "2.0", "id": 2, "result": {"data": large_data}}
            ).encode()
            + b"\n"
        )

        # First chunk arrives via readline, the rest via read()
        first_chunk, rest = payload[:100], payload[100:]

        mock_process = make_mock_process([first_chunk])
        mock_process.stdout.read = AsyncMock(side_effect=[rest])

        session = SimpleClientSession(mock_process)
        response = await session._send_request("tools/list")

        assert response["result"]["data"] == large_data

    @pytest.mark.asyncio
    async def test_concurrent_server_connections(self):
        """Multiple servers can be connected concurrently."""
        client = MCPClient()

        configs = [
            MCPServerConfig(
                name=f"test_server_{i}",
                transport=MCPTransport.STDIO,
                command=["fake-server"],
            )
            for i in range(3)
        ]

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(
                side_effect=lambda *args, **kwargs: make_mock_process(
                    [INIT_RESPONSE, TOOLS_RESPONSE]
                )
            ),
        ):
            results = await asyncio.gather(
                *(client.add_server(config) for config in configs),
                return_exceptions=True,
            )

        assert all(result is True for result in results)
        assert len(client.sessions) == 3

    def test_server_config_validation(self):
        """Server configuration validation."""
        # Valid config
        config = MCPServerConfig(
            name="test", transport=MCPTransport.STDIO, command=["echo", "test"]
        )
        assert config.name == "test"
        assert config.transport == MCPTransport.STDIO

        # STDIO without a command is invalid
        with pytest.raises(ValueError):
            MCPServerConfig(name="test", transport=MCPTransport.STDIO)

        # HTTP/SSE without a URL is invalid
        with pytest.raises(ValueError):
            MCPServerConfig(name="test", transport=MCPTransport.HTTP)

        # Unknown transport values are rejected by the enum
        with pytest.raises(ValueError):
            MCPTransport("invalid")

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Graceful shutdown closes all sessions and clears state."""
        client = MCPClient()

        mock_session = Mock()
        mock_session.close = AsyncMock()
        client.sessions["test_server"] = mock_session
        client.tools_cache["test_server"] = []

        await client.close_all()

        mock_session.close.assert_awaited_once()
        assert len(client.sessions) == 0
        assert len(client.tools_cache) == 0


class TestErrorScenarios:
    """Test various error scenarios and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_server_error_response(self):
        """JSON-RPC error responses raise an exception."""
        error_response = (
            b'{"jsonrpc": "2.0", "id": 2, '
            b'"error": {"code": -32601, "message": "Method not found"}}\n'
        )
        mock_process = make_mock_process([error_response])
        session = SimpleClientSession(mock_process)

        with pytest.raises(Exception, match="Server error"):
            await session._send_request("test_method")

    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Empty responses from servers raise an exception."""
        mock_process = make_mock_process([b""])
        session = SimpleClientSession(mock_process)

        with pytest.raises(Exception, match="No response from server"):
            await session._send_request("test_method")

    @pytest.mark.asyncio
    async def test_process_crash_handling(self):
        """A server process that exits immediately fails gracefully."""
        client = MCPClient()

        config = MCPServerConfig(
            name="crash_test",
            transport=MCPTransport.STDIO,
            command=["false"],  # Command that exits with error
        )

        success = await client.add_server(config)
        assert not success  # Should fail gracefully

    @pytest.mark.asyncio
    async def test_mock_filesystem_server(self):
        """Integration with a real subprocess speaking the MCP protocol."""
        client = MCPClient()

        # Use Python to run our mock server
        mock_server_path = Path(__file__).parent / "mocks" / "mock_mcp_server.py"
        config = MCPServerConfig(
            name="mock_filesystem",
            transport=MCPTransport.STDIO,
            command=["python", str(mock_server_path), "filesystem"],
        )

        try:
            success = await client.add_server(config)
            assert success
            assert "mock_filesystem" in client.sessions

            # Test tool listing
            tools = await client.list_tools("mock_filesystem")
            assert "mock_filesystem" in tools
            assert len(tools["mock_filesystem"]) > 0

            # Verify expected tools are present
            tool_names = [tool["name"] for tool in tools["mock_filesystem"]]
            expected_tools = [
                "read_file",
                "write_file",
                "list_directory",
                "search_files",
            ]
            for expected_tool in expected_tools:
                assert expected_tool in tool_names
        finally:
            await client.close_all()
