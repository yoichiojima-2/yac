# Architecture Overview

> **Note**: This architecture heavily leverages [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) servers for tool functionality, providing a standardized way to extend capabilities.

## Design Goals

1. **Model Agnostic**: Support any LLM provider (OpenAI, Anthropic, Google, local models)
2. **Feature Parity**: Match Claude Code's core functionality
3. **Extensible**: Easy to add new providers and tools
4. **Performant**: Efficient context management and streaming responses
5. **User Friendly**: Simple CLI interface with good defaults

## Core Components

### Provider Abstraction Layer

All LLM providers implement a common interface:

```python
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, messages: List[Message], tools: List[Tool]) -> Response:
        pass
    
    @abstractmethod
    async def stream(self, messages: List[Message], tools: List[Tool]) -> AsyncIterator[StreamChunk]:
        pass
```

### Tool System (MCP-based)

Tools are primarily provided by MCP servers, with a thin wrapper for built-in tools:

```python
# MCP Client integration
class MCPClient:
    async def connect(self, server_config: dict) -> MCPConnection:
        pass
    
    async def list_tools(self) -> List[MCPTool]:
        pass
    
    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        pass

# Wrapper for built-in tools not available via MCP
class BuiltinTool(ABC):
    name: str
    description: str
    parameters: JSONSchema
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
```

### Message Flow

```
User Input → CLI → Session Manager → Provider → MCP Client → MCP Servers → Response
                         ↑                         ↓
                         └─── Context Manager ←────┘
```

### Directory Structure

```
src/yet_claude_code/
├── providers/          # LLM provider implementations
│   ├── __init__.py
│   ├── base.py        # Abstract base provider
│   ├── openai.py      # OpenAI implementation
│   ├── anthropic.py   # Anthropic implementation
│   ├── google.py      # Google (Gemini) implementation
│   ├── ollama.py      # Local models via Ollama
│   └── registry.py    # Provider discovery and registration
│
├── mcp/               # MCP integration
│   ├── __init__.py
│   ├── client.py      # MCP client implementation
│   ├── server.py      # MCP server management
│   ├── transport.py   # Transport layer (stdio, SSE, etc.)
│   └── registry.py    # MCP server discovery
│
├── tools/             # Built-in tools (minimal, for core functionality)
│   ├── __init__.py
│   ├── base.py        # Abstract base tool
│   ├── builtin.py     # Essential built-in tools
│   └── registry.py    # Tool discovery and registration
│
├── core/              # Core engine components
│   ├── __init__.py
│   ├── conversation.py # Conversation state management
│   ├── context.py     # Context window optimization
│   ├── executor.py    # Tool execution orchestration
│   ├── formatter.py   # Message/response formatting
│   └── session.py     # Session lifecycle management
│
├── cli/               # Command-line interface
│   ├── __init__.py
│   ├── app.py         # Main CLI application
│   ├── commands.py    # CLI command definitions
│   ├── config.py      # Configuration management
│   └── display.py     # Terminal display utilities
│
├── models/            # Data models
│   ├── __init__.py
│   ├── message.py     # Message types
│   ├── tool.py        # Tool-related models
│   └── provider.py    # Provider-related models
│
├── utils/             # Utility functions
│   ├── __init__.py
│   ├── streaming.py   # Streaming helpers
│   ├── validation.py  # Input validation
│   └── logging.py     # Logging configuration
│
└── main.py            # Application entry point
```

## Configuration

Users can configure the application via:

1. **Config File**: `~/.yet-claude-code/config.yaml`
2. **Environment Variables**: `YCC_PROVIDER`, `YCC_MODEL`, etc.
3. **CLI Arguments**: `--provider openai --model gpt-4`

Example configuration:

```yaml
# Default provider and model
provider: openai
model: gpt-4-turbo-preview

# API credentials (can use env vars)
api_keys:
  openai: ${OPENAI_API_KEY}
  anthropic: ${ANTHROPIC_API_KEY}
  google: ${GOOGLE_API_KEY}

# MCP Servers configuration
mcp_servers:
  # Filesystem operations
  filesystem:
    command: "npx"
    args: ["@modelcontextprotocol/server-filesystem", "/"]
    
  # GitHub integration
  github:
    command: "npx"
    args: ["@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      
  # Web search
  brave-search:
    command: "npx"
    args: ["@modelcontextprotocol/server-brave-search"]
    env:
      BRAVE_API_KEY: ${BRAVE_API_KEY}
      
  # Git operations
  git:
    command: "npx"
    args: ["@modelcontextprotocol/server-git"]
    
  # Memory/knowledge graph
  memory:
    command: "npx"
    args: ["@modelcontextprotocol/server-memory"]
    
  # Custom MCP server example
  my-tools:
    command: "python"
    args: ["-m", "my_mcp_server"]
    
# Built-in tools (only used if no MCP equivalent)
tools:
  builtin:
    - conversation_history
    - context_info
    
# Context management
context:
  max_tokens: 128000
  preserve_ratio: 0.8    # Keep 80% of context between turns
  
# Display preferences
display:
  syntax_highlighting: true
  markdown_rendering: true
  max_output_lines: 1000
```

## Key Features

### 1. MCP Integration
- **Standardized Tools**: Use any MCP server for tools
- **Dynamic Discovery**: Auto-discover available tools from MCP servers
- **Process Management**: Automatic MCP server lifecycle management
- **Transport Support**: stdio, SSE, and other MCP transports

### 2. Provider Flexibility
- Seamless switching between providers
- Provider-specific optimizations
- Fallback mechanisms

### 3. Tool Ecosystem
- **MCP Servers**: Primary tool source (filesystem, git, github, web, etc.)
- **Built-in Tools**: Minimal set for core functionality
- **Tool Composition**: Combine multiple MCP servers
- **Custom Servers**: Easy to add custom MCP servers

### 4. Context Optimization
- Smart truncation
- Token counting per provider
- Context compression
- MCP resource management

### 5. Streaming Support
- Real-time responses
- Progress indicators
- Partial result handling
- MCP streaming protocol support

### 6. Session Management
- Conversation persistence
- Project context via MCP
- Resume capabilities
- Multi-server coordination

## MCP Server Examples

### Official MCP Servers to Use:
- `@modelcontextprotocol/server-filesystem` - File operations
- `@modelcontextprotocol/server-git` - Git operations
- `@modelcontextprotocol/server-github` - GitHub API
- `@modelcontextprotocol/server-gitlab` - GitLab API
- `@modelcontextprotocol/server-brave-search` - Web search
- `@modelcontextprotocol/server-memory` - Persistent memory
- `@modelcontextprotocol/server-postgres` - Database access
- `@modelcontextprotocol/server-sqlite` - SQLite operations

### Benefits of MCP:
1. **Standardization**: Common protocol for all tools
2. **Security**: Process isolation for each server
3. **Extensibility**: Easy to add new capabilities
4. **Interoperability**: Tools work across different AI systems
5. **Community**: Growing ecosystem of MCP servers

## Extension Points

1. **Custom Providers**: Implement `BaseProvider` for new LLMs
2. **Custom MCP Servers**: Create new MCP servers for specialized tools
3. **Transport Layers**: Add new MCP transport mechanisms
4. **Middleware**: Hook into message flow for custom processing
5. **Formatters**: Custom output formatting options