# yac

yac (yet-another-claude) is an alternative take on Claude Code with model flexibility. While Claude Code only works with Claude models, yac delivers the same core idea — an agentic coding assistant in your terminal — with the ability to switch between AI providers.

## Features

- **Multi-Provider Support**: OpenAI, Anthropic (Claude), or Google (Gemini) via LangChain
- **Tool System**: MCP-based tool integration — default servers (filesystem, git, fetch, terminal, puppeteer, sequential-thinking) are set up automatically and their tools are bound to the model
- **Agentic Loop**: the model can call tools, read the results, and keep going until the task is done
- **Runtime MCP Management**: add, remove, and inspect MCP servers from within the CLI

## Installation

```bash
pip install -e .
```

Default MCP servers are launched with `npx`, so Node.js is required for tool support (chat works without it).

## Quick Start

```bash
# Set up an API key for your provider
export OPENAI_API_KEY=your-api-key

# Use the default provider (OpenAI)
yac

# Or pick a provider/model explicitly
yac --provider anthropic --model claude-sonnet-5
```

## Configuration

Provider selection is via environment variables:

| Variable | Meaning | Default |
| --- | --- | --- |
| `YAC_PROVIDER` | `openai`, `anthropic`, or `google` | `openai` |
| `YAC_MODEL` | Model name for the chosen provider | `gpt-5.6-terra` / `claude-sonnet-5` / `gemini-3.5-flash` |
| `YAC_STREAM` | Enable streaming on the LLM client | `true` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` | Provider API keys | — |
| `BRAVE_API_KEY`, `GITHUB_TOKEN`, `SLACK_BOT_TOKEN` | Optional; enable the Brave Search / GitHub / Slack MCP servers | — |

MCP server configuration persists in `~/.yac/config.json`.

## CLI Commands

- `/help` — Show available commands
- `/clear` — Clear conversation history
- `/exit` (also `/quit`, `/q`) — Exit
- `/mcp add|remove|list|tools|available` — Manage MCP servers at runtime

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/
```

## Status

This is an early-stage project. Current state:

- Provider abstraction via LangChain (OpenAI, Anthropic, Google) — implemented
- MCP integration with a default server set and runtime `/mcp` management — implemented
- Interactive CLI — implemented
- Context management — planned
- Additional providers (e.g. local models) — planned
