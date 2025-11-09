"""Git operations tool."""

import asyncio
from typing import Optional

from pydantic import Field

from src.tools.base import (
    BaseTool,
    ToolParameters,
    ToolResult,
)
from src.utils import logger


class GitParameters(ToolParameters):
    """Parameters for Git tool."""

    operation: str = Field(
        description="Git operation to perform (status, add, commit, push, pull, etc.)"
    )
    args: Optional[list[str]] = Field(
        default=None, description="Additional arguments for the git command"
    )
    message: Optional[str] = Field(
        default=None, description="Commit message (for commit operation)"
    )


class GitTool(BaseTool):
    """Tool for Git operations."""

    name = "Git"
    description = (
        "Performs git operations like status, add, commit, push, pull, etc. "
        "Supports all standard git commands with safety checks."
    )
    parameters_class = GitParameters

    def _validate_command(self, command: str) -> None:
        """
        Validate command for safety.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is invalid or dangerous
        """
        if not command or not command.startswith("git "):
            raise ValueError("Invalid git command")

        # Check for dangerous patterns
        dangerous_patterns = ["; ", "&&", "||", "|", ">", "<", "`", "$"]
        for pattern in dangerous_patterns:
            if pattern in command:
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

    def _format_command_output(self, stdout: str, stderr: str, return_code: int) -> str:
        """
        Format command output for display.

        Args:
            stdout: Standard output
            stderr: Standard error
            return_code: Command return code

        Returns:
            Formatted output string
        """
        output_parts = []

        if stdout:
            output_parts.append(stdout.strip())

        if stderr:
            if output_parts:
                output_parts.append("\n")
            output_parts.append(f"Error: {stderr.strip()}")

        if not output_parts:
            output_parts.append(f"Command completed with return code {return_code}")

        return "".join(output_parts)

    async def execute(
        self,
        operation: str,
        args: Optional[list[str]] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute git operation."""
        try:
            # Build git command
            cmd_parts = ["git", operation]

            if args:
                cmd_parts.extend(args)

            # Special handling for commit
            if operation == "commit" and message:
                cmd_parts.extend(["-m", message])

            command = " ".join(cmd_parts)

            # Validate command
            self._validate_command(command)

            logger.info(f"Executing git command: {command}")

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=60.0
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            return_code = process.returncode

            output = self._format_command_output(stdout_str, stderr_str, return_code)

            metadata = {
                "operation": operation,
                "command": command,
                "return_code": return_code,
            }

            success = return_code == 0

            if not success:
                logger.warning(f"Git command failed: {command}")

            return ToolResult(
                success=success,
                output=output,
                error=None if success else f"Git command failed with return code {return_code}",
                metadata=metadata,
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error="Git command timed out after 60s",
            )
        except Exception as e:
            logger.error(f"Error executing git command: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute git command: {str(e)}",
            )
