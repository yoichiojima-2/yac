import asyncio
import sys
from typing import Optional

# Use the newer memory approach instead of deprecated ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from .config import Config
from .display import Display
from ..mcp.client import MCPClient
from ..mcp.config import MCPServerConfig, MCPTransport
from ..mcp.defaults import get_default_mcp_servers


class YetClaudeCodeApp:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.config = Config()
        self.display = Display()
        self.messages: list = []  # Store conversation history directly
        self.llm = self._create_llm(provider, model)
        self.mcp_client = MCPClient()
        self.running = True

    def _create_llm(self, provider: Optional[str] = None, model: Optional[str] = None):
        provider_name = provider or self.config.get_provider()
        model_name = model or self.config.get_model()
        api_key = self.config.get_api_key(provider_name)

        if not api_key:
            raise ValueError(f"No API key found for {provider_name}")

        if provider_name == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name, api_key=api_key, streaming=self.config.should_stream()
            )
        elif provider_name == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model_name,
                anthropic_api_key=api_key,
                streaming=self.config.should_stream(),
            )
        elif provider_name == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                streaming=self.config.should_stream(),
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    async def run(self):
        self.display.welcome()
        await self._load_mcp_servers()

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
            # Add user message to history
            messages = self.messages + [HumanMessage(content=content)]
            response = await self.llm.ainvoke(messages)

            # Store both messages in history
            self.messages.append(HumanMessage(content=content))
            self.messages.append(AIMessage(content=response.content))

            self.display.print_response(response.content)
        except Exception as e:
            self.display.error(f"Error: {e}")

    async def _load_mcp_servers(self):
        self.display.print("Starting MCP setup...")
        servers = self.config.get_mcp_servers()

        # If no servers configured, set up defaults
        if not servers:
            self.display.print("Setting up default MCP servers...")
            default_servers = get_default_mcp_servers()
            for server in default_servers.values():
                self.config.add_mcp_server(server)
            servers = default_servers

        # Connect to servers with timeout and error handling
        for server in servers.values():
            try:
                # Add timeout to prevent hanging
                success = await asyncio.wait_for(
                    self.mcp_client.add_server(server), timeout=30.0
                )
                if success:
                    self.display.print(f"✓ Connected to MCP server: {server.name}")
                else:
                    self.display.print(
                        f"✗ Failed to connect to MCP server: {server.name}"
                    )
            except asyncio.TimeoutError:
                self.display.print(f"✗ Timeout connecting to MCP server: {server.name}")
            except Exception as e:
                self.display.print(
                    f"✗ Error connecting to MCP server {server.name}: {e}"
                )

        connected_servers = len(self.mcp_client.sessions)
        if connected_servers > 0:
            self.display.print(
                f"MCP setup complete - {connected_servers} server(s) connected"
            )
        else:
            self.display.print(
                "MCP setup complete - no servers connected (chat still works!)"
            )

    def handle_command(self, command: str):
        parts = command.split()
        cmd = parts[0]

        if cmd == "/help":
            self.display.show_help()
        elif cmd == "/clear":
            self.messages.clear()
            self.display.print("Conversation cleared.")
        elif cmd == "/mcp":
            asyncio.create_task(self._handle_mcp_command(parts[1:]))
        else:
            self.display.print(f"Unknown command: {command}")

    async def _handle_mcp_command(self, args):
        if not args:
            self.display.print("Usage: /mcp <add|remove|list|tools>")
            return

        subcmd = args[0]

        if subcmd == "add":
            if len(args) < 3:
                self.display.print("Usage: /mcp add <name> <transport> [options...]")
                return
            await self._add_mcp_server(args[1:])
        elif subcmd == "remove":
            if len(args) < 2:
                self.display.print("Usage: /mcp remove <name>")
                return
            await self._remove_mcp_server(args[1])
        elif subcmd == "list":
            await self._list_mcp_servers()
        elif subcmd == "tools":
            server_name = args[1] if len(args) > 1 else None
            await self._list_mcp_tools(server_name)
        else:
            self.display.print(f"Unknown MCP command: {subcmd}")

    async def _add_mcp_server(self, args):
        try:
            name = args[0]
            transport = MCPTransport(args[1])

            if transport == MCPTransport.STDIO:
                if len(args) < 3:
                    self.display.print("STDIO transport requires command")
                    return
                command = args[2:]
                config = MCPServerConfig(
                    name=name, transport=transport, command=command
                )
            else:
                if len(args) < 3:
                    self.display.print(f"{transport.value} transport requires URL")
                    return
                url = args[2]
                config = MCPServerConfig(name=name, transport=transport, url=url)

            success = await self.mcp_client.add_server(config)
            if success:
                self.config.add_mcp_server(config)
                self.display.print(f"Added MCP server: {name}")
            else:
                self.display.print(f"Failed to add MCP server: {name}")
        except Exception as e:
            self.display.print(f"Error adding MCP server: {e}")

    async def _remove_mcp_server(self, name: str):
        success = await self.mcp_client.remove_server(name)
        if success:
            self.config.remove_mcp_server(name)
            self.display.print(f"Removed MCP server: {name}")
        else:
            self.display.print(f"MCP server not found: {name}")

    async def _list_mcp_servers(self):
        servers = self.config.list_mcp_servers()
        if servers:
            self.display.print("MCP Servers:")
            for server in servers:
                self.display.print(f"  - {server}")
        else:
            self.display.print("No MCP servers configured")

    async def _list_mcp_tools(self, server_name: Optional[str]):
        tools = await self.mcp_client.list_tools(server_name)
        if tools:
            for server, server_tools in tools.items():
                self.display.print(f"Tools from {server}:")
                for tool in server_tools:
                    self.display.print(
                        f"  - {tool['name']}: {tool.get('description', 'No description')}"
                    )
        else:
            self.display.print("No tools available")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Yet Claude Code - Multi-model AI assistant"
    )
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
