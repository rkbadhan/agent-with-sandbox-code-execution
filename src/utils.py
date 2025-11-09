"""Utility functions for the sandboxed agent."""

import asyncio
import hashlib
import json
import logging
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from src.config import config

# Set up logging
logging.basicConfig(
    level=config.log_level,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)
console = Console()

T = TypeVar("T")


def setup_logging(name: str = __name__) -> logging.Logger:
    """Set up logging for a module."""
    logger = logging.getLogger(name)
    logger.setLevel(config.log_level)
    return logger


def retry_with_backoff(
    max_retries: int = 4,
    initial_delay: float = 2.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}"
                        )
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}"
                    )
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= exponential_base
            raise RuntimeError("Unreachable code")

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}"
                        )
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}"
                    )
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= exponential_base
            raise RuntimeError("Unreachable code")

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def calculate_hash(content: Union[str, bytes]) -> str:
    """Calculate SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def truncate_output(
    output: str, max_lines: int = 1000, max_chars: int = 100000
) -> str:
    """Truncate output to prevent excessive memory usage."""
    lines = output.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"\n... (truncated {len(lines) - max_lines} lines)")

    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"

    return result


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def parse_file_path(path: Union[str, Path]) -> Path:
    """Parse and validate file path."""
    if isinstance(path, str):
        path = Path(path)

    # Resolve to absolute path
    if not path.is_absolute():
        path = path.resolve()

    return path


def is_text_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is a text file."""
    text_extensions = {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".css",
        ".scss",
        ".sass",
        ".html",
        ".xml",
        ".svg",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".sql",
    }

    path = parse_file_path(file_path)
    return path.suffix.lower() in text_extensions


def print_table(
    title: str,
    headers: List[str],
    rows: List[List[str]],
    show_lines: bool = True,
) -> None:
    """Print a formatted table using rich."""
    table = Table(title=title, show_lines=show_lines)

    for header in headers:
        table.add_column(header, style="cyan")

    for row in rows:
        table.add_row(*row)

    console.print(table)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"




def extract_code_blocks(text: str, language: Optional[str] = None) -> List[str]:
    """Extract code blocks from markdown text."""
    import re

    if language:
        pattern = rf"```{language}\n(.*?)```"
    else:
        pattern = r"```(?:\w+)?\n(.*?)```"

    matches = re.findall(pattern, text, re.DOTALL)
    return matches


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely load JSON, returning default if parsing fails."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result




async def run_parallel(
    tasks: List[asyncio.Task[T]], max_concurrent: int = 10
) -> List[T]:
    """Run multiple async tasks in parallel with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_task(task: asyncio.Task[T]) -> T:
        async with semaphore:
            return await task

    return await asyncio.gather(*[bounded_task(task) for task in tasks])
