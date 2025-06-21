# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`yet-claude-code` is an alternative implementation of Claude Code that provides model flexibility. While Claude Code only works with Claude models, this project aims to deliver the same core features but with the ability to switch between different AI models (e.g., GPT-4, Gemini, local models, etc.).

The project uses modern Python packaging standards with `pyproject.toml` configuration.

## Development Setup

1. **Python Version**: This project uses Python 3.13.5 (specified in `.python-version`)
2. **Virtual Environment**: Already created at `.venv`
3. **Installation**: Run `pip install -e .` to install in editable mode

## Project Structure

```
src/yet_claude_code/   # Main package directory
├── __init__.py       # Package initialization
└── main.py          # Main module (currently empty)
tests/               # Test directory (currently empty)
```

## Current State

- This is a skeleton project with no implementation yet
- No test framework is configured
- No linting or formatting tools are set up
- No CI/CD pipelines exist
- Dependencies list in `pyproject.toml` is empty

## Common Development Tasks

Since the project lacks standard development tooling, you may need to:

1. **Add dependencies**: Update the `dependencies` list in `pyproject.toml`
2. **Set up testing**: Consider adding pytest as a dev dependency
3. **Add linting**: Consider tools like ruff, black, or flake8
4. **Implement features**: Start in `src/yet_claude_code/main.py`

## Key Features to Implement

To match Claude Code's functionality with model flexibility:

1. **Model Abstraction Layer**: Create interfaces that work with multiple AI providers
2. **MCP Integration**: Use MCP servers for tools instead of building from scratch
3. **CLI Interface**: Command-line interface for interacting with the AI
4. **Model Configuration**: Allow users to specify which model/provider to use
5. **Context Management**: Handle conversation history and file context efficiently

## Important Design Decision

This project uses MCP (Model Context Protocol) servers extensively for tool functionality. This provides:
- Standardized tool interface
- Access to existing MCP server ecosystem
- Better security through process isolation
- Easier maintenance and extensibility

See ARCHITECTURE.md for detailed design.