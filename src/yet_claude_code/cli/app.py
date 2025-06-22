import asyncio
import sys
from typing import Optional

# Use the newer memory approach instead of deprecated ConversationBufferMemory
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import SecretStr
from .config import Config
from .display import Display
from ..mcp.client import MCPClient
from ..mcp.config import MCPServerConfig, MCPTransport
from ..mcp.defaults import get_default_mcp_servers, get_optional_mcp_servers
from ..mcp.langchain_bridge import MCPLangChainBridge


class YetClaudeCodeApp:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.config = Config()
        self.display = Display()
        self.messages: list = []  # Store conversation history directly
        self.base_llm = self._create_llm(provider, model)
        self.llm = self.base_llm  # Will be updated with tools after MCP setup
        self.mcp_client = MCPClient()
        self.bridge = MCPLangChainBridge(self.mcp_client)
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
                model=model_name,
                api_key=SecretStr(api_key),
                streaming=self.config.should_stream(),
            )
        elif provider_name == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model_name=model_name,
                api_key=SecretStr(api_key),
                streaming=self.config.should_stream(),
                timeout=None,
                stop=None,
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
                    await self.handle_command(user_input)
                    continue
                await self.process_message(user_input)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self.display.error(str(e))

        self.display.goodbye()

    async def process_message(self, content: str):
        try:
            # Store user message first
            self.messages.append(HumanMessage(content=content))

            # Add system context to help the AI reason through problems
            await self._add_reasoning_context(content)

            # Start agent-style conversation loop
            while True:
                # Get response from LLM with reasoning instructions
                response = await self.llm.ainvoke(self.messages)

                # Store the AI response
                self.messages.append(response)

                # Handle tool calls if present
                if hasattr(response, "tool_calls") and response.tool_calls:
                    # Execute each tool call and collect results
                    tool_messages = []

                    for tool_call in response.tool_calls:
                        try:
                            # Find the tool by name
                            tools = await self.bridge.get_langchain_tools()
                            tool = next(
                                (t for t in tools if t.name == tool_call["name"]), None
                            )

                            if tool:
                                # Execute the tool
                                tool_result = await tool.ainvoke(tool_call["args"])

                                # Create tool message
                                tool_message = ToolMessage(
                                    content=str(tool_result),
                                    tool_call_id=tool_call["id"],
                                )
                                tool_messages.append(tool_message)

                                self.display.print(
                                    f"🔧 Executed {tool_call['name']}: {tool_result}"
                                )
                            else:
                                error_msg = f"Tool '{tool_call['name']}' not found"
                                tool_message = ToolMessage(
                                    content=error_msg, tool_call_id=tool_call["id"]
                                )
                                tool_messages.append(tool_message)
                                self.display.error(error_msg)

                        except Exception as e:
                            # Try intelligent error handling first
                            retry_result = await self._handle_tool_error(
                                tool_call, e, tools
                            )

                            if retry_result:
                                # Successful retry
                                tool_message = ToolMessage(
                                    content=str(retry_result),
                                    tool_call_id=tool_call["id"],
                                )
                                tool_messages.append(tool_message)
                                self.display.print(
                                    f"🔧 Executed {tool_call['name']} (after intelligent retry): {retry_result}"
                                )
                            else:
                                # Still failed after intelligent handling
                                error_msg = (
                                    f"Error executing {tool_call['name']}: {str(e)}"
                                )
                                tool_message = ToolMessage(
                                    content=error_msg, tool_call_id=tool_call["id"]
                                )
                                tool_messages.append(tool_message)
                                self.display.error(error_msg)

                    # Add all tool messages to conversation
                    self.messages.extend(tool_messages)

                    # Continue the loop to get LLM's final response
                    continue
                else:
                    # No tool calls, print response and exit loop
                    self.display.print_response(response.content)
                    break

        except Exception as e:
            self.display.error(f"Error: {e}")

    async def _handle_tool_error(self, tool_call, error, tools):
        """Intelligent error handling for tool failures."""
        tool_name = tool_call["name"]
        args = tool_call["args"]
        error_str = str(error).lower()

        try:
            # Handle file not found errors
            if (
                "file not found" in error_str
                or "no such file" in error_str
                or "does not exist" in error_str
            ):
                return await self._handle_file_not_found(tool_name, args, tools)

            # Handle permission errors
            elif "permission denied" in error_str:
                return await self._handle_permission_error(tool_name, args, tools)

            # Handle directory not found
            elif "directory not found" in error_str or "no such directory" in error_str:
                return await self._handle_directory_not_found(tool_name, args, tools)

            # Handle network/connection errors
            elif (
                "connection" in error_str
                or "timeout" in error_str
                or "network" in error_str
            ):
                return await self._handle_network_error(tool_name, args, tools)

        except Exception as retry_error:
            self.display.print(f"🔄 Intelligent retry also failed: {retry_error}")

        return None

    async def _handle_file_not_found(self, tool_name, args, tools):
        """Handle file not found errors by providing context for AI reasoning."""
        # Extract filename from args
        filename = None
        if isinstance(args, dict):
            filename = args.get("path") or args.get("file_path") or args.get("filename")
        elif isinstance(args, str):
            filename = args

        if not filename:
            return None

        # Instead of hardcoded search, provide information for the AI to reason about
        error_context = f"File '{filename}' not found. "

        # Give the AI information about available tools to investigate
        available_tools = [t.name for t in tools]
        investigation_tools = [
            t
            for t in available_tools
            if t
            in ["search_files", "list_directory", "directory_tree", "execute_command"]
        ]

        if investigation_tools:
            error_context += (
                f"Available tools to investigate: {', '.join(investigation_tools)}. "
            )
            error_context += "Consider using search_files to look for similar files, list_directory to see what's available, or execute_command with 'find' to search the filesystem."

        return error_context

    async def _handle_permission_error(self, tool_name, args, tools):
        """Handle permission errors."""
        self.display.print("🔒 Permission denied, trying alternative approaches...")
        # Could implement chmod, sudo alternatives, or different file operations
        return None

    async def _handle_directory_not_found(self, tool_name, args, tools):
        """Handle directory not found errors."""
        directory = None
        if isinstance(args, dict):
            directory = args.get("path") or args.get("directory")
        elif isinstance(args, str):
            directory = args

        if directory:
            self.display.print(
                f"📁 Directory '{directory}' not found, checking parent directories..."
            )
            # Could implement directory creation or alternative path suggestions

        return None

    async def _handle_network_error(self, tool_name, args, tools):
        """Handle network/connection errors with retry logic."""
        self.display.print("🌐 Network error detected, retrying...")

        # Simple retry for network operations
        try:
            import asyncio

            await asyncio.sleep(1)  # Brief delay

            original_tool = next((t for t in tools if t.name == tool_name), None)
            if original_tool:
                retry_result = await original_tool.ainvoke(args)
                self.display.print("✅ Network retry successful")
                return retry_result

        except Exception as retry_error:
            self.display.print(f"🌐 Network retry failed: {retry_error}")

        return None

    async def _add_reasoning_context(self, content: str):
        """Add context to help the AI reason through problems step by step."""
        from langchain_core.messages import SystemMessage

        reasoning_prompt = """You are a coding assistant that solves problems step by step, like Claude Code.

When faced with a problem:
1. THINK about what you need to do first
2. Use the available tools to investigate (search_files, list_directory, read_file, etc.)
3. Based on what you find, decide the next step
4. Take action using the appropriate tools
5. Continue until the problem is solved

If a file is missing:
- Use search_files to look for similar files
- Use list_directory to see what's available
- Try different search terms and patterns
- Don't give up after the first attempt - keep investigating

Available tools include: read_file, write_file, search_files, list_directory, directory_tree, execute_command, git_status, and more.

Be methodical and persistent. Reason through each step aloud."""

        # Only add this context once per conversation to avoid repetition
        if not any(
            isinstance(msg, SystemMessage) and "step by step" in msg.content
            for msg in self.messages
        ):
            self.messages.append(SystemMessage(content=reasoning_prompt))

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
            # Bind MCP tools to the LLM
            try:
                self.llm = await self.bridge.bind_tools_to_llm(self.base_llm)
                self.display.print("✓ MCP tools bound to LLM")
            except Exception as e:
                self.display.print(f"Warning: Failed to bind MCP tools: {e}")
                self.llm = self.base_llm
        else:
            self.display.print(
                "MCP setup complete - no servers connected (chat still works!)"
            )

    async def handle_command(self, command: str):
        parts = command.split()
        cmd = parts[0]

        if cmd == "/help":
            self.display.show_help()
        elif cmd == "/clear":
            self.messages.clear()
            self.display.print("Conversation cleared.")
        elif cmd == "/mcp":
            await self._handle_mcp_command(parts[1:])
        else:
            self.display.print(f"Unknown command: {command}")

    async def _handle_mcp_command(self, args):
        if not args:
            self.display.print("Usage: /mcp <add|remove|list|tools|available>")
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
        elif subcmd == "available":
            await self._list_available_mcp_servers()
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

    async def _list_available_mcp_servers(self):
        """List all available MCP servers (default + optional)."""
        import os

        self.display.print("Available MCP Servers:")
        self.display.print("")

        # Show default servers (always available)
        default_servers = get_default_mcp_servers()
        self.display.print("Default servers (always available):")
        for name, config in default_servers.items():
            status = (
                "✓ Connected" if name in self.mcp_client.sessions else "○ Available"
            )
            self.display.print(f"  {status} {name}")
            self.display.print(f"    Command: {' '.join(config.command)}")

        self.display.print("")

        # Show optional servers
        optional_servers = get_optional_mcp_servers()
        self.display.print("Optional servers (require setup/API keys):")
        for name, config in optional_servers.items():
            # Check if server would be enabled (has required env vars)
            enabled = True
            required_env_vars = []

            if name == "github" and not os.getenv("GITHUB_TOKEN"):
                enabled = False
                required_env_vars.append("GITHUB_TOKEN")
            elif name == "brave-search" and not os.getenv("BRAVE_API_KEY"):
                enabled = False
                required_env_vars.append("BRAVE_API_KEY")
            elif name == "slack" and not os.getenv("SLACK_BOT_TOKEN"):
                enabled = False
                required_env_vars.append("SLACK_BOT_TOKEN")

            if enabled:
                status = (
                    "✓ Connected" if name in self.mcp_client.sessions else "✓ Available"
                )
            else:
                status = f"✗ Missing: {', '.join(required_env_vars)}"

            self.display.print(f"  {status} {name}")
            self.display.print(f"    Command: {' '.join(config.command)}")

        self.display.print("")
        self.display.print(
            "To enable optional servers, set the required environment variables."
        )
        self.display.print(
            "Use '/mcp add <name> stdio <command>' to add custom servers."
        )


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
