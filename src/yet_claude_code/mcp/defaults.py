import os
from pathlib import Path
from typing import Dict, List
from .config import MCPServerConfig, MCPTransport


def get_default_mcp_servers(
    workspace_path: str | None = None,
) -> Dict[str, MCPServerConfig]:
    """Get default MCP server configurations for Claude Code compatibility."""

    if workspace_path is None:
        workspace_path = str(Path.cwd())

    servers = {
        "filesystem": MCPServerConfig(
            name="filesystem",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@modelcontextprotocol/server-filesystem",
                workspace_path,
            ],
        ),
        "fetch": MCPServerConfig(
            name="fetch",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@kazuph/mcp-fetch",
            ],
        ),
        "git": MCPServerConfig(
            name="git",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@cyanheads/git-mcp-server",
            ],
        ),
        "bash": MCPServerConfig(
            name="bash",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@wonderwhy-er/desktop-commander",
            ],
        ),
    }

    # Add Brave Search if API key is available
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if brave_api_key:
        servers["brave-search"] = MCPServerConfig(
            name="brave-search",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@modelcontextprotocol/server-brave-search",
            ],
            env={"BRAVE_API_KEY": brave_api_key},
        )

    # Add Puppeteer (no API key required, but might need Chrome installed)
    servers["puppeteer"] = MCPServerConfig(
        name="puppeteer",
        transport=MCPTransport.STDIO,
        command=[
            "npx",
            "-y",
            "@modelcontextprotocol/server-puppeteer",
        ],
    )

    # Sequential Thinking MCP (moved from optional for enhanced reasoning)
    servers["sequential-thinking"] = MCPServerConfig(
        name="sequential-thinking",
        transport=MCPTransport.STDIO,
        command=[
            "npx",
            "-y",
            "@modelcontextprotocol/server-sequential-thinking",
        ],
    )

    return servers


def get_essential_tools() -> List[str]:
    """List of essential tools that should be available."""
    return [
        # Filesystem operations
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "create_directory",
        "search_files",
        "move_file",
        "get_file_info",
        "directory_tree",
        "read_multiple_files",
        # Git operations (always available)
        "git_status",
        "git_diff",
        "git_log",
        "git_add",
        "git_commit",
        "git_push",
        "git_pull",
        "git_branch",
        "git_checkout",
        "git_clone",
        # Terminal/bash operations (always available)
        "execute_command",
        "run_bash",
        "list_processes",
        "get_directory",
        "change_directory",
        # Web browsing and search
        "brave_search",
        "fetch_url",
        "puppeteer_navigate",
        "puppeteer_screenshot",
        "puppeteer_click",
        "puppeteer_type",
        # GitHub operations (if available)
        "get_repo",
        "list_repos",
        "create_issue",
        "get_issue",
        "create_pull_request",
        # Memory operations (if available)
        "store_memory",
        "retrieve_memory",
        "search_memory",
        # Code execution (if available)
        "execute_python",
        "run_code",
        "execute_script",
    ]


def get_optional_mcp_servers(
    workspace_path: str | None = None,
) -> Dict[str, MCPServerConfig]:
    """Get optional MCP server configurations that require additional setup or API keys."""

    if workspace_path is None:
        workspace_path = str(Path.cwd())

    servers = {}

    # GitHub MCP server (requires GitHub token)
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        servers["github"] = MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@modelcontextprotocol/server-github",
            ],
            env={"GITHUB_TOKEN": github_token},
        )

    # Sequential Thinking MCP (useful for complex reasoning) - moved to default
    # servers["sequential-thinking"] = MCPServerConfig(
    #     name="sequential-thinking",
    #     transport=MCPTransport.STDIO,
    #     command=[
    #         "npx",
    #         "-y",
    #         "@modelcontextprotocol/server-sequential-thinking",
    #     ],
    # )

    # Slack MCP server (requires Slack bot token)
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    if slack_bot_token:
        servers["slack"] = MCPServerConfig(
            name="slack",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@modelcontextprotocol/server-slack",
            ],
            env={"SLACK_BOT_TOKEN": slack_bot_token},
        )

    # SQLite MCP server for database operations
    servers["sqlite"] = MCPServerConfig(
        name="sqlite",
        transport=MCPTransport.STDIO,
        command=[
            "npx",
            "-y",
            "@modelcontextprotocol/server-sqlite",
        ],
    )

    # Memory MCP server (requires configuration)
    servers["memory"] = MCPServerConfig(
        name="memory",
        transport=MCPTransport.STDIO,
        command=[
            "npx",
            "-y",
            "@modelcontextprotocol/server-memory",
        ],
    )

    # Desktop Commander MCP - provides terminal control and file editing
    servers["desktop-commander"] = MCPServerConfig(
        name="desktop-commander",
        transport=MCPTransport.STDIO,
        command=[
            "npx",
            "-y",
            "@wonderwhy-er/desktop-commander",
        ],
    )

    # Code execution server for Python
    servers["code-executor"] = MCPServerConfig(
        name="code-executor",
        transport=MCPTransport.STDIO,
        command=[
            "npx",
            "-y",
            "@modelcontextprotocol/server-code-executor",
        ],
    )

    return servers


def get_all_mcp_servers(
    workspace_path: str | None = None,
) -> Dict[str, MCPServerConfig]:
    """Get all available MCP servers (default + optional)."""
    servers = get_default_mcp_servers(workspace_path)
    servers.update(get_optional_mcp_servers(workspace_path))
    return servers
