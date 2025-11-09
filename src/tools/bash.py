"""Bash command execution tool."""

import asyncio
import shlex
from typing import Optional

from pydantic import Field

from src.tools.base import (
    BaseTool,
    ToolParameters,
    ToolResult,
)
from src.utils import logger, truncate_output


class BashParameters(ToolParameters):
    """Parameters for Bash tool."""

    command: str = Field(description="The shell command to execute")
    timeout: Optional[int] = Field(
        default=120000, description="Timeout in milliseconds (default: 120000 = 2 minutes)"
    )
    description: Optional[str] = Field(
        default=None, description="Description of what the command does"
    )
    run_in_background: bool = Field(
        default=False, description="Run command in background"
    )


class BashTool(BaseTool):
    """Tool for executing bash commands."""

    name = "Bash"
    description = (
        "Executes shell commands in the sandbox environment with timeout support. "
        "Commands run in a persistent shell session. "
        "Use run_in_background=True for long-running commands."
    )
    parameters_class = BashParameters

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        description: Optional[str] = None,
        run_in_background: bool = False,
        **kwargs,
    ) -> ToolResult:
        """Execute bash command."""
        try:
            # Validate command
            from src.security.validator import InputValidator
            from src.config import config

            validator = InputValidator(enabled=config.enable_command_validation)
            validator.validate_command(command)

            # Convert timeout from milliseconds to seconds
            timeout_sec = (timeout / 1000.0) if timeout else 120.0

            logger.info(
                f"Executing command{f' ({description})' if description else ''}: {command}"
            )

            if run_in_background:
                # Start process in background
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE,
                )

                metadata = {
                    "command": command,
                    "pid": process.pid,
                    "background": True,
                }

                return ToolResult(
                    success=True,
                    output=f"Started background process with PID {process.pid}",
                    metadata=metadata,
                )

            else:
                # Execute command with timeout
                try:
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        stdin=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=timeout_sec
                    )

                    stdout_str = stdout.decode("utf-8", errors="replace")
                    stderr_str = stderr.decode("utf-8", errors="replace")
                    return_code = process.returncode

                    # Format output
                    output_parts = []
                    if stdout_str:
                        output_parts.append(f"stdout:\n{stdout_str}")
                    if stderr_str:
                        output_parts.append(f"stderr:\n{stderr_str}")
                    output_parts.append(f"exit code: {return_code}")
                    output = "\n\n".join(output_parts)

                    # Truncate if too large
                    output = truncate_output(output)

                    metadata = {
                        "command": command,
                        "return_code": return_code,
                        "timeout": timeout_sec,
                    }

                    success = return_code == 0

                    if not success:
                        logger.warning(
                            f"Command failed with return code {return_code}: {command}"
                        )

                    return ToolResult(
                        success=success,
                        output=output,
                        error=None if success else f"Command failed with return code {return_code}",
                        metadata=metadata,
                    )

                except asyncio.TimeoutError:
                    # Kill process if it times out
                    if process:
                        process.kill()
                        await process.wait()

                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Command timed out after {timeout_sec}s",
                        metadata={"command": command, "timeout": timeout_sec},
                    )

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {str(e)}",
            )
