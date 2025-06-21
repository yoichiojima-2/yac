import os


class Config:
    def __init__(self):
        pass
    
    def get_provider(self) -> str:
        return os.getenv("YCC_PROVIDER", "openai")
    
    def get_model(self) -> str:
        provider = self.get_provider()
        defaults = {
            "openai": "gpt-4-turbo-preview",
            "anthropic": "claude-3-sonnet-20240229", 
            "google": "gemini-pro"
        }
        return os.getenv("YCC_MODEL", defaults.get(provider, "gpt-4-turbo-preview"))
    
    def get_api_key(self, provider: str) -> str:
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY"
        }
        return os.getenv(env_vars.get(provider, ""))
    
    def should_stream(self) -> bool:
        return os.getenv("YCC_STREAM", "true").lower() == "true"