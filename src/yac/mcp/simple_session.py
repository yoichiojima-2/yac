"""
Simple MCP client session that works directly with subprocess stdio.
This is a workaround for issues with the mcp library's stdio_client.
"""

import asyncio
import json
from typing import Dict, Any


class SimpleClientSession:
    """Simple MCP client session that communicates directly with a subprocess."""

    def __init__(self, process=None):
        self.process = process
        self._request_id = 1

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    async def connect(self, config):
        """Connect to an MCP server based on configuration."""
        try:
            if config.transport.value == "stdio":
                # Spawn the process for stdio transport
                self.process = await asyncio.create_subprocess_exec(
                    *config.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                # Send initialization request with required clientInfo
                await self._send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "yac",
                        "version": "0.1.0"
                    }
                })
                
                return True
            else:
                # For non-stdio transports, we'd need different handling
                raise NotImplementedError(f"Transport {config.transport} not yet supported")
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    async def _send_request(
        self, method: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request and return the response."""
        request = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            request["params"] = params

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response - handle notifications and find matching response
        request_id = request["id"]
        max_attempts = 10  # Handle up to 10 notifications before timing out
        
        for _ in range(max_attempts):
            try:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(), timeout=5.0
                )
                if not response_line:
                    raise Exception(f"No response from server for {method}")

                response_text = response_line.decode().strip()
                
                try:
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
                
                # Check if this is the response we're waiting for
                if "id" in response and response["id"] == request_id:
                    break
                    
                # If it's a notification or different response, continue reading
                if "method" in response:
                    # It's a notification, ignore and continue
                    continue
                    
            except asyncio.TimeoutError:
                raise Exception(f"No response from server for {method}")
        else:
            raise Exception(f"Could not find matching response for {method}")

        if "error" in response:
            raise Exception(f"Server error for {method}: {response['error']}")

        return response

    async def list_tools(self):
        """List available tools from the MCP server."""
        response = await self._send_request("tools/list")
        
        # Return the tools list directly as expected by MCPClient
        if "result" in response and "tools" in response["result"]:
            return response["result"]["tools"]
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call a tool on the MCP server."""
        params = {"name": name, "arguments": arguments}
        response = await self._send_request("tools/call", params)
        
        # Return the result directly
        if "result" in response:
            return response["result"]
        return {"content": [], "isError": True}

    async def close(self):
        """Close the session and terminate the process."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()


# Compatibility alias for the old name
SimpleSession = SimpleClientSession