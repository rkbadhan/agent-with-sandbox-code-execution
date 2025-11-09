"""Simplified sandbox agent with native LLM tool calling."""

import uuid
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.config import config
from src.sandbox.executor import SandboxExecutor
from src.sandbox.manager import ContainerManager
from src.tools import TOOL_REGISTRY
from src.utils import logger


# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful coding assistant with access to development tools and capabilities.

You can execute code, read and write files, run shell commands, and perform various development tasks using the available tools.

When analyzing logs or complex files:
- Use Read tool to examine file contents
- Use Grep to search for specific patterns
- Use Bash to run analysis commands
- Break down complex analysis into steps

Always explain your reasoning and provide clear, actionable results.
"""


class SandboxAgent:
    """
    Simplified sandboxed code execution agent.

    Uses a simple reasoning loop with native LLM tool calling instead of
    complex state machines. The LLM decides which tools to use and when.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        session_timeout: int = 3600,
        max_iterations: int = 50,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the sandbox agent.

        Args:
            model: LLM model to use (default: from config)
            session_timeout: Session timeout in seconds
            max_iterations: Maximum number of iterations
            system_prompt: Custom system prompt (optional)
        """
        self.model_name = model or config.model_name
        self.session_timeout = session_timeout
        self.max_iterations = max_iterations
        self.session_id = str(uuid.uuid4())
        self.system_prompt = system_prompt or SYSTEM_PROMPT

        # Initialize LLM based on provider
        if config.llm_provider == "azure":
            logger.info("Initializing Azure OpenAI client")
            self.llm = AzureChatOpenAI(
                azure_endpoint=config.azure_openai_endpoint,
                azure_deployment=config.azure_openai_deployment,
                api_key=config.azure_openai_api_key,
                api_version=config.azure_api_version,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )
        else:
            logger.info("Initializing Anthropic client")
            self.llm = ChatAnthropic(
                model=self.model_name,
                api_key=config.api_key,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )

        # Initialize container manager
        self.container_manager = ContainerManager()

        # Initialize executor
        self.executor: Optional[SandboxExecutor] = None

        # Convert tools to LangChain format for tool calling
        self.tools = self._prepare_tools()

        # Bind tools to LLM for native tool calling
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        logger.info(f"Initialized SandboxAgent (session: {self.session_id})")

    def _prepare_tools(self) -> List[Dict[str, Any]]:
        """
        Prepare tools in LangChain tool calling format.

        Returns:
            List of tool definitions
        """
        tools = []

        for tool_name, tool_instance in TOOL_REGISTRY.items():
            # Create tool definition from our tool class
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_instance.description,
                    "parameters": tool_instance.parameters_class.model_json_schema(),
                },
            }
            tools.append(tool_def)

        return tools

    async def setup(self) -> None:
        """Set up the agent and container."""
        logger.info("Setting up sandbox environment...")

        # Create container
        container_id = await self.container_manager.create_container()

        # Initialize executor
        self.executor = SandboxExecutor(self.container_manager)

        logger.info(f"Sandbox ready (container: {container_id[:12]})")

    async def run(self, task: str) -> str:
        """
        Run the agent on a task using simple reasoning loop.

        Args:
            task: Task description

        Returns:
            Final response from the agent
        """
        # Set up if not already done
        if not self.executor:
            await self.setup()

        logger.info(f"Running task: {task}")

        # Initialize messages with system prompt and user task
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=task),
        ]

        # Simple while loop - LLM controls everything
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Iteration {iteration}/{self.max_iterations}")

            # Get LLM response (may include tool calls)
            response = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)

            # Check if LLM wants to use tools
            if hasattr(response, "tool_calls") and response.tool_calls:
                logger.debug(f"LLM requested {len(response.tool_calls)} tool call(s)")

                # Execute each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_call_id = tool_call["id"]

                    logger.debug(f"Executing tool: {tool_name}")

                    # Execute tool in sandbox
                    result = await self.executor.execute_tool(tool_name, tool_args)

                    # Add tool result to messages
                    tool_message = ToolMessage(
                        content=result.output if result.success else result.error,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                    messages.append(tool_message)

                    if not result.success:
                        logger.warning(f"Tool {tool_name} failed: {result.error}")

            else:
                # LLM provided final answer without tool calls
                logger.info("Task completed")
                return response.content

        # Max iterations reached
        logger.warning("Max iterations reached")
        return "I've reached the maximum number of iterations. Here's what I found so far:\n\n" + (
            messages[-1].content if messages else "No results yet."
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up agent resources...")

        if self.container_manager:
            await self.container_manager.cleanup()

        logger.info("Cleanup complete")

    async def __aenter__(self) -> "SandboxAgent":
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()


# Convenience function for one-off tasks
async def run_task(task: str, **kwargs) -> str:
    """
    Run a single task with automatic cleanup.

    Args:
        task: Task description
        **kwargs: Additional arguments for SandboxAgent

    Returns:
        Result string
    """
    async with SandboxAgent(**kwargs) as agent:
        return await agent.run(task)
