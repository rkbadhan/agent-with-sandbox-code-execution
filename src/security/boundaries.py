"""Filesystem boundary enforcement."""

from pathlib import Path
from typing import List

from src.config import config
from src.utils import logger


class FilesystemBoundaries:
    """Enforces filesystem access boundaries."""

    def __init__(self, read_only_paths: List[str] = None):
        """Initialize filesystem boundaries."""
        self.read_only_paths = read_only_paths or config.read_only_paths

    def is_read_only(self, file_path: str) -> bool:
        """Check if a path is in a read-only directory."""
        path = Path(file_path).resolve()

        for ro_path in self.read_only_paths:
            ro_path_resolved = Path(ro_path).resolve()
            try:
                # Check if path is within or equal to read-only path
                path.relative_to(ro_path_resolved)
                return True
            except ValueError:
                # path is not relative to ro_path_resolved
                continue

        return False

    def validate_write_access(self, file_path: str) -> None:
        """Validate that a path can be written to."""
        if self.is_read_only(file_path):
            raise PermissionError(
                f"Cannot write to read-only path: {file_path}. "
                f"Read-only paths: {', '.join(self.read_only_paths)}"
            )

    def validate_delete_access(self, file_path: str) -> None:
        """Validate that a path can be deleted."""
        if self.is_read_only(file_path):
            raise PermissionError(
                f"Cannot delete from read-only path: {file_path}"
            )

    def get_accessible_path(self, file_path: str) -> Path:
        """
        Get an accessible version of the path.

        Resolves symlinks and checks for path traversal attacks.
        """
        path = Path(file_path).resolve()

        # Check for suspicious patterns
        path_str = str(path)
        if ".." in path_str:
            logger.warning(f"Suspicious path with ..: {file_path}")

        return path

    def is_safe_path(self, file_path: str, base_path: str = "/home/user") -> bool:
        """
        Check if a path is safe (within base_path).

        Args:
            file_path: Path to check
            base_path: Base directory that access is restricted to

        Returns:
            True if path is safe, False otherwise
        """
        try:
            resolved_path = Path(file_path).resolve()
            resolved_base = Path(base_path).resolve()

            # Check if path is within base
            resolved_path.relative_to(resolved_base)
            return True

        except ValueError:
            # Path is outside base
            return False
