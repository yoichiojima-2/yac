# yac

yac (yet-another-claude) is an alternative implementation of Claude Code that provides model flexibility. While Claude Code only works with Claude models, this project delivers the same core features but with the ability to switch between different AI models.

## Features

- **Multi-Model Support**: Use OpenAI (GPT-4), Anthropic (Claude), Google (Gemini), or local models via Ollama
- **Provider Abstraction**: Clean interface for adding new AI providers
- **Streaming Support**: Real-time responses from AI models
- **Tool System**: MCP-based tool integration (coming soon)
- **Configuration**: Flexible configuration via YAML files
- **CLI Interface**: Simple command-line interface

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Use default provider (OpenAI)
ycc

# Use a specific provider
ycc --provider openai --model gpt-4

# Set up API key
export OPENAI_API_KEY=your-api-key
```

## Configuration

Create `~/.yet-claude-code/config.yaml`:

```yaml
provider: openai
model: gpt-4-turbo-preview

api_keys:
  openai: ${OPENAI_API_KEY}
  anthropic: ${ANTHROPIC_API_KEY}
  google: ${GOOGLE_API_KEY}

stream: true
```

## CLI Commands

- `/help` - Show available commands
- `/exit` - Exit the application
- `/clear` - Clear conversation history
- `/model` - Show or set the current model
- `/tokens` - Show token count

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design information.

## Status

This is an early-stage project. Core features implemented:
-  Provider abstraction layer
-  OpenAI provider
-  Basic CLI interface
- ó MCP integration (in progress)
- ó Additional providers (planned)
- ó Context management (planned)
