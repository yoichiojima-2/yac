from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Optional
from ..models import Message, Tool, Response, StreamChunk


class BaseProvider(ABC):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    async def complete(self, messages: List[Message], tools: Optional[List[Tool]] = None, **kwargs) -> Response:
        pass
    
    @abstractmethod
    async def stream(self, messages: List[Message], tools: Optional[List[Tool]] = None, **kwargs) -> AsyncIterator[StreamChunk]:
        pass
    
    @abstractmethod
    def supports_tools(self) -> bool:
        pass
    
    @abstractmethod
    def get_max_tokens(self) -> int:
        pass
    
    @abstractmethod
    def count_tokens(self, messages: List[Message]) -> int:
        pass