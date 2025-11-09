"""Search tools: Glob and Grep."""

import asyncio
import glob as glob_module
import re
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import Field

from src.tools.base import BaseTool, ToolParameters, ToolResult
from src.utils import logger, truncate_output


class GlobParameters(ToolParameters):
    """Parameters for Glob tool."""

    pattern: str = Field(description="Glob pattern to match files (e.g., **/*.py)")
    path: Optional[str] = Field(
        default=None, description="Directory to search in (default: current directory)"
    )


class GlobTool(BaseTool):
    """Tool for finding files by pattern."""

    name = "Glob"
    description = (
        "Fast file pattern matching using glob patterns. "
        "Supports ** for recursive matching. "
        "Returns list of matching file paths sorted by modification time."
    )
    parameters_class = GlobParameters

    async def execute(
        self, pattern: str, path: Optional[str] = None, **kwargs
    ) -> ToolResult:
        """Find files matching pattern."""
        try:
            search_path = Path(path) if path else Path.cwd()

            if not search_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Directory not found: {search_path}",
                )

            # Use glob to find matching files
            full_pattern = str(search_path / pattern)
            matches = glob_module.glob(full_pattern, recursive=True)

            # Filter out directories, keep only files
            file_matches = [m for m in matches if Path(m).is_file()]

            # Sort by modification time (most recent first)
            file_matches.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)

            if not file_matches:
                output = f"No files found matching pattern: {pattern}"
            else:
                output = "\n".join(file_matches)

            metadata = {
                "pattern": pattern,
                "search_path": str(search_path),
                "match_count": len(file_matches),
            }

            logger.info(f"Found {len(file_matches)} files matching {pattern}")

            return ToolResult(success=True, output=output, metadata=metadata)

        except Exception as e:
            logger.error(f"Error in glob search: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Glob search failed: {str(e)}",
            )


class GrepParameters(ToolParameters):
    """Parameters for Grep tool."""

    pattern: str = Field(description="Regular expression pattern to search for")
    path: Optional[str] = Field(
        default=None, description="File or directory to search in"
    )
    glob: Optional[str] = Field(
        default=None, description="Glob pattern to filter files (e.g., *.py)"
    )
    type: Optional[str] = Field(
        default=None, description="File type filter (e.g., py, js, rust)"
    )
    output_mode: str = Field(
        default="files_with_matches",
        description="Output mode: content, files_with_matches, or count",
    )
    case_insensitive: bool = Field(default=False, description="Case insensitive search")
    context_lines: Optional[int] = Field(
        default=None, description="Number of context lines before and after match"
    )
    multiline: bool = Field(
        default=False, description="Enable multiline matching"
    )


class GrepTool(BaseTool):
    """Tool for searching file contents using ripgrep."""

    name = "Grep"
    description = (
        "Powerful search tool using ripgrep for fast content search. "
        "Supports regex, file type filtering, and multiple output modes. "
        "Use for finding code patterns across files."
    )
    parameters_class = GrepParameters

    async def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        type: Optional[str] = None,
        output_mode: str = "files_with_matches",
        case_insensitive: bool = False,
        context_lines: Optional[int] = None,
        multiline: bool = False,
        **kwargs,
    ) -> ToolResult:
        """Search for pattern in files using ripgrep."""
        try:
            search_path = path if path else "."

            # Build ripgrep command
            cmd = ["rg"]

            # Add output mode flags
            if output_mode == "files_with_matches":
                cmd.append("-l")  # List files with matches
            elif output_mode == "count":
                cmd.append("-c")  # Count matches per file

            # Add pattern matching flags
            if case_insensitive:
                cmd.append("-i")

            if multiline:
                cmd.extend(["-U", "--multiline-dotall"])

            # Add context lines
            if context_lines is not None and output_mode == "content":
                cmd.extend(["-C", str(context_lines)])

            # Add file filtering
            if glob:
                cmd.extend(["--glob", glob])

            if type:
                cmd.extend(["--type", type])

            # Add pattern and path
            cmd.extend([pattern, search_path])

            logger.info(f"Executing ripgrep: {' '.join(cmd)}")

            # Execute ripgrep
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            return_code = process.returncode

            # ripgrep returns 1 if no matches found (not an error)
            if return_code == 0:
                output = truncate_output(stdout_str)
                match_count = len(stdout_str.strip().split("\n")) if stdout_str.strip() else 0
            elif return_code == 1:
                output = f"No matches found for pattern: {pattern}"
                match_count = 0
            else:
                # Actual error
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Ripgrep error: {stderr_str}",
                )

            metadata = {
                "pattern": pattern,
                "search_path": search_path,
                "output_mode": output_mode,
                "match_count": match_count,
            }

            logger.info(f"Found {match_count} matches for pattern: {pattern}")

            return ToolResult(success=True, output=output, metadata=metadata)

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error="ripgrep (rg) not found. Please install ripgrep.",
            )
        except Exception as e:
            logger.error(f"Error in grep search: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Grep search failed: {str(e)}",
            )
