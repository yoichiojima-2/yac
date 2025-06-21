from dataclasses import dataclass
from typing import Optional, Dict
from .message import Message


@dataclass
class Response:
    message: Message
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None