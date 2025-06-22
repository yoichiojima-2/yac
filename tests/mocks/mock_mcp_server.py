"""Mock MCP servers for testing purposes."""

import asyncio
import json
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MockTool:
    """Represents a mock tool available on an MCP server."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    response: Any = None
    error: Optional[Exception] = None


class MockMCPServer:
    """A mock MCP server that implements the MCP protocol over stdio."""

    def __init__(self, tools: List[MockTool]):
        self.tools = {tool.name: tool for tool in tools}
        self.request_id = 0

    async def run(self):
        """Run the mock server, processing requests from stdin."""
        while True:
            try:
                line = await self._read_line()
                if not line:
                    break

                request = json.loads(line)
                response = await self._handle_request(request)

                if response:
                    await self._write_response(response)

            except json.JSONDecodeError:
                # Invalid JSON, ignore
                continue
            except Exception as e:
                # Send error response
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if "request" in locals() else None,
                    "error": {"code": -32603, "message": str(e)},
                }
                await self._write_response(error_response)

    async def _read_line(self) -> str:
        """Read a line from stdin."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sys.stdin.readline)

    async def _write_response(self, response: Dict[str, Any]):
        """Write response to stdout."""
        response_json = json.dumps(response) + "\n"
        sys.stdout.write(response_json)
        sys.stdout.flush()

    async def _handle_request(
        self, request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle an incoming MCP request."""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}},
                    "serverInfo": {"name": "mock-mcp-server", "version": "1.0.0"},
                },
            }

        elif method == "tools/list":
            tools_list = []
            for tool in self.tools.values():
                tools_list.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                    }
                )

            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools_list}}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found",
                    },
                }

            tool = self.tools[tool_name]

            # Simulate tool error if configured
            if tool.error:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": str(tool.error)}],
                        "isError": True,
                    },
                }

            # Return configured response
            response_text = tool.response
            if callable(response_text):
                response_text = response_text(arguments)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": str(response_text)}],
                    "isError": False,
                },
            }

        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }


def create_filesystem_mock() -> MockMCPServer:
    """Create a mock filesystem MCP server."""
    tools = [
        MockTool(
            name="read_file",
            description="Read a file from the filesystem",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            response=lambda args: f"Mock content of {args.get('path', 'unknown')}",
        ),
        MockTool(
            name="write_file",
            description="Write content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            response=lambda args: f"File {args.get('path')} written successfully",
        ),
        MockTool(
            name="list_directory",
            description="List contents of a directory",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            response=lambda args: "[DIR] subdir1\n[FILE] file1.txt\n[FILE] file2.py",
        ),
        MockTool(
            name="search_files",
            description="Search for files matching a pattern",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}, "path": {"type": "string"}},
                "required": ["query"],
            },
            response=lambda args: f"Found: /mock/path/{args.get('query', 'file')}.txt",
        ),
    ]

    return MockMCPServer(tools)


def create_git_mock() -> MockMCPServer:
    """Create a mock git MCP server."""
    tools = [
        MockTool(
            name="git_status",
            description="Get git repository status",
            input_schema={"type": "object", "properties": {}},
            response='{"branch": "main", "clean": true, "changes": []}',
        ),
        MockTool(
            name="git_add",
            description="Stage files for commit",
            input_schema={
                "type": "object",
                "properties": {"files": {"type": "array", "items": {"type": "string"}}},
            },
            response=lambda args: f"Staged files: {', '.join(args.get('files', []))}",
        ),
        MockTool(
            name="git_commit",
            description="Create a git commit",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            response=lambda args: f"Committed: {args.get('message', 'No message')}",
        ),
    ]

    return MockMCPServer(tools)


def create_failing_server() -> MockMCPServer:
    """Create a mock server that always fails."""
    tools = [
        MockTool(
            name="failing_tool",
            description="A tool that always fails",
            input_schema={"type": "object"},
            error=Exception("Mock tool failure"),
        )
    ]

    return MockMCPServer(tools)


def create_slow_server() -> MockMCPServer:
    """Create a mock server with delayed responses."""

    async def slow_response(args):
        await asyncio.sleep(2)  # 2 second delay
        return "Slow response completed"

    tools = [
        MockTool(
            name="slow_tool",
            description="A tool with delayed response",
            input_schema={"type": "object"},
            response=slow_response,
        )
    ]

    return MockMCPServer(tools)


if __name__ == "__main__":
    """Run a mock server based on command line argument."""
    import sys

    server_type = sys.argv[1] if len(sys.argv) > 1 else "filesystem"

    if server_type == "filesystem":
        server = create_filesystem_mock()
    elif server_type == "git":
        server = create_git_mock()
    elif server_type == "failing":
        server = create_failing_server()
    elif server_type == "slow":
        server = create_slow_server()
    else:
        print(f"Unknown server type: {server_type}", file=sys.stderr)
        sys.exit(1)

    # Run the server
    asyncio.run(server.run())
