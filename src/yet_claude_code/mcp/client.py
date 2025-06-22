import asyncio
from typing import Dict, List, Optional, Any, Protocol

from .config import MCPServerConfig, MCPTransport, MCPToolCall, MCPToolResult


class MCPSession(Protocol):
    """Protocol defining the interface for MCP sessions."""

    async def list_tools(self) -> Any: ...

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any: ...

    async def close(self) -> None: ...


class MCPClient:
    def __init__(self) -> None:
        self.servers: Dict[str, MCPServerConfig] = {}
        self.sessions: Dict[str, MCPSession] = {}
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.stdio_contexts: Dict[str, Any] = {}

    async def add_server(self, config: MCPServerConfig) -> bool:
        try:
            self.servers[config.name] = config

            if config.transport == MCPTransport.STDIO:
                await self._connect_stdio_server(config)
            elif config.transport == MCPTransport.SSE:
                await self._connect_sse_server(config)
            elif config.transport == MCPTransport.HTTP:
                await self._connect_http_server(config)

            return True
        except Exception as e:
            print(f"Failed to connect to server {config.name}: {e}")
            return False

    async def _connect_stdio_server(self, config: MCPServerConfig):
        print(f"Connecting to {config.name} with command: {config.command}")

        try:
            # Use our own subprocess management instead of the mcp library's stdio_client
            # which seems to have stream communication issues
            print(f"Starting stdio connection for {config.name}...")

            if not config.command:
                raise ValueError("No command specified for STDIO server")

            process = await asyncio.create_subprocess_exec(
                config.command[0],
                *config.command[1:],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Store the process for cleanup
            self.processes[config.name] = process

            # Create streams from the process
            import json

            # Create a simple session that communicates directly with the process
            print(f"Initializing session for {config.name}...")

            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "yet-claude-code", "version": "1.0.0"},
                },
            }

            request_json = json.dumps(init_request) + "\n"
            if process.stdin is None:
                raise Exception("Process stdin is not available")
            process.stdin.write(request_json.encode())
            await process.stdin.drain()

            # Read the response
            if process.stdout is None:
                raise Exception("Process stdout is not available")
            response_line = await process.stdout.readline()
            if not response_line:
                raise Exception("No response from server")

            response = json.loads(response_line.decode().strip())

            if "error" in response:
                raise Exception(f"Server initialization error: {response['error']}")

            # Create a simple client session wrapper
            from .simple_session import SimpleClientSession

            session = SimpleClientSession(process)
            self.sessions[config.name] = session

            print(f"Successfully connected to {config.name}")

        except Exception as e:
            import traceback

            print(f"Failed to connect to {config.name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Clean up process if it exists
            if config.name in self.processes:
                try:
                    self.processes[config.name].terminate()
                    del self.processes[config.name]
                except Exception:
                    pass
            raise

    async def _connect_sse_server(self, config: MCPServerConfig):
        pass

    async def _connect_http_server(self, config: MCPServerConfig):
        pass

    async def list_tools(
        self, server_name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        tools = {}

        servers_to_check = [server_name] if server_name else self.sessions.keys()

        for name in servers_to_check:
            if name in self.sessions:
                try:
                    result = await self.sessions[name].list_tools()
                    tools[name] = [tool.model_dump() for tool in result.tools]
                except Exception as e:
                    print(f"Failed to list tools for {name}: {e}")
                    tools[name] = []

        return tools

    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        if tool_call.server_name not in self.sessions:
            return MCPToolResult(
                content=f"Server {tool_call.server_name} not connected", is_error=True
            )

        try:
            session = self.sessions[tool_call.server_name]
            result = await session.call_tool(tool_call.name, tool_call.arguments)

            content = ""
            for item in result.content:
                if hasattr(item, "text"):
                    content += item.text
                elif hasattr(item, "data"):
                    content += str(item.data)

            return MCPToolResult(
                content=content,
                is_error=result.isError if hasattr(result, "isError") else False,
            )
        except Exception as e:
            return MCPToolResult(content=f"Tool call failed: {e}", is_error=True)

    async def remove_server(self, server_name: str) -> bool:
        # Close session first
        if server_name in self.sessions:
            try:
                await self.sessions[server_name].close()
                del self.sessions[server_name]
            except Exception as e:
                print(f"Error closing session for {server_name}: {e}")

        # Clean up stdio context
        if server_name in self.stdio_contexts:
            try:
                # Suppress the task boundary error by catching and ignoring it
                stdio_context = self.stdio_contexts[server_name]
                try:
                    await stdio_context.__aexit__(None, None, None)
                except (RuntimeError, Exception) as e:
                    # Ignore task boundary errors during cleanup
                    if "cancel scope" not in str(e):
                        print(f"Error closing stdio context for {server_name}: {e}")
                del self.stdio_contexts[server_name]
            except Exception as e:
                print(f"Error cleaning up stdio context for {server_name}: {e}")

        # Clean up processes
        if server_name in self.processes:
            try:
                self.processes[server_name].terminate()
                del self.processes[server_name]
            except Exception as e:
                print(f"Error terminating process for {server_name}: {e}")

        if server_name in self.servers:
            del self.servers[server_name]
            return True

        return False

    async def close_all(self):
        for name in list(self.sessions.keys()):
            await self.remove_server(name)
