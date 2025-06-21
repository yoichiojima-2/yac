import os
import yaml
from pathlib import Path
from typing import Any, Optional


class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".yet-claude-code"
        self.config_file = self.config_dir / "config.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    content = f.read()
                    content = os.path.expandvars(content)
                    return yaml.safe_load(content) or {}
            except Exception:
                return {}
        return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        return {
            "provider": "openai",
            "model": "gpt-4-turbo-preview",
            "stream": True,
            "api_keys": {
                "openai": "${OPENAI_API_KEY}",
                "anthropic": "${ANTHROPIC_API_KEY}",
                "google": "${GOOGLE_API_KEY}",
            },
            "context": {
                "max_tokens": 128000,
                "preserve_ratio": 0.8,
            },
            "display": {
                "syntax_highlighting": True,
                "markdown_rendering": True,
                "max_output_lines": 1000,
            },
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_api_key(self, provider: str) -> Optional[str]:
        key = self.get(f"api_keys.{provider}")
        if key and key.startswith("${") and key.endswith("}"):
            env_var = key[2:-1]
            return os.getenv(env_var)
        return key
    
    def save(self):
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)