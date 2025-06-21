from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class ToolResult:
    output: Any
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None