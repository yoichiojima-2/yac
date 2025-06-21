import pytest
from yet_claude_code.providers import BaseProvider, ProviderRegistry, register_default_providers
from yet_claude_code.models import Message, Role


def test_provider_registry():
    register_default_providers()
    providers = ProviderRegistry.list()
    assert "openai" in providers


def test_openai_provider_creation():
    register_default_providers()
    provider = ProviderRegistry.create("openai", api_key="test-key")
    assert provider is not None
    assert provider.supports_tools() is True
    assert provider.get_max_tokens() > 0


def test_message_creation():
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"
    
    msg_dict = msg.to_dict()
    assert msg_dict["role"] == "user"
    assert msg_dict["content"] == "Hello"