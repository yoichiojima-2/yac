from enum import Enum
from typing import Optional, Any, Dict
from dataclasses import dataclass


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role.value, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result


@dataclass
class StreamChunk:
    content: Optional[str] = None
    tool_calls: Optional[list[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None