"""Tools for the sandboxed agent."""

from src.tools.base import BaseTool, ToolResult
from src.tools.bash import BashTool
from src.tools.file_ops import EditTool, ReadTool, WriteTool
from src.tools.git import GitTool
from src.tools.search import GlobTool, GrepTool
from src.tools.web import WebFetchTool, WebSearchTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "BashTool",
    "GlobTool",
    "GrepTool",
    "WebFetchTool",
    "WebSearchTool",
    "GitTool",
]


# Registry of all available tools
TOOL_REGISTRY = {
    "Read": ReadTool,
    "Write": WriteTool,
    "Edit": EditTool,
    "Bash": BashTool,
    "Glob": GlobTool,
    "Grep": GrepTool,
    "WebFetch": WebFetchTool,
    "WebSearch": WebSearchTool,
    "Git": GitTool,
}


def get_tool(name: str) -> type[BaseTool]:
    """Get a tool class by name."""
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}")
    return TOOL_REGISTRY[name]


def list_tools() -> list[str]:
    """List all available tools."""
    return list(TOOL_REGISTRY.keys())
