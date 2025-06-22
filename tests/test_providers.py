import os
from yet_claude_code.cli.config import Config


def test_config_defaults():
    config = Config()
    assert config.get_provider() == "openai"
    assert config.get_model() == "gpt-4-turbo-preview"
    assert config.should_stream() is True


def test_config_env_vars():
    os.environ["YCC_PROVIDER"] = "anthropic"
    os.environ["YCC_MODEL"] = "claude-3-haiku-20240307"
    os.environ["YCC_STREAM"] = "false"

    config = Config()
    assert config.get_provider() == "anthropic"
    assert config.get_model() == "claude-3-haiku-20240307"
    assert config.should_stream() is False

    # Clean up
    del os.environ["YCC_PROVIDER"]
    del os.environ["YCC_MODEL"]
    del os.environ["YCC_STREAM"]


def test_api_key_retrieval():
    os.environ["OPENAI_API_KEY"] = "test-key"
    config = Config()
    assert config.get_api_key("openai") == "test-key"
    del os.environ["OPENAI_API_KEY"]
