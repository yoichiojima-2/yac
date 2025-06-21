import os
from typing import List, AsyncIterator, Optional, Dict, Any
from ..models import Message, Tool, Response, StreamChunk, Role
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview", **kwargs):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), **kwargs)
        self.model = model
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self._client
    
    async def complete(self, messages: List[Message], tools: Optional[List[Tool]] = None, **kwargs) -> Response:
        messages_dict = [msg.to_dict() for msg in messages]
        
        request_kwargs = {
            "model": kwargs.get("model", self.model),
            "messages": messages_dict,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        if tools:
            request_kwargs["tools"] = [self._convert_tool(tool) for tool in tools]
            request_kwargs["tool_choice"] = kwargs.get("tool_choice", "auto")
        
        response = await self.client.chat.completions.create(**request_kwargs)
        
        choice = response.choices[0]
        message = Message(
            role=Role.ASSISTANT,
            content=choice.message.content or "",
            tool_calls=[tc.to_dict() for tc in choice.message.tool_calls] if choice.message.tool_calls else None
        )
        
        return Response(
            message=message,
            usage=response.usage.to_dict() if response.usage else None,
            model=response.model,
            finish_reason=choice.finish_reason
        )
    
    async def stream(self, messages: List[Message], tools: Optional[List[Tool]] = None, **kwargs) -> AsyncIterator[StreamChunk]:
        messages_dict = [msg.to_dict() for msg in messages]
        
        request_kwargs = {
            "model": kwargs.get("model", self.model),
            "messages": messages_dict,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }
        
        if tools:
            request_kwargs["tools"] = [self._convert_tool(tool) for tool in tools]
            request_kwargs["tool_choice"] = kwargs.get("tool_choice", "auto")
        
        stream = await self.client.chat.completions.create(**request_kwargs)
        
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                yield StreamChunk(
                    content=delta.content,
                    tool_calls=[tc.to_dict() for tc in delta.tool_calls] if delta.tool_calls else None,
                    finish_reason=chunk.choices[0].finish_reason,
                    usage=chunk.usage.to_dict() if chunk.usage else None
                )
    
    def supports_tools(self) -> bool:
        return True
    
    def get_max_tokens(self) -> int:
        model_limits = {
            "gpt-4-turbo-preview": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
        }
        return model_limits.get(self.model, 4096)
    
    def count_tokens(self, messages: List[Message]) -> int:
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            total = 0
            for msg in messages:
                total += len(encoding.encode(msg.content))
                total += 4
            return total
        except Exception:
            total_chars = sum(len(msg.content) for msg in messages)
            return int(total_chars / 4)
    
    def _convert_tool(self, tool: Tool) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        }