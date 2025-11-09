"""Basic usage example for the sandboxed agent."""

import asyncio

from src.agent import SandboxAgent


async def main():
    """Run a simple task with the sandbox agent."""
    print("Starting Sandboxed Agent Example")
    print("=" * 50)

    # Create agent
    async with SandboxAgent() as agent:
        # Simple task
        task = """
        Create a Python script called hello.py that prints 'Hello, Sandbox!'
        and then execute it.
        """

        print(f"\nTask: {task.strip()}\n")

        # Run task
        result = await agent.run(task)

        # Display results
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"\n{result}")
        print(f"\nSession ID: {agent.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
