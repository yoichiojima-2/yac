#!/bin/bash

# Yet Claude Code UI Startup Script
# This script ensures the Python virtual environment is activated and starts the React Ink UI

set -e

echo "🚀 Starting Yet Claude Code UI..."

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Run this script from the yet-claude-code project root"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Python virtual environment not found. Please run 'python -m venv .venv' first"
    exit 1
fi

# Activate Python virtual environment
echo "🐍 Activating Python virtual environment..."
source .venv/bin/activate

# Check if yet-claude-code is installed
if ! python -c "import yet_claude_code" 2>/dev/null; then
    echo "📦 Installing yet-claude-code in development mode..."
    pip install -e .
fi

# Check if Node.js dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Start the React Ink UI
echo "🎨 Starting React Ink UI..."
npm run ui