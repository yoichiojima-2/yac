"""Integration tests for MCP server connections and functionality."""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from yet_claude_code.mcp.client import MCPClient
from yet_claude_code.mcp.config import MCPServerConfig, MCPTransport
from yet_claude_code.mcp.defaults import get_default_mcp_servers

# Add the mocks directory to the path
sys.path.insert(0, str(Path(__file__).parent / "mocks"))


class TestMCPIntegration:
    """Test MCP server connections and tool execution."""

    @pytest.mark.asyncio
    async def test_filesystem_server_connection(self):
        """Test that filesystem MCP server connects successfully."""
        client = MCPClient()
        config = MCPServerConfig(
            name="test_filesystem",
            transport=MCPTransport.STDIO,
            command=[
                "echo",
                '{"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}',
            ],
        )

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock successful process
            mock_process = Mock()
            mock_process.stdin = Mock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline = AsyncMock(
                return_value=b'{"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}\n'
            )
            mock_subprocess.return_value = mock_process

            success = await client.add_server(config)
            assert success
            assert "test_filesystem" in client.sessions

    @pytest.mark.asyncio
    async def test_server_connection_timeout(self):
        """Test that server connections timeout gracefully."""
        client = MCPClient()
        config = MCPServerConfig(
            name="test_timeout",
            transport=MCPTransport.STDIO,
            command=["sleep", "10"],  # Will timeout
        )

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock hanging process
            mock_process = Mock()
            mock_process.stdin = Mock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_subprocess.return_value = mock_process

            success = await client.add_server(config)
            assert not success

    @pytest.mark.asyncio
    async def test_tool_execution_with_error_recovery(self):
        """Test tool execution with intelligent error recovery."""
        client = MCPClient()

        # Mock session with failing tool
        mock_session = Mock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("File not found"))
        client.sessions["test_server"] = mock_session

        from yet_claude_code.mcp.config import MCPToolCall

        tool_call = MCPToolCall(
            server_name="test_server",
            name="read_file",
            arguments={"path": "nonexistent.txt"},
        )

        result = await client.call_tool(tool_call)
        assert result.is_error
        assert "File not found" in result.content

    @pytest.mark.asyncio
    async def test_default_servers_configuration(self):
        """Test that default server configurations are valid."""
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
        """Test handling of large JSON responses."""
        client = MCPClient()

        # Create a large JSON response (>8KB)
        large_data = "x" * 10000
        large_response = (
            f'{{"jsonrpc": "2.0", "id": 1, "result": {{"data": "{large_data}"}}}}\n'
        )

        config = MCPServerConfig(
            name="test_large",
            transport=MCPTransport.STDIO,
            command=["echo", large_response],
        )

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.stdin = Mock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline = AsyncMock(
                return_value=large_response.encode()
            )
            mock_subprocess.return_value = mock_process

            success = await client.add_server(config)
            assert success

    @pytest.mark.asyncio
    async def test_concurrent_server_connections(self):
        """Test connecting to multiple servers concurrently."""
        client = MCPClient()

        # Create multiple server configs
        configs = []
        for i in range(3):
            configs.append(
                MCPServerConfig(
                    name=f"test_server_{i}",
                    transport=MCPTransport.STDIO,
                    command=[
                        "echo",
                        '{"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}',
                    ],
                )
            )

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.stdin = Mock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdout = Mock()
            mock_process.stdout.readline = AsyncMock(
                return_value=b'{"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}\n'
            )
            mock_subprocess.return_value = mock_process

            # Connect to all servers concurrently
            tasks = [client.add_server(config) for config in configs]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed
            assert all(result is True for result in results)
            assert len(client.sessions) == 3

    def test_server_config_validation(self):
        """Test server configuration validation."""
        # Valid config
        config = MCPServerConfig(
            name="test", transport=MCPTransport.STDIO, command=["echo", "test"]
        )
        assert config.name == "test"
        assert config.transport == MCPTransport.STDIO

        # Invalid transport should raise error
        with pytest.raises(ValueError):
            MCPServerConfig(
                name="test",
                transport="invalid",  # type: ignore
                command=["echo", "test"],
            )

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown of MCP client."""
        client = MCPClient()

        # Add a mock server
        mock_session = Mock()
        mock_session.close = AsyncMock()
        client.sessions["test_server"] = mock_session

        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        client.processes["test_server"] = mock_process

        # Test graceful shutdown
        await client.close_all()

        # Verify cleanup
        mock_session.close.assert_called_once()
        mock_process.terminate.assert_called_once()
        assert len(client.sessions) == 0
        assert len(client.processes) == 0


class TestErrorScenarios:
    """Test various error scenarios and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON responses."""
        from yet_claude_code.mcp.simple_session import SimpleClientSession

        # Mock process with malformed JSON
        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline = AsyncMock(return_value=b"invalid json\n")

        session = SimpleClientSession(mock_process)

        with pytest.raises(Exception) as exc_info:
            await session._send_request("test_method")

        assert "Failed to read large response" in str(
            exc_info.value
        ) or "Server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Test handling of empty responses from servers."""
        from yet_claude_code.mcp.simple_session import SimpleClientSession

        mock_process = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")  # Empty response

        session = SimpleClientSession(mock_process)

        with pytest.raises(Exception) as exc_info:
            await session._send_request("test_method")

        assert "No response from server" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_crash_handling(self):
        """Test handling when MCP server process crashes."""
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
        """Test integration with mock filesystem server."""
        client = MCPClient()

        # Use Python to run our mock server
        mock_server_path = Path(__file__).parent / "mocks" / "mock_mcp_server.py"
        config = MCPServerConfig(
            name="mock_filesystem",
            transport=MCPTransport.STDIO,
            command=["python", str(mock_server_path), "filesystem"],
        )

        success = await client.add_server(config)
        assert success
        assert "mock_filesystem" in client.sessions

        # Test tool listing
        tools = await client.list_tools("mock_filesystem")
        assert "mock_filesystem" in tools
        assert len(tools["mock_filesystem"]) > 0

        # Verify expected tools are present
        tool_names = [tool["name"] for tool in tools["mock_filesystem"]]
        expected_tools = ["read_file", "write_file", "list_directory", "search_files"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_retry_mechanism_with_mock(self):
        """Test retry mechanism with a server that fails initially."""
        client = MCPClient()
        client.retry_config["max_retries"] = 2  # Reduce for faster testing

        # Configure to fail initially, then succeed
        call_count = 0
        original_connect = client._connect_stdio_server

        async def failing_connect(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Initial connection failure")
            return await original_connect(config)

        client._connect_stdio_server = failing_connect

        mock_server_path = Path(__file__).parent / "mocks" / "mock_mcp_server.py"
        config = MCPServerConfig(
            name="retry_test",
            transport=MCPTransport.STDIO,
            command=["python", str(mock_server_path), "filesystem"],
        )

        success = await client.add_server(config)
        assert success
        assert call_count == 2  # Should have retried once

    @pytest.mark.asyncio
    async def test_network_error_simulation(self):
        """Test network error simulation and recovery."""
        from yet_claude_code.cli.app import YetClaudeCodeApp

        app = YetClaudeCodeApp()

        # Mock tool call that fails with network error
        tools = []

        # Test network error handling
        result = await app._handle_network_error(
            "fetch_url", {"url": "http://invalid"}, tools
        )
        # Should return None if retry fails
        assert result is None
