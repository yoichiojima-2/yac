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

            # Check if we should think more for complex queries
            if self._should_think_more(content):
                await self._perform_thinking(content)

            # Try to understand user intent and prepare context
            await self._prepare_context_for_request(content)

            # Start conversation loop
            while True:
                # Get response from LLM
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

                    # Check if we should suggest follow-up actions
                    await self._suggest_followup_actions(response.content)
                    break

        except Exception as e:
            self.display.error(f"Error: {e}")

    def _should_think_more(self, content: str) -> bool:
        """Determine if the query requires deeper thinking."""
        thinking_triggers = [
            "complex",
            "difficult",
            "analyze",
            "compare",
            "explain why",
            "how does",
            "what if",
            "debug",
            "optimize",
            "refactor",
            "design",
            "architecture",
            "strategy",
            "plan",
            "solve",
            "multiple",
            "several",
            "various",
            "different approaches",
        ]

        # Check for complexity indicators
        content_lower = content.lower()
        word_count = len(content.split())

        # Trigger thinking for:
        # 1. Long queries (>20 words)
        # 2. Queries containing thinking trigger words
        # 3. Questions with multiple parts (contains "and" or multiple "?")
        return (
            word_count > 20
            or any(trigger in content_lower for trigger in thinking_triggers)
            or content_lower.count("and") > 1
            or content.count("?") > 1
        )

    async def _perform_thinking(self, content: str):
        """Perform sequential thinking before main response."""
        try:
            # Get available tools
            tools = await self.bridge.get_langchain_tools()
            thinking_tool = next(
                (t for t in tools if t.name == "sequential_thinking"), None
            )

            if thinking_tool:
                self.display.print("🤔 Thinking more deeply about your question...")

                # Use the sequential thinking tool
                thinking_result = await thinking_tool.ainvoke(
                    {
                        "query": content,
                        "steps": 3,  # Number of thinking steps
                    }
                )

                # Add thinking result to conversation context
                from langchain_core.messages import SystemMessage

                thinking_context = SystemMessage(
                    content=f"I've thought about this query: {thinking_result}. Now I'll provide my response."
                )
                self.messages.append(thinking_context)

        except Exception as e:
            # If thinking fails, continue without it
            self.display.print(f"Note: Enhanced thinking unavailable ({e})")

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
        """Handle file not found errors by searching for the file."""
        # Extract filename from args
        filename = None
        if isinstance(args, dict):
            filename = args.get("path") or args.get("file_path") or args.get("filename")
        elif isinstance(args, str):
            filename = args

        if not filename:
            return None

        self.display.print(f"🔍 File '{filename}' not found, searching...")

        # Try to find the file using search tools
        search_tool = next((t for t in tools if t.name == "search_files"), None)
        if search_tool:
            try:
                # Extract just the basename for searching
                import os

                basename = os.path.basename(filename)
                search_result = await search_tool.ainvoke({"query": basename})

                if search_result and "found" in str(search_result).lower():
                    self.display.print(f"✅ Found similar files: {search_result}")

                    # Try to extract the first valid path and retry original operation
                    if hasattr(search_result, "split"):
                        potential_files = [
                            line.strip()
                            for line in str(search_result).split("\n")
                            if basename.lower() in line.lower()
                        ]

                        if potential_files:
                            # Try the first match
                            suggested_path = (
                                potential_files[0].split(":")[0]
                                if ":" in potential_files[0]
                                else potential_files[0]
                            )

                            # Retry original tool with corrected path
                            original_tool = next(
                                (t for t in tools if t.name == tool_name), None
                            )
                            if original_tool:
                                corrected_args = (
                                    args.copy()
                                    if isinstance(args, dict)
                                    else {"path": suggested_path}
                                )
                                if isinstance(corrected_args, dict):
                                    corrected_args.update(
                                        {
                                            key: suggested_path
                                            for key in ["path", "file_path", "filename"]
                                            if key in corrected_args
                                        }
                                    )

                                retry_result = await original_tool.ainvoke(
                                    corrected_args
                                )
                                self.display.print(
                                    f"🎯 Successfully found and used: {suggested_path}"
                                )
                                return retry_result

            except Exception as search_error:
                self.display.print(f"🔍 Search failed: {search_error}")

        # Try directory listing as fallback
        list_tool = next((t for t in tools if t.name == "list_directory"), None)
        if list_tool:
            try:
                # List current directory to show available files
                dir_result = await list_tool.ainvoke({"path": "."})
                self.display.print(
                    f"📁 Available files in current directory:\n{dir_result}"
                )
                return f"File '{filename}' not found. Available files: {dir_result}"
            except Exception:
                pass

        return None

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

    async def _suggest_followup_actions(self, response_content):
        """Suggest intelligent follow-up actions based on the response."""
        if not response_content:
            return

        content_lower = response_content.lower()

        # Suggest actions based on response content
        suggestions = []

        if "error" in content_lower or "failed" in content_lower:
            suggestions.append("🔧 Run diagnostic commands to investigate the issue")
            suggestions.append("📋 Check logs for more details")

        elif "file" in content_lower and "found" in content_lower:
            suggestions.append("📖 Open the file to examine its contents")
            suggestions.append("✏️ Edit the file if modifications are needed")

        elif "test" in content_lower:
            suggestions.append("🧪 Run the test suite to verify functionality")
            suggestions.append("📊 Check test coverage")

        elif "install" in content_lower or "dependency" in content_lower:
            suggestions.append("📦 Verify installation was successful")
            suggestions.append("🔍 Check for version conflicts")

        elif "git" in content_lower or "commit" in content_lower:
            suggestions.append("📊 Check git status")
            suggestions.append("🔄 Review changes before committing")

        # Only show suggestions if we have any and they're relevant
        if suggestions and len(response_content) > 50:  # Only for substantial responses
            self.display.print("\n💡 Suggested next steps:")
            for suggestion in suggestions[:2]:  # Limit to 2 suggestions
                self.display.print(f"   • {suggestion}")

    async def _prepare_context_for_request(self, content):
        """Proactively prepare context based on user request."""
        content_lower = content.lower()

        try:
            tools = await self.bridge.get_langchain_tools()

            # If user mentions a file, try to check if it exists first
            if any(
                keyword in content_lower for keyword in ["read", "open", "show", "file"]
            ):
                # Look for potential file references
                words = content.split()
                for word in words:
                    if "." in word and not word.startswith(".") and len(word) > 3:
                        # Looks like a filename
                        await self._proactive_file_check(word, tools)

            # If user asks about project structure, prepare directory overview
            elif any(
                keyword in content_lower
                for keyword in ["structure", "overview", "files", "project"]
            ):
                await self._proactive_project_overview(tools)

            # If user mentions git, prepare git status
            elif "git" in content_lower:
                await self._proactive_git_status(tools)

        except Exception:
            # Context preparation is optional, don't fail the main request
            pass

    async def _proactive_file_check(self, filename, tools):
        """Proactively check if a file exists and suggest alternatives if not."""
        try:
            read_tool = next((t for t in tools if t.name == "read_file"), None)
            if read_tool:
                # Try to read the file
                await read_tool.ainvoke({"path": filename})
                self.display.print(f"✅ Found file: {filename}")
        except Exception:
            # File doesn't exist, try to find similar files
            search_tool = next((t for t in tools if t.name == "search_files"), None)
            if search_tool:
                try:
                    import os

                    basename = os.path.basename(filename)
                    search_result = await search_tool.ainvoke({"query": basename})
                    if search_result:
                        self.display.print(
                            f"📝 File '{filename}' not found, but found similar: {search_result}"
                        )
                except Exception:
                    pass

    async def _proactive_project_overview(self, tools):
        """Provide project overview proactively."""
        try:
            dir_tool = next((t for t in tools if t.name == "list_directory"), None)
            if dir_tool:
                overview = await dir_tool.ainvoke({"path": "."})
                self.display.print(f"📁 Project overview: {overview}")
        except Exception:
            pass

    async def _proactive_git_status(self, tools):
        """Proactively check git status."""
        try:
            git_tool = next((t for t in tools if t.name == "git_status"), None)
            if git_tool:
                status = await git_tool.ainvoke({})
                self.display.print(f"🔍 Git status: {status}")
        except Exception:
            pass

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
