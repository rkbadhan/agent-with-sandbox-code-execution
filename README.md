# Sandboxed LangGraph Agent

A production-ready implementation of a sandboxed code execution agent using LangGraph, replicating Claude Code's functionality.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface / API                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Core                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Planner   │→ │   Executor   │→ │    Validator     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        Tool Layer                            │
│  Read | Write | Edit | Bash | Grep | Glob | WebFetch        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Docker Sandbox Manager                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │  Session   │  │  Network   │  │   Filesystem       │   │
│  │  Manager   │  │  Proxy     │  │   Boundaries       │   │
│  └────────────┘  └────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│            Isolated Docker Container (Ubuntu 24)             │
│               Ephemeral • Restricted • Secure                │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 🔒 Sandboxed Execution
- **Docker-based isolation**: Each session runs in a separate container
- **Ephemeral environments**: Containers are destroyed after session ends
- **Resource limits**: CPU, memory, and disk quotas
- **Network restrictions**: Whitelist-based egress filtering

### 🛠️ Comprehensive Tool System
- **File Operations**: Read, Write, Edit with safety checks
- **Command Execution**: Bash with timeout and output streaming
- **Code Search**: Grep (regex), Glob (patterns)
- **Web Access**: WebFetch and WebSearch through proxy
- **Git Operations**: Full git workflow support

### 🤖 LangGraph Agent
- **State management**: Conversation history and context
- **Planning & execution**: Break down complex tasks
- **Error recovery**: Retry logic and fallback strategies
- **Parallel execution**: Concurrent tool calls when possible

### 🔐 Security Model
- **Filesystem boundaries**: Read-only mounts for sensitive data
- **Command validation**: Prevent injection attacks
- **Network filtering**: Allow only trusted domains
- **Secret detection**: Prevent committing credentials

## Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Anthropic API key (or other LLM provider)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd agent-with-file-system

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Build the sandbox Docker image
docker compose build

# Run the agent
python -m src.main
```

### Basic Usage

```python
from src.agent import SandboxAgent

# Initialize the agent
agent = SandboxAgent(
    model="claude-sonnet-4-5-20250929",
    session_timeout=3600  # 1 hour
)

# Run a task
result = await agent.run(
    "Create a Python script that analyzes log files and finds error patterns"
)

print(result)
```

## Project Structure

```
agent-with-file-system/
├── src/
│   ├── agent/                 # LangGraph agent implementation
│   │   ├── __init__.py
│   │   ├── graph.py          # LangGraph state machine
│   │   ├── nodes.py          # Agent nodes (planner, executor, etc.)
│   │   └── state.py          # Agent state definition
│   ├── tools/                 # Tool implementations
│   │   ├── __init__.py
│   │   ├── base.py           # Base tool class
│   │   ├── file_ops.py       # Read, Write, Edit
│   │   ├── bash.py           # Bash command execution
│   │   ├── search.py         # Grep, Glob
│   │   ├── web.py            # WebFetch, WebSearch
│   │   └── git.py            # Git operations
│   ├── sandbox/               # Docker sandbox management
│   │   ├── __init__.py
│   │   ├── manager.py        # Container lifecycle
│   │   ├── executor.py       # Execute tools in container
│   │   └── network.py        # Network proxy and filtering
│   ├── security/              # Security components
│   │   ├── __init__.py
│   │   ├── validator.py      # Input validation
│   │   ├── boundaries.py     # Filesystem boundaries
│   │   └── secrets.py        # Secret detection
│   ├── config.py              # Configuration
│   ├── main.py               # Entry point
│   └── utils.py              # Utilities
├── docker/
│   ├── Dockerfile            # Sandbox container image
│   ├── docker-compose.yml    # Container orchestration
│   └── entrypoint.sh         # Container startup script
├── tests/
│   ├── test_agent.py
│   ├── test_tools.py
│   ├── test_sandbox.py
│   └── test_security.py
├── examples/
│   ├── basic_usage.py
│   ├── file_operations.py
│   └── git_workflow.py
├── docs/
│   ├── architecture.md
│   ├── tools.md
│   └── security.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Configuration

### Environment Variables

```bash
# LLM Configuration
ANTHROPIC_API_KEY=your_api_key_here
MODEL_NAME=claude-sonnet-4-5-20250929

# Sandbox Configuration
SANDBOX_TIMEOUT=3600           # Session timeout in seconds
SANDBOX_CPU_LIMIT=2            # CPU cores
SANDBOX_MEMORY_LIMIT=4g        # Memory limit
SANDBOX_DISK_LIMIT=10g         # Disk space

# Network Configuration
ALLOWED_DOMAINS=github.com,npmjs.com,pypi.org,ubuntu.com
NETWORK_PROXY_PORT=8888

# Security Configuration
ENABLE_SECRET_DETECTION=true
READ_ONLY_PATHS=/mnt/user-data,/mnt/skills
MAX_FILE_SIZE=100MB
```

## Tool Documentation

### File Operations

```python
# Read a file
result = await agent.use_tool("Read", {
    "file_path": "/home/user/project/main.py",
    "offset": 0,
    "limit": 100
})

# Write a file
await agent.use_tool("Write", {
    "file_path": "/home/user/project/new_file.py",
    "content": "print('Hello, World!')"
})

# Edit a file
await agent.use_tool("Edit", {
    "file_path": "/home/user/project/main.py",
    "old_string": "def old_function():",
    "new_string": "def new_function():"
})
```

### Command Execution

```python
# Run a bash command
result = await agent.use_tool("Bash", {
    "command": "pytest tests/ -v",
    "timeout": 60000,  # 60 seconds
    "description": "Run test suite"
})

# Run in background
result = await agent.use_tool("Bash", {
    "command": "npm run dev",
    "run_in_background": True
})
```

### Code Search

```python
# Search by file pattern
files = await agent.use_tool("Glob", {
    "pattern": "**/*.py",
    "path": "/home/user/project"
})

# Search by content
matches = await agent.use_tool("Grep", {
    "pattern": "def.*main",
    "path": "/home/user/project",
    "output_mode": "content",
    "type": "py"
})
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_agent.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Building Docker Image

```bash
# Build the sandbox image
docker build -t sandbox-agent:latest -f docker/Dockerfile .

# Test the image
docker run --rm -it sandbox-agent:latest /bin/bash
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Security Considerations

### Threat Model

1. **Untrusted Code Execution**: User-provided code runs in isolated container
2. **Network Attacks**: Restricted egress, whitelist-based filtering
3. **Data Exfiltration**: Read-only mounts, no persistent storage
4. **Resource Exhaustion**: CPU, memory, disk limits enforced
5. **Container Escape**: Docker isolation, non-root user

### Best Practices

- Always validate user inputs
- Use read-only mounts for sensitive data
- Implement rate limiting for API calls
- Monitor resource usage
- Rotate containers regularly
- Keep dependencies updated

## Performance Optimization

### Parallel Tool Execution

The agent automatically identifies independent tool calls and executes them in parallel:

```python
# These will run concurrently
results = await agent.run_parallel([
    ("Read", {"file_path": "/home/user/file1.py"}),
    ("Read", {"file_path": "/home/user/file2.py"}),
    ("Bash", {"command": "git status"})
])
```

### Container Pooling

Pre-warm containers for faster session startup:

```python
from src.sandbox import ContainerPool

pool = ContainerPool(size=5)
await pool.warm_up()
```

## Roadmap

- [ ] Support for additional LLM providers (OpenAI, Cohere, etc.)
- [ ] Web UI for interactive sessions
- [ ] Kubernetes deployment support
- [ ] Enhanced monitoring and logging
- [ ] Plugin system for custom tools
- [ ] Multi-language REPL support
- [ ] Collaborative sessions

## License

MIT License - see LICENSE file for details

## Acknowledgments

Inspired by Claude Code's sandboxed execution environment and LangGraph's agent framework.
