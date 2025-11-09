"""Sandbox executor for running tools in containers."""

from typing import Any, Dict, Optional

from src.sandbox.manager import ContainerManager
from src.tools import TOOL_REGISTRY, BaseTool, ToolResult
from src.utils import logger


class SandboxExecutor:
    """Executes tools within a sandboxed container."""

    def __init__(self, container_manager: ContainerManager):
        """Initialize sandbox executor."""
        self.container_manager = container_manager
        self.tools: Dict[str, BaseTool] = {}

        # Initialize all tools with this executor
        for tool_name, tool_class in TOOL_REGISTRY.items():
            self.tools[tool_name] = tool_class(executor=self)

    async def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters

        Returns:
            ToolResult with execution results
        """
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}",
            )

        tool = self.tools[tool_name]

        logger.info(f"Executing tool: {tool_name}")
        logger.debug(f"Parameters: {parameters}")

        try:
            result = await tool.run(**parameters)
            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {str(e)}",
            )

    async def execute_command_in_container(
        self,
        command: str,
        workdir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> tuple[int, str, str]:
        """
        Execute a command in the sandbox container.

        Args:
            command: Command to execute
            workdir: Working directory
            environment: Environment variables
            timeout: Execution timeout

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        exit_code, stdout_bytes, stderr_bytes = (
            self.container_manager.execute_command(
                command, workdir=workdir, environment=environment, timeout=timeout
            )
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        return exit_code, stdout, stderr

    def list_tools(self) -> list[str]:
        """List available tools."""
        return list(self.tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a tool."""
        if tool_name not in self.tools:
            return None

        tool = self.tools[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_class.model_json_schema(),
        }

    def get_all_tools_info(self) -> list[Dict[str, Any]]:
        """Get information about all tools."""
        return [self.get_tool_info(name) for name in self.tools.keys()]
