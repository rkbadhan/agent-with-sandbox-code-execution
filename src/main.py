"""Main entry point for the sandboxed agent."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from src.agent import SandboxAgent
from src.config import config
from src.utils import logger, print_table

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Sandboxed AI Agent - Execute code safely in isolated containers."""
    pass


@cli.command()
@click.argument("task", required=False)
@click.option(
    "--model",
    "-m",
    default=None,
    help="LLM model to use (default: from config)",
)
@click.option(
    "--timeout",
    "-t",
    default=3600,
    help="Session timeout in seconds (default: 3600)",
)
@click.option(
    "--max-iterations",
    "-i",
    default=50,
    help="Maximum number of iterations (default: 50)",
)
def run(task: str, model: str, timeout: int, max_iterations: int):
    """
    Run the agent on a task.

    Examples:

        \b
        # Simple task
        sandbox-agent run "Create a Python script that analyzes log files"

        \b
        # Interactive mode
        sandbox-agent run

        \b
        # With custom model
        sandbox-agent run "Fix bugs in main.py" --model claude-opus-4
    """
    if not task:
        # Interactive mode
        console.print(
            Panel(
                "[bold green]Sandboxed Agent - Interactive Mode[/bold green]\n\n"
                "Enter your task below, or type 'exit' to quit.",
                border_style="green",
            )
        )
        task = console.input("\n[bold cyan]Task:[/bold cyan] ")

        if task.lower() in ["exit", "quit", "q"]:
            console.print("[yellow]Goodbye![/yellow]")
            sys.exit(0)

    asyncio.run(_run_agent(task, model, timeout, max_iterations))


async def _run_agent(
    task: str, model: str, timeout: int, max_iterations: int
) -> None:
    """Run the agent asynchronously."""
    try:
        console.print(f"\n[bold]Task:[/bold] {task}\n")

        async with SandboxAgent(
            model=model, session_timeout=timeout, max_iterations=max_iterations
        ) as agent:
            console.print("[yellow]Setting up sandbox environment...[/yellow]")

            result = await agent.run(task)

            console.print("\n[bold green]✓ Task completed![/bold green]\n")

            # Display results (result is now a simple string)
            console.print(Panel(result, title="Output", border_style="green"))

            console.print(f"\n[dim]Session ID: {agent.session_id}[/dim]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Task cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Agent execution failed")
        sys.exit(1)


@cli.command()
def info():
    """Display information about the agent and configuration."""
    console.print("\n[bold cyan]Sandboxed AI Agent[/bold cyan]\n")

    # Configuration
    config_info = [
        ["LLM Model", config.model_name],
        ["Max Tokens", str(config.max_tokens)],
        ["Temperature", str(config.temperature)],
        ["Sandbox Image", config.sandbox_image],
        ["CPU Limit", config.sandbox_cpu_limit],
        ["Memory Limit", config.sandbox_memory_limit],
        ["Session Timeout", f"{config.sandbox_timeout}s"],
        ["Network Proxy", "Enabled" if config.network_proxy_enabled else "Disabled"],
        ["Allowed Domains", str(len(config.allowed_domains))],
        [
            "Secret Detection",
            "Enabled" if config.enable_secret_detection else "Disabled",
        ],
    ]

    print_table("Configuration", ["Setting", "Value"], config_info, show_lines=False)

    # Tools
    from src.tools import list_tools

    tools = list_tools()
    console.print(f"\n[bold]Available Tools:[/bold] {len(tools)}")
    for tool in tools:
        console.print(f"  • {tool}")

    console.print()


@cli.command()
@click.option(
    "--build", is_flag=True, help="Build the Docker image before checking status"
)
def status(build: bool):
    """Check Docker and sandbox status."""
    import docker

    if build:
        console.print("[yellow]Building Docker image...[/yellow]")
        asyncio.run(_build_docker_image())

    console.print("\n[bold cyan]System Status[/bold cyan]\n")

    try:
        client = docker.from_env()
        console.print("[green]✓ Docker daemon: Connected[/green]")

        # Check for sandbox image
        try:
            image = client.images.get(config.sandbox_image)
            console.print(f"[green]✓ Sandbox image: {config.sandbox_image}[/green]")
            console.print(f"  Created: {image.attrs['Created'][:19]}")
            console.print(f"  Size: {image.attrs['Size'] / 1024 / 1024:.1f} MB")
        except docker.errors.ImageNotFound:
            console.print(f"[red]✗ Sandbox image not found: {config.sandbox_image}[/red]")
            console.print("  Run: docker compose -f docker/docker-compose.yml build")

        # Check running containers
        containers = client.containers.list(filters={"ancestor": config.sandbox_image})
        console.print(f"\n[bold]Running Containers:[/bold] {len(containers)}")
        for container in containers:
            console.print(f"  • {container.name} ({container.status})")

    except Exception as e:
        console.print(f"[red]✗ Docker error: {e}[/red]")

    console.print()


async def _build_docker_image():
    """Build the Docker image."""
    import subprocess

    try:
        process = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "-f",
            "docker/docker-compose.yml",
            "build",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await process.communicate()

        if process.returncode == 0:
            console.print("[green]✓ Docker image built successfully[/green]")
        else:
            console.print("[red]✗ Failed to build Docker image[/red]")

    except Exception as e:
        console.print(f"[red]Error building image: {e}[/red]")


@cli.command()
@click.argument("example", required=False)
def example(example: str):
    """
    Run example tasks.

    Available examples:
      - hello: Simple hello world
      - file-ops: File operations
      - git-workflow: Git workflow
      - web-fetch: Fetch web content
    """
    examples = {
        "hello": "Create a Python script that prints 'Hello, World!' and run it",
        "file-ops": "Create a file named test.txt with 'Hello', read it, and modify it to say 'Hello, Agent!'",
        "git-workflow": "Initialize a git repo, create a README.md, commit it with message 'Initial commit'",
        "web-fetch": "Fetch the contents of https://example.com and save it to a file",
    }

    if not example:
        console.print("\n[bold cyan]Available Examples:[/bold cyan]\n")
        for name, task in examples.items():
            console.print(f"[bold]{name}[/bold]")
            console.print(f"  {task}\n")
        return

    if example not in examples:
        console.print(f"[red]Unknown example: {example}[/red]")
        console.print("Run 'sandbox-agent example' to see available examples")
        sys.exit(1)

    task = examples[example]
    console.print(f"\n[bold]Running example:[/bold] {example}\n")
    asyncio.run(_run_agent(task, None, 3600, 50))


if __name__ == "__main__":
    cli()
