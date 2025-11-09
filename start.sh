#!/bin/bash

# Startup script for Sandboxed LangGraph Agent with Azure OpenAI support
# Works on Linux and macOS

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Main script
print_header "Sandboxed LangGraph Agent - Startup Script"

# Check Python version
echo ""
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
REQUIRED_VERSION="3.11"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi
print_success "Python $PYTHON_VERSION detected"

# Check Docker
echo ""
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker ps &> /dev/null; then
    print_error "Docker is not running. Please start Docker."
    exit 1
fi
print_success "Docker is running"

# Check for uv package manager
echo ""
echo "Checking for uv package manager..."
if ! command -v uv &> /dev/null; then
    print_warning "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1

    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        print_error "Failed to install uv. Please install manually: https://github.com/astral-sh/uv"
        exit 1
    fi
    print_success "uv installed"
else
    print_success "uv is available"
fi

# Create virtual environment if it doesn't exist
echo ""
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv venv --python python3
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Install dependencies using uv
echo ""
echo "Installing dependencies with uv (this is much faster than pip)..."
uv pip install -r requirements.txt
print_success "Dependencies installed"

# Setup .env file
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    print_warning ".env file created. Please configure your API keys!"
    echo ""
    echo "To use Azure OpenAI, edit .env and set:"
    echo "  - LLM_PROVIDER=azure"
    echo "  - AZURE_OPENAI_API_KEY=your_api_key"
    echo "  - AZURE_OPENAI_ENDPOINT=your_endpoint"
    echo "  - AZURE_OPENAI_DEPLOYMENT=your_deployment_name"
    echo ""
    read -p "Press Enter to open .env file in default editor (or Ctrl+C to skip)..."
    ${EDITOR:-nano} .env
else
    print_success ".env file already exists"
fi

# Check LLM provider configuration
echo ""
echo "Checking LLM configuration..."
if [ -f ".env" ]; then
    source .env

    if [ "$LLM_PROVIDER" = "azure" ]; then
        print_success "LLM Provider: Azure OpenAI"

        # Validate Azure config
        if [ -z "$AZURE_OPENAI_API_KEY" ] || [ "$AZURE_OPENAI_API_KEY" = "your_azure_openai_api_key_here" ]; then
            print_error "AZURE_OPENAI_API_KEY is not set in .env file"
            exit 1
        fi

        if [ -z "$AZURE_OPENAI_ENDPOINT" ] || [ "$AZURE_OPENAI_ENDPOINT" = "https://your-resource-name.openai.azure.com/" ]; then
            print_error "AZURE_OPENAI_ENDPOINT is not set in .env file"
            exit 1
        fi

        if [ -z "$AZURE_OPENAI_DEPLOYMENT" ] || [ "$AZURE_OPENAI_DEPLOYMENT" = "your_deployment_name" ]; then
            print_error "AZURE_OPENAI_DEPLOYMENT is not set in .env file"
            exit 1
        fi

        print_success "Azure OpenAI configuration validated"

    elif [ "$LLM_PROVIDER" = "anthropic" ]; then
        print_success "LLM Provider: Anthropic Claude"

        if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
            print_error "ANTHROPIC_API_KEY is not set in .env file"
            exit 1
        fi

        print_success "Anthropic configuration validated"
    else
        print_warning "Unknown LLM_PROVIDER: $LLM_PROVIDER (defaulting to anthropic)"
    fi
fi

# Build Docker image
echo ""
echo "Checking Docker image..."
if ! docker image inspect sandbox-agent:latest &> /dev/null; then
    echo "Building Docker image (this may take a few minutes)..."
    docker compose -f docker/docker-compose.yml build
    print_success "Docker image built"
else
    print_success "Docker image already exists"
    read -p "Rebuild Docker image? (y/N): " rebuild
    if [ "$rebuild" = "y" ] || [ "$rebuild" = "Y" ]; then
        docker compose -f docker/docker-compose.yml build
        print_success "Docker image rebuilt"
    fi
fi

# Run test
echo ""
print_header "Running Test Task"
echo ""
echo "Running a simple test task..."
echo ""

python3 -m src.main run "Print 'Hello from Azure OpenAI!' to a file called test.txt"

echo ""
print_success "Test completed!"

echo ""
print_header "Setup Complete!"
echo ""
echo "Your sandbox agent is ready to use with Azure OpenAI!"
echo ""
echo "Usage examples:"
echo "  python3 -m src.main run \"your task here\""
echo "  python3 -m src.main info"
echo "  python3 -m src.main status"
echo "  python3 -m src.main example hello"
echo ""
echo "To switch between Anthropic and Azure OpenAI:"
echo "  Edit .env and change LLM_PROVIDER=azure or LLM_PROVIDER=anthropic"
echo ""
