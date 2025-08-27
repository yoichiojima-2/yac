from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from enum import Enum


class MCPTransport(Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@dataclass
class MCPServerConfig:
    name: str
    transport: MCPTransport
    command: Optional[List[str]] = None
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    args: Optional[List[str]] = None

    def __post_init__(self):
        if self.transport == MCPTransport.STDIO and not self.command:
            raise ValueError("STDIO transport requires command")
        if self.transport in [MCPTransport.SSE, MCPTransport.HTTP] and not self.url:
            raise ValueError(f"{self.transport.value} transport requires url")


@dataclass
class MCPToolCall:
    name: str
    arguments: Dict[str, Union[str, int, float, bool, None]]
    server_name: str


@dataclass
class MCPToolResult:
    content: str
    is_error: bool = False
    metadata: Optional[Dict[str, str]] = None