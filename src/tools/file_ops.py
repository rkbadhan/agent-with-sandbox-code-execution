"""File operation tools: Read, Write, Edit."""

import aiofiles
from pathlib import Path
from typing import Optional

from pydantic import Field

from src.config import config
from src.tools.base import (
    BaseTool,
    ToolParameters,
    ToolResult,
)
from src.utils import logger


class ReadParameters(ToolParameters):
    """Parameters for Read tool."""

    file_path: str = Field(description="Absolute path to the file to read")
    offset: Optional[int] = Field(
        default=None, description="Line number to start reading from (0-indexed)"
    )
    limit: Optional[int] = Field(
        default=None, description="Number of lines to read"
    )


class ReadTool(BaseTool):
    """Tool for reading files."""

    name = "Read"
    description = (
        "Reads a file from the filesystem. Supports offset and limit for large files. "
        "Returns content with line numbers."
    )
    parameters_class = ReadParameters

    async def execute(
        self,
        file_path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """Read file content."""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {file_path}",
                )

            if not path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path is not a file: {file_path}",
                )

            # Check file size
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > config.max_file_size_mb:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File size ({size_mb:.2f} MB) exceeds maximum allowed size ({config.max_file_size_mb} MB)",
                )

            # Read file
            async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = await f.readlines()

            # Apply offset and limit
            start = offset if offset is not None else 0
            end = start + limit if limit is not None else len(lines)
            lines = lines[start:end]

            # Format with line numbers (1-indexed)
            numbered_lines = [
                f"{start + i + 1:6d}\t{line.rstrip()}"
                for i, line in enumerate(lines)
            ]

            output = "\n".join(numbered_lines)

            metadata = {
                "file_path": str(path),
                "total_lines": len(lines),
                "offset": start,
                "limit": limit,
            }

            logger.debug(f"Read {len(lines)} lines from {file_path}")

            return ToolResult(success=True, output=output, metadata=metadata)

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to read file: {str(e)}",
            )


class WriteParameters(ToolParameters):
    """Parameters for Write tool."""

    file_path: str = Field(description="Absolute path to the file to write")
    content: str = Field(description="Content to write to the file")


class WriteTool(BaseTool):
    """Tool for writing files."""

    name = "Write"
    description = (
        "Writes content to a file, creating it if it doesn't exist or overwriting if it does. "
        "Cannot write to read-only paths."
    )
    parameters_class = WriteParameters

    async def execute(self, file_path: str, content: str, **kwargs) -> ToolResult:
        """Write content to file."""
        try:
            path = Path(file_path)

            # Check if path is read-only
            resolved_path = path.resolve()
            for ro_path in config.read_only_paths:
                ro_path_resolved = Path(ro_path).resolve()
                if str(resolved_path).startswith(str(ro_path_resolved)):
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Cannot write to read-only path: {file_path}",
                    )

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)

            file_size = path.stat().st_size
            line_count = len(content.split("\n"))

            metadata = {
                "file_path": str(path),
                "size_bytes": file_size,
                "lines": line_count,
            }

            logger.debug(
                f"Wrote {line_count} lines ({file_size} bytes) to {file_path}"
            )

            return ToolResult(
                success=True,
                output=f"Successfully wrote to {file_path}",
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to write file: {str(e)}",
            )


class EditParameters(ToolParameters):
    """Parameters for Edit tool."""

    file_path: str = Field(description="Absolute path to the file to edit")
    old_string: str = Field(description="String to replace")
    new_string: str = Field(description="String to replace with")
    replace_all: bool = Field(
        default=False, description="Replace all occurrences (default: False)"
    )


class EditTool(BaseTool):
    """Tool for editing files with string replacement."""

    name = "Edit"
    description = (
        "Performs exact string replacement in files. "
        "The old_string must be unique unless replace_all is True. "
        "Must read the file before editing."
    )
    parameters_class = EditParameters

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **kwargs,
    ) -> ToolResult:
        """Edit file by replacing strings."""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {file_path}",
                )

            # Check if path is read-only
            resolved_path = path.resolve()
            for ro_path in config.read_only_paths:
                ro_path_resolved = Path(ro_path).resolve()
                if str(resolved_path).startswith(str(ro_path_resolved)):
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Cannot write to read-only path: {file_path}",
                    )

            # Read current content
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()

            # Check if old_string exists
            if old_string not in content:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"String not found in file: {old_string[:100]}...",
                )

            # Check uniqueness if not replace_all
            if not replace_all and content.count(old_string) > 1:
                return ToolResult(
                    success=False,
                    output="",
                    error=(
                        f"String appears {content.count(old_string)} times. "
                        "Use replace_all=True or provide more context."
                    ),
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacement_count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacement_count = 1

            # Write updated content
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(new_content)

            metadata = {
                "file_path": str(path),
                "replacements": replacement_count,
                "old_length": len(old_string),
                "new_length": len(new_string),
            }

            logger.debug(
                f"Made {replacement_count} replacement(s) in {file_path}"
            )

            return ToolResult(
                success=True,
                output=f"Successfully replaced {replacement_count} occurrence(s)",
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Error editing file {file_path}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to edit file: {str(e)}",
            )
