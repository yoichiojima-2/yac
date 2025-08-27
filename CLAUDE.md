# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`yac` (Yet Another Claude) is an alternative implementation of Claude Code that provides model flexibility. While Claude Code only works with Claude models, this project aims to deliver the same core features but with the ability to switch between different AI models (e.g., GPT-4, Gemini, local models, etc.).

The project uses modern Python packaging standards with `pyproject.toml` configuration.

## Development Setup

1. **Python Version**: This project uses Python 3.13.5 (specified in `.python-version`)
2. **Virtual Environment**: Already created at `.venv`
3. **Installation**: Run `pip install -e .` to install in editable mode

## Project Structure

```
src/yac/             # Main package directory
├── __init__.py       # Package initialization
├── main.py          # Main entry point
├── cli/             # Command-line interface
│   └── app.py       # CLI application and MCP orchestration
└── mcp/             # MCP (Model Context Protocol) integration
    ├── client.py    # MCP client for server communication
    ├── config.py    # MCP configuration structures
    ├── defaults.py  # Default MCP server configurations
    ├── simple_session.py  # Custom MCP session handling
    └── langchain_bridge.py  # LangChain tool integration
tests/               # Test directory
```

## Available Tools

This project provides the same comprehensive toolset as Claude Code through MCP servers:

### Core File Operations (Always Available)
- **read_file** - Read file contents
- **write_file** - Write/create files
- **edit_file** - Edit existing files with find/replace
- **list_directory** - List directory contents
- **create_directory** - Create new directories
- **search_files** - Search for files by name/pattern
- **move_file** - Move/rename files
- **get_file_info** - Get file metadata
- **directory_tree** - Show directory structure
- **read_multiple_files** - Batch file reading

### Git Operations (Always Available)
- **git_status** - Show repository status
- **git_diff** - Show file differences
- **git_log** - View commit history
- **git_add** - Stage files for commit
- **git_commit** - Create commits
- **git_push** - Push changes to remote
- **git_pull** - Pull changes from remote
- **git_branch** - List/create/delete branches
- **git_checkout** - Switch branches or restore files
- **git_clone** - Clone repositories

### Terminal Operations (Always Available)
- **execute_command** - Run shell commands
- **run_bash** - Execute bash scripts
- **list_processes** - Show running processes
- **get_directory** - Get current directory
- **change_directory** - Change working directory

### Web Operations
- **brave_search** - Web search capabilities
- **fetch_url** - Fetch web page content
- **puppeteer_navigate** - Browser automation navigation
- **puppeteer_screenshot** - Take browser screenshots
- **puppeteer_click** - Automated clicking
- **puppeteer_type** - Automated text input

### GitHub Integration (with GITHUB_TOKEN)
- **get_repo** - Fetch repository information
- **list_repos** - List repositories
- **create_issue** - Create GitHub issues
- **get_issue** - Retrieve issue details
- **create_pull_request** - Create pull requests

### Memory & Persistence
- **store_memory** - Store information for later use
- **retrieve_memory** - Retrieve stored information
- **search_memory** - Search through stored data

### Database Operations
- **sqlite_query** - Execute SQL queries
- **sqlite_schema** - View database schema

### Terminal Operations (via desktop-commander)
- **run_command** - Execute terminal commands
- **list_processes** - Show running processes

### Code Execution (Optional)
- **execute_python** - Run Python code snippets
- **run_code** - Execute code in various languages
- **execute_script** - Run script files

### Advanced Features
- **sequential_thinking** - Enhanced reasoning capabilities
- **slack_integration** - Slack bot operations (with SLACK_BOT_TOKEN)

## Current State

- Core CLI application implemented with MCP integration
- Full MCP server ecosystem configured and operational
- LangChain integration for model flexibility
- Comprehensive tool set matching Claude Code capabilities
- Support for multiple AI model providers

## Environment Setup

### Required Environment Variables

For full functionality, set these environment variables:

- **BRAVE_API_KEY** - Enable web search capabilities
- **GITHUB_TOKEN** - Enable GitHub operations and repository access
- **SLACK_BOT_TOKEN** - Enable Slack integration features

### Common Development Tasks

The project supports standard development workflows:

1. **Dependencies**: Managed via `pyproject.toml` with automatic MCP server installation
2. **Testing**: Run test suite with `python -m pytest tests/`
3. **Linting**: Code quality checks via pre-commit hooks
4. **Development**: CLI entry point at `src/yac/cli/app.py`

## Claude Code Feature Parity

This implementation provides the same capabilities as Claude Code:

### ✅ Implemented Features
1. **Model Abstraction Layer** - LangChain integration supports multiple AI providers
2. **MCP Integration** - Full MCP server ecosystem with 20+ tools
3. **CLI Interface** - Interactive command-line interface matching Claude Code UX
4. **File Operations** - Complete file system management (read, write, edit, search)
5. **Web Capabilities** - Search, browsing, and content fetching
6. **Code Understanding** - Project analysis and codebase navigation
7. **Git Integration** - Through GitHub MCP server and filesystem tools
8. **Memory System** - Persistent memory across sessions

### 🔧 Core Workflows Supported
- **Bug Fixing** - Error analysis and code repair
- **Code Refactoring** - Modernization and optimization
- **Testing** - Test generation and execution
- **Documentation** - Code documentation generation
- **Codebase Understanding** - Project overview and code tracing

## Important Design Decisions

This project uses MCP (Model Context Protocol) servers extensively for tool functionality. This provides:
- Standardized tool interface
- Access to existing MCP server ecosystem
- Better security through process isolation
- Easier maintenance and extensibility

**Minimal Codebase Philosophy**: Keep the codebase as minimal and readable as possible. Prefer leveraging existing libraries and tools (like LangChain for model providers and MCP for tools) over building custom implementations. Only add code when absolutely necessary for core functionality. Code should be simple, clear, and easy to understand - avoid complex abstractions when simpler solutions work.

See ARCHITECTURE.md for detailed design.
