"""Base tool class and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolParameters(BaseModel):
    """Base class for tool parameters."""

    pass


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """Base class for all tools."""

    name: str
    description: str
    parameters_class: type[ToolParameters]

    def __init__(self, executor: Optional[Any] = None):
        """Initialize tool with optional executor."""
        self.executor = executor

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> ToolParameters:
        """Validate and parse parameters."""
        return self.parameters_class(**params)

    async def run(self, **kwargs: Any) -> ToolResult:
        """Run the tool with parameter validation."""
        try:
            # Validate parameters
            validated_params = self.validate_parameters(kwargs)

            # Execute tool
            result = await self.execute(**validated_params.model_dump())

            return result

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {str(e)}",
                metadata={"tool_name": self.name, "parameters": kwargs},
            )

    def to_langchain_tool(self) -> Dict[str, Any]:
        """Convert to LangChain tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_class.model_json_schema(),
        }
