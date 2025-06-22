"""
Simple MCP client session that works directly with subprocess stdio.
This is a workaround for issues with the mcp library's stdio_client.
"""

import asyncio
import json
from typing import Dict, Any


class SimpleClientSession:
    """Simple MCP client session that communicates directly with a subprocess."""

    def __init__(self, process):
        self.process = process
        self._request_id = 1

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    async def _send_request(
        self, method: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request and return the response."""
        request = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params:
            request["params"] = params

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response - handle large responses by reading more data if needed
        try:
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise Exception(f"No response from server for {method}")

            response_text = response_line.decode().strip()
            response = json.loads(response_text)

        except json.JSONDecodeError:
            # If JSON decode fails, it might be a truncated large response
            # Try reading more data
            additional_data = b""
            try:
                # Read up to 1MB more data for large responses
                while len(additional_data) < 1024 * 1024:  # 1MB limit
                    chunk = await asyncio.wait_for(
                        self.process.stdout.read(8192), timeout=1.0
                    )
                    if not chunk:
                        break
                    additional_data += chunk

                    # Try parsing the combined data
                    combined_text = (response_line + additional_data).decode().strip()
                    try:
                        response = json.loads(combined_text)
                        break
                    except json.JSONDecodeError:
                        continue
                else:
                    raise Exception(f"Response too large or malformed for {method}")

            except asyncio.TimeoutError:
                raise Exception(f"Response incomplete or server hung for {method}")
            except Exception as read_error:
                raise Exception(
                    f"Failed to read large response for {method}: {read_error}"
                )

        if "error" in response:
            raise Exception(f"Server error for {method}: {response['error']}")

        return response

    async def list_tools(self):
        """List available tools from the MCP server."""
        response = await self._send_request("tools/list")

        # Convert to the format expected by the calling code
        class ToolsResult:
            def __init__(self, tools_data):
                self.tools = []
                if "result" in tools_data and "tools" in tools_data["result"]:
                    for tool_data in tools_data["result"]["tools"]:
                        self.tools.append(Tool(tool_data))

        class Tool:
            def __init__(self, data):
                self.data = data

            def model_dump(self):
                return self.data

        return ToolsResult(response)

    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call a tool on the MCP server."""
        params = {"name": name, "arguments": arguments}
        response = await self._send_request("tools/call", params)

        # Convert to the format expected by the calling code
        class ToolResult:
            def __init__(self, result_data):
                self.content = []
                self.isError = False

                if "result" in result_data:
                    result = result_data["result"]
                    if "content" in result:
                        for item in result["content"]:
                            self.content.append(ContentItem(item))
                    if "isError" in result:
                        self.isError = result["isError"]

        class ContentItem:
            def __init__(self, data):
                self.text = data.get("text", "")
                self.data = data

        return ToolResult(response)

    async def close(self):
        """Close the session and terminate the process."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
