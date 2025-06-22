from pathlib import Path
from typing import Dict, List
from .config import MCPServerConfig, MCPTransport


def get_default_mcp_servers(
    workspace_path: str | None = None,
) -> Dict[str, MCPServerConfig]:
    """Get default MCP server configurations for Claude Code compatibility."""

    if workspace_path is None:
        workspace_path = str(Path.cwd())

    return {
        "filesystem": MCPServerConfig(
            name="filesystem",
            transport=MCPTransport.STDIO,
            command=[
                "npx",
                "-y",
                "@modelcontextprotocol/server-filesystem",
                workspace_path,
            ],
        )
    }


def get_essential_tools() -> List[str]:
    """List of essential tools that should be available."""
    return [
        # Filesystem operations
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "create_directory",
        "search_files",
        # GitHub operations
        "get_repo",
        "list_repos",
        "create_issue",
        "get_issue",
        "create_pull_request",
        # Memory operations
        "store_memory",
        "retrieve_memory",
        "search_memory",
    ]
