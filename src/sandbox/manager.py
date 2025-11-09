"""Docker container manager for sandbox environments."""

import asyncio
import time
import uuid
from typing import Dict, Optional

import docker
from docker.errors import DockerException
from docker.models.containers import Container

from src.config import config
from src.utils import logger, retry_with_backoff


class ContainerManager:
    """Manages Docker container lifecycle for sandbox execution."""

    def __init__(self, image: Optional[str] = None):
        """Initialize container manager."""
        self.image = image or config.sandbox_image
        self.client: Optional[docker.DockerClient] = None
        self.container: Optional[Container] = None
        self.session_id: Optional[str] = None
        self.created_at: Optional[float] = None

    def connect(self) -> None:
        """Connect to Docker daemon."""
        try:
            self.client = docker.from_env()
            logger.info("Connected to Docker daemon")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise

    async def create_container(
        self,
        workspace_path: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Create a new sandbox container.

        Args:
            workspace_path: Path to mount as workspace
            environment: Environment variables to set

        Returns:
            Container ID
        """
        if not self.client:
            self.connect()

        self.session_id = str(uuid.uuid4())
        self.created_at = time.time()

        logger.debug(f"Creating sandbox container (session: {self.session_id})")

        try:
            # Prepare volumes
            volumes = {}
            if workspace_path:
                volumes[workspace_path] = {
                    "bind": "/home/user/workspace",
                    "mode": "rw",
                }

            # Prepare environment variables
            env = environment or {}
            env.update({
                "SESSION_ID": self.session_id,
                "PYTHONUNBUFFERED": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            })

            # Create container
            self.container = self.client.containers.run(
                self.image,
                detach=True,
                tty=True,
                stdin_open=True,
                remove=False,  # We'll remove manually
                name=f"sandbox-{self.session_id[:8]}",
                hostname="sandbox",
                # Resource limits
                cpu_count=int(config.sandbox_cpu_limit),
                mem_limit=config.sandbox_memory_limit,
                # Security
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                cap_add=["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"],
                # Network
                network_mode=config.sandbox_network_mode,
                # Volumes
                volumes=volumes,
                # Environment
                environment=env,
                # Working directory
                working_dir="/home/user/workspace",
            )

            # Wait for container to be ready
            await self._wait_for_ready()

            container_id = self.container.id
            logger.info(f"Container created: {container_id[:12]}")

            return container_id

        except DockerException as e:
            logger.error(f"Failed to create container: {e}")
            raise

    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for container to be ready."""
        if not self.container:
            raise RuntimeError("No container available")

        logger.debug("Waiting for container to be ready...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if container is running
                self.container.reload()
                if self.container.status == "running":
                    # Try to execute a simple command
                    exit_code, _ = self.container.exec_run("python --version")
                    if exit_code == 0:
                        logger.debug("Container is ready")
                        return

            except Exception:
                pass

            await asyncio.sleep(0.5)

        raise TimeoutError(f"Container not ready after {timeout}s")

    def execute_command(
        self,
        command: str,
        workdir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> tuple[int, bytes, bytes]:
        """
        Execute a command in the container.

        Args:
            command: Command to execute
            workdir: Working directory for command
            environment: Environment variables
            timeout: Execution timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.container:
            raise RuntimeError("No container available")

        try:
            logger.debug(f"Executing in container: {command}")

            # Execute command
            exec_result = self.container.exec_run(
                command,
                workdir=workdir or "/home/user/workspace",
                environment=environment,
                demux=True,  # Separate stdout and stderr
                tty=False,
            )

            exit_code = exec_result.exit_code
            stdout = exec_result.output[0] if exec_result.output[0] else b""
            stderr = exec_result.output[1] if exec_result.output[1] else b""

            return exit_code, stdout, stderr

        except DockerException as e:
            logger.error(f"Failed to execute command: {e}")
            raise

    def stop_container(self, timeout: int = 10) -> None:
        """Stop the container."""
        if not self.container:
            logger.warning("No container to stop")
            return

        try:
            logger.info(f"Stopping container {self.container.id[:12]}")
            self.container.stop(timeout=timeout)
            logger.info("Container stopped")
        except DockerException as e:
            logger.error(f"Failed to stop container: {e}")
            raise

    def remove_container(self, force: bool = True) -> None:
        """Remove the container."""
        if not self.container:
            logger.warning("No container to remove")
            return

        try:
            logger.info(f"Removing container {self.container.id[:12]}")
            self.container.remove(force=force)
            logger.info("Container removed")
            self.container = None
        except DockerException as e:
            logger.error(f"Failed to remove container: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up container and resources."""
        logger.debug("Cleaning up container...")

        if self.container:
            try:
                self.stop_container()
                self.remove_container()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

        logger.debug("Cleanup complete")

    def get_status(self) -> Dict[str, any]:
        """Get container status."""
        if not self.container:
            return {"status": "no_container"}

        try:
            self.container.reload()
            uptime = time.time() - self.created_at if self.created_at else 0

            return {
                "status": self.container.status,
                "id": self.container.id[:12],
                "session_id": self.session_id,
                "uptime": uptime,
                "image": self.image,
            }
        except DockerException:
            return {"status": "error"}
