import asyncio
import sys
from typing import Optional
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage
from .config import Config
from .display import Display


class YetClaudeCodeApp:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.config = Config()
        self.display = Display()
        self.memory = ConversationBufferMemory(return_messages=True)
        self.llm = self._create_llm(provider, model)
        self.running = True

    def _create_llm(self, provider: Optional[str] = None, model: Optional[str] = None):
        provider_name = provider or self.config.get_provider()
        model_name = model or self.config.get_model()
        api_key = self.config.get_api_key(provider_name)
        
        if not api_key:
            raise ValueError(f"No API key found for {provider_name}")
        
        if provider_name == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_name, api_key=api_key, streaming=self.config.should_stream())
        elif provider_name == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model_name, anthropic_api_key=api_key, streaming=self.config.should_stream())
        elif provider_name == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, streaming=self.config.should_stream())
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    async def run(self):
        self.display.welcome()
        
        while self.running:
            try:
                user_input = input(self.display.get_prompt())
                if not user_input.strip():
                    continue
                if user_input.lower() in ["/exit", "/quit", "/q"]:
                    break
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                    continue
                await self.process_message(user_input)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self.display.error(str(e))
        
        self.display.goodbye()

    async def process_message(self, content: str):
        try:
            messages = self.memory.chat_memory.messages + [HumanMessage(content=content)]
            response = await self.llm.ainvoke(messages)
            self.memory.chat_memory.add_user_message(content)
            self.memory.chat_memory.add_ai_message(response.content)
            self.display.print_response(response.content)
        except Exception as e:
            self.display.error(f"Error: {e}")

    def handle_command(self, command: str):
        if command == "/help":
            self.display.show_help()
        elif command == "/clear":
            self.memory.clear()
            self.display.print("Conversation cleared.")
        else:
            self.display.print(f"Unknown command: {command}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Yet Claude Code - Multi-model AI assistant")
    parser.add_argument("--provider", help="AI provider (openai, anthropic, google)")
    parser.add_argument("--model", help="Model to use")
    args = parser.parse_args()
    
    try:
        app = YetClaudeCodeApp(provider=args.provider, model=args.model)
        asyncio.run(app.run())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)