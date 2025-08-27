import os
from yac.cli.config import Config


def test_config_defaults():
    config = Config()
    assert config.get_provider() == "openai"
    assert config.get_model() == "o3-mini"
    assert config.should_stream() is True


def test_config_env_vars():
    os.environ["YAC_PROVIDER"] = "anthropic"
    os.environ["YAC_MODEL"] = "claude-3-haiku-20240307"
    os.environ["YAC_STREAM"] = "false"

    config = Config()
    assert config.get_provider() == "anthropic"
    assert config.get_model() == "claude-3-haiku-20240307"
    assert config.should_stream() is False

    # Clean up
    del os.environ["YAC_PROVIDER"]
    del os.environ["YAC_MODEL"]
    del os.environ["YAC_STREAM"]


def test_api_key_retrieval():
    os.environ["OPENAI_API_KEY"] = "test-key"
    config = Config()
    assert config.get_api_key("openai") == "test-key"
    del os.environ["OPENAI_API_KEY"]
