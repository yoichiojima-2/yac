from typing import Dict, Type, Optional
from .base import BaseProvider


class ProviderRegistry:
    _providers: Dict[str, Type[BaseProvider]] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseProvider]]:
        return cls._providers.get(name.lower())
    
    @classmethod
    def list(cls) -> list[str]:
        return list(cls._providers.keys())
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseProvider:
        provider_class = cls.get(name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {name}. Available: {', '.join(cls.list())}")
        return provider_class(**kwargs)


def register_default_providers():
    from .openai import OpenAIProvider
    
    ProviderRegistry.register("openai", OpenAIProvider)
    
    try:
        from .anthropic import AnthropicProvider
        ProviderRegistry.register("anthropic", AnthropicProvider)
    except ImportError:
        pass
    
    try:
        from .google import GoogleProvider
        ProviderRegistry.register("google", GoogleProvider)
    except ImportError:
        pass
    
    try:
        from .ollama import OllamaProvider
        ProviderRegistry.register("ollama", OllamaProvider)
    except ImportError:
        pass