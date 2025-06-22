# MCP Servers for Yet Claude Code

This document describes the available MCP (Model Context Protocol) servers that can be used with Yet Claude Code to extend its capabilities.

## Default Servers (Always Available)

These servers are included by default and should work out of the box:

### 1. Filesystem
- **Purpose**: File and directory operations
- **Tools**: `read_file`, `write_file`, `edit_file`, `list_directory`, `create_directory`, `search_files`, etc.
- **Setup**: Automatically configured for current workspace
- **Usage**: Already active when you start Yet Claude Code

### 2. Fetch
- **Purpose**: Web content fetching and HTTP requests
- **Tools**: `fetch` - retrieve content from URLs
- **Setup**: Add with `/mcp add fetch stdio npx -y @kazuph/mcp-fetch`
- **Usage**: Ask the assistant to fetch web pages or make HTTP requests

### 3. Puppeteer
- **Purpose**: Web browser automation and interaction
- **Tools**: `puppeteer_navigate`, `puppeteer_screenshot`, `puppeteer_click`, `puppeteer_type`
- **Setup**: Add with `/mcp add puppeteer stdio npx -y @modelcontextprotocol/server-puppeteer`
- **Requirements**: Chrome/Chromium browser installed
- **Usage**: Ask the assistant to interact with websites, take screenshots, etc.

## Optional Servers (Require API Keys/Setup)

### 1. Brave Search
- **Purpose**: Web search capabilities
- **Tools**: `brave_search` - search the web using Brave Search API
- **Setup**:
  1. Get API key from [Brave Search API](https://api.search.brave.com/)
  2. Set environment variable: `export BRAVE_API_KEY=your_api_key`
  3. Restart Yet Claude Code
- **Usage**: Ask the assistant to search for information on the web

### 2. GitHub
- **Purpose**: GitHub repository and issue management
- **Tools**: `get_repo`, `list_repos`, `create_issue`, `get_issue`, `create_pull_request`
- **Setup**:
  1. Create GitHub Personal Access Token at https://github.com/settings/tokens
  2. Set environment variable: `export GITHUB_TOKEN=your_token`
  3. Restart Yet Claude Code
- **Usage**: Ask the assistant to interact with GitHub repositories

### 3. Slack
- **Purpose**: Slack workspace integration
- **Tools**: Slack messaging and channel management
- **Setup**:
  1. Create Slack Bot in your workspace
  2. Get Bot User OAuth Token
  3. Set environment variable: `export SLACK_BOT_TOKEN=xoxb-your-token`
  4. Restart Yet Claude Code
- **Usage**: Ask the assistant to send messages or manage Slack channels

## Additional Servers

### 1. Sequential Thinking
- **Purpose**: Enhanced reasoning capabilities for complex problems
- **Tools**: Structured thinking and problem decomposition
- **Setup**: Add with `/mcp add sequential-thinking stdio npx -y @modelcontextprotocol/server-sequential-thinking`
- **Usage**: Automatically improves the assistant's reasoning on complex tasks

### 2. SQLite
- **Purpose**: Database operations and SQL queries
- **Tools**: Database creation, querying, and management
- **Setup**: Add with `/mcp add sqlite stdio npx -y @modelcontextprotocol/server-sqlite`
- **Usage**: Ask the assistant to work with SQLite databases

### 3. Memory
- **Purpose**: Persistent memory across conversations
- **Tools**: `store_memory`, `retrieve_memory`, `search_memory`
- **Setup**: Add with `/mcp add memory stdio npx -y @modelcontextprotocol/server-memory`
- **Usage**: The assistant can remember information between sessions

### 4. Desktop Commander
- **Purpose**: Terminal command execution and process management
- **Tools**: `run_command`, `list_processes`, advanced file editing
- **Setup**: Add with `/mcp add desktop-commander stdio npx -y desktopcommandermcp`
- **Usage**: Ask the assistant to run terminal commands and manage processes

## Managing MCP Servers

### View Available Servers
```
/mcp available
```

### List Connected Servers
```
/mcp list
```

### View Tools from All Servers
```
/mcp tools
```

### View Tools from Specific Server
```
/mcp tools filesystem
```

### Add a Server Manually
```
/mcp add <name> stdio <command> [args...]
```

### Remove a Server
```
/mcp remove <name>
```

## Environment Variables

Set these environment variables in your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
# Brave Search API
export BRAVE_API_KEY="your_brave_search_api_key"

# GitHub Personal Access Token
export GITHUB_TOKEN="your_github_token"

# Slack Bot Token
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"

# AI Provider API Keys (choose one or more)
export OPENAI_API_KEY="your_openai_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export GOOGLE_API_KEY="your_google_api_key"

# AI Provider Selection
export YCC_PROVIDER="openai"  # or "anthropic" or "google"
export YCC_MODEL="gpt-4-turbo-preview"  # or specific model name
```

## Troubleshooting

### Server Connection Issues
1. Make sure Node.js and npm are installed
2. Check that the MCP server package is available: `npx -y <package-name> --help`
3. Verify API keys are set correctly: `echo $BRAVE_API_KEY`
4. Restart Yet Claude Code after setting environment variables

### Tool Execution Errors
1. Check server logs in the terminal output
2. Verify the tool arguments match the expected schema
3. Use `/mcp tools <server-name>` to see available tools and their descriptions

### Performance Issues
1. Consider disabling servers you don't need
2. Some servers (like Puppeteer) may be resource-intensive
3. Use `/mcp remove <name>` to disconnect unused servers

## Security Considerations

- **File Access**: The filesystem server has access to your specified directories
- **Terminal Access**: Desktop Commander can execute arbitrary commands
- **Network Access**: Web-based servers can make external requests
- **API Keys**: Store API keys securely and use minimal required permissions

Always review what tools you're giving the assistant access to, especially in sensitive environments.
