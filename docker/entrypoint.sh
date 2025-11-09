#!/bin/bash
set -e

# Entrypoint script for sandbox container

echo "🚀 Sandbox container starting..."
echo "📁 Working directory: $(pwd)"
echo "👤 User: $(whoami)"
echo "🐍 Python version: $(python --version)"
echo "📦 Node version: $(node --version)"
echo "🔍 Ripgrep version: $(rg --version | head -n 1)"

# Activate virtual environment
source /home/user/.venv/bin/activate

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Configure git if not already configured
if ! git config --global user.name > /dev/null 2>&1; then
    git config --global user.name "Sandbox User"
    git config --global user.email "sandbox@example.com"
fi

# Initialize workspace if it's empty
if [ ! -d ".git" ] && [ -z "$(ls -A)" ]; then
    echo "📝 Initializing empty workspace..."
    git init
fi

echo "✅ Sandbox ready!"
echo ""

# Execute the command passed to the container
exec "$@"
