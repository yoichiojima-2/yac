from yac.cli.config import Config


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("YAC_PROVIDER", raising=False)
    monkeypatch.delenv("YAC_MODEL", raising=False)
    monkeypatch.delenv("YAC_STREAM", raising=False)

    config = Config()
    assert config.get_provider() == "openai"
    assert config.get_model() == "gpt-5.6-terra"
    assert config.should_stream() is True


def test_per_provider_default_models(monkeypatch):
    monkeypatch.delenv("YAC_MODEL", raising=False)
    config = Config()

    monkeypatch.setenv("YAC_PROVIDER", "anthropic")
    assert config.get_model() == "claude-sonnet-5"

    monkeypatch.setenv("YAC_PROVIDER", "google")
    assert config.get_model() == "gemini-3.5-flash"


def test_config_env_vars(monkeypatch):
    monkeypatch.setenv("YAC_PROVIDER", "anthropic")
    monkeypatch.setenv("YAC_MODEL", "claude-3-haiku-20240307")
    monkeypatch.setenv("YAC_STREAM", "false")

    config = Config()
    assert config.get_provider() == "anthropic"
    assert config.get_model() == "claude-3-haiku-20240307"
    assert config.should_stream() is False


def test_api_key_retrieval(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config = Config()
    assert config.get_api_key("openai") == "test-key"

    monkeypatch.delenv("OPENAI_API_KEY")
    assert config.get_api_key("openai") is None
