import asyncio
import sys
from typing import Optional
from ..providers import ProviderRegistry, register_default_providers
from ..models import Message, Role
from .display import Display
from .config import Config


class YetClaudeCodeApp:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        register_default_providers()
        
        self.config = Config()
        self.display = Display()
        
        provider_name = provider or self.config.get("provider", "openai")
        self.provider = ProviderRegistry.create(
            provider_name,
            model=model or self.config.get("model"),
            api_key=self.config.get_api_key(provider_name)
        )
        
        self.messages: list[Message] = []
        self.running = True
    
    async def run(self):
        self.display.welcome()
        
        if self.config.get("system_prompt"):
            self.messages.append(Message(
                role=Role.SYSTEM,
                content=self.config.get("system_prompt", "You are a helpful AI assistant.")
            ))
        
        while self.running:
            try:
                user_input = await self.get_user_input()
                if not user_input:
                    continue
                
                if user_input.lower() in ["/exit", "/quit", "/q"]:
                    self.running = False
                    break
                
                if user_input.startswith("/"):
                    await self.handle_command(user_input)
                    continue
                
                await self.process_message(user_input)
                
            except KeyboardInterrupt:
                self.display.print("\nExiting...")
                break
            except Exception as e:
                self.display.error(f"Error: {e}")
        
        self.display.goodbye()
    
    async def get_user_input(self) -> str:
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: input(self.display.get_prompt())
        )
    
    async def process_message(self, content: str):
        self.messages.append(Message(role=Role.USER, content=content))
        
        try:
            self.display.thinking()
            
            if self.config.get("stream", True):
                response_content = ""
                async for chunk in self.provider.stream(self.messages):
                    if chunk.content:
                        response_content += chunk.content
                        self.display.stream_chunk(chunk.content)
                
                self.display.stream_end()
                self.messages.append(Message(role=Role.ASSISTANT, content=response_content))
            else:
                response = await self.provider.complete(self.messages)
                self.messages.append(response.message)
                self.display.print_message(response.message)
        
        except Exception as e:
            self.display.error(f"Provider error: {e}")
            self.messages.pop()
    
    async def handle_command(self, command: str):
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/help":
            self.display.show_help()
        elif cmd == "/clear":
            self.messages = self.messages[:1] if self.messages and self.messages[0].role == Role.SYSTEM else []
            self.display.print("Conversation cleared.")
        elif cmd == "/model":
            if len(parts) > 1:
                self.provider.model = parts[1]
                self.display.print(f"Model set to: {parts[1]}")
            else:
                self.display.print(f"Current model: {getattr(self.provider, 'model', 'unknown')}")
        elif cmd == "/tokens":
            token_count = self.provider.count_tokens(self.messages)
            self.display.print(f"Current conversation: {token_count} tokens")
        else:
            self.display.print(f"Unknown command: {cmd}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Yet Claude Code - Multi-model AI assistant")
    parser.add_argument("--provider", help="AI provider (openai, anthropic, google, ollama)")
    parser.add_argument("--model", help="Model to use")
    
    args = parser.parse_args()
    
    app = YetClaudeCodeApp(provider=args.provider, model=args.model)
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        sys.exit(0)