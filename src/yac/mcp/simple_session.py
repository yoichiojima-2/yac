import asyncio
import json
from typing import Dict, Any


class SimpleClientSession:
    def __init__(self, process=None):
        self.process = process
        self._request_id = 1

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    async def connect(self, config):
        try:
            if config.transport.value == "stdio":
                self.process = await asyncio.create_subprocess_exec(
                    *config.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                await self._send_request(
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "yac", "version": "0.1.0"},
                    },
                )
                return True
            else:
                raise NotImplementedError(f"Transport {config.transport} not supported")
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    async def _send_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        request = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params:
            request["params"] = params

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        request_id = request["id"]
        for _ in range(10):
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
                    additional_data = b""
                    try:
                        while len(additional_data) < 1024 * 1024:
                            chunk = await asyncio.wait_for(
                                self.process.stdout.read(8192), timeout=1.0
                            )
                            if not chunk:
                                break
                            additional_data += chunk

                            combined_text = (
                                (response_line + additional_data).decode().strip()
                            )
                            try:
                                response = json.loads(combined_text)
                                break
                            except json.JSONDecodeError:
                                continue
                        else:
                            raise Exception(f"Response too large for {method}")
                    except asyncio.TimeoutError:
                        raise Exception(f"Response incomplete for {method}")

                if "id" in response and response["id"] == request_id:
                    break

                if "method" in response:
                    continue

            except asyncio.TimeoutError:
                raise Exception(f"No response from server for {method}")
        else:
            raise Exception(f"Could not find matching response for {method}")

        if "error" in response:
            raise Exception(f"Server error for {method}: {response['error']}")

        return response

    async def list_tools(self):
        response = await self._send_request("tools/list")
        if "result" in response and "tools" in response["result"]:
            return response["result"]["tools"]
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        params = {"name": name, "arguments": arguments}
        response = await self._send_request("tools/call", params)
        if "result" in response:
            return response["result"]
        return {"content": [], "isError": True}

    async def close(self):
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()


SimpleSession = SimpleClientSession
