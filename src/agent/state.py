"""Simplified agent state - no longer using LangGraph state machine.

The agent now uses a simple list of messages (LangChain format) instead of
complex state management. This file is kept for backwards compatibility
and may be removed in the future.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AgentSession:
    """Simple session information for tracking agent execution."""

    session_id: str
    container_id: Optional[str] = None
    iteration: int = 0
    max_iterations: int = 50

    def increment_iteration(self) -> None:
        """Increment the iteration counter."""
        self.iteration += 1

    def is_max_iterations_reached(self) -> bool:
        """Check if max iterations reached."""
        return self.iteration >= self.max_iterations
