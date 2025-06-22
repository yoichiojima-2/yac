import os
import json
from pathlib import Path
from typing import Dict, List

from ..mcp.config import MCPServerConfig, MCPTransport


class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".yet-claude-code"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        self._config_data = self._load_config()

    def get_provider(self) -> str:
        return os.getenv("YCC_PROVIDER", "openai")

    def get_model(self) -> str:
        provider = self.get_provider()
        defaults = {
            "openai": "o3-mini",
            "anthropic": "claude-3-sonnet-20240229",
            "google": "gemini-pro",
        }
        return os.getenv("YCC_MODEL", defaults.get(provider, "gpt-4-turbo-preview"))

    def get_api_key(self, provider: str) -> str | None:
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        return os.getenv(env_vars.get(provider, ""))

    def should_stream(self) -> bool:
        return os.getenv("YCC_STREAM", "true").lower() == "true"

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"mcp_servers": {}}

    def _save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self._config_data, f, indent=2)

    def get_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        servers = {}
        for name, data in self._config_data.get("mcp_servers", {}).items():
            try:
                servers[name] = MCPServerConfig(
                    name=name,
                    transport=MCPTransport(data["transport"]),
                    command=data.get("command"),
                    url=data.get("url"),
                    env=data.get("env"),
                    headers=data.get("headers"),
                    args=data.get("args"),
                )
            except (KeyError, ValueError) as e:
                print(f"Invalid MCP server config for {name}: {e}")
        return servers

    def add_mcp_server(self, config: MCPServerConfig):
        self._config_data.setdefault("mcp_servers", {})[config.name] = {
            "transport": config.transport.value,
            "command": config.command,
            "url": config.url,
            "env": config.env,
            "headers": config.headers,
            "args": config.args,
        }
        self._save_config()

    def remove_mcp_server(self, name: str) -> bool:
        if name in self._config_data.get("mcp_servers", {}):
            del self._config_data["mcp_servers"][name]
            self._save_config()
            return True
        return False

    def list_mcp_servers(self) -> List[str]:
        return list(self._config_data.get("mcp_servers", {}).keys())
