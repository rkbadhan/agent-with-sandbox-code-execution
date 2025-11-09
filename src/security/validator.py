"""Input validation for security."""

import re
from typing import Any, Dict

from src.utils import logger


class InputValidator:
    """Validates user inputs for security."""

    # Dangerous command patterns
    DANGEROUS_COMMANDS = [
        r"\brm\s+-rf\s+/",  # Standalone rm -rf /
        r"\brm\s+-rf\s+\*",  # Standalone rm -rf *
        r";\s*rm\s+-rf",
        r"&&\s*rm\s+-rf",
        r"\|\s*rm\s+-rf",
        r";\s*curl.*\|.*sh",
        r"&&\s*curl.*\|.*sh",
        r";\s*wget.*\|.*sh",
        r"&&\s*wget.*\|.*sh",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r">\s*/dev/sd",
        r"mkfs\.",
        r"dd\s+if=",
        r":\(\)\{.*:\|:&\};:",  # Fork bomb
    ]

    # Dangerous file paths
    DANGEROUS_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root/",
        "/boot/",
        "/sys/",
        "/proc/",
        "/dev/",
    ]

    def __init__(self, enabled: bool = True):
        """Initialize input validator."""
        self.enabled = enabled

    def validate_command(self, command: str) -> bool:
        """
        Validate a shell command for safety.

        Args:
            command: Command to validate

        Returns:
            True if safe, False otherwise

        Raises:
            ValueError: If command is dangerous
        """
        if not self.enabled:
            return True

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(
                    f"Command contains dangerous pattern: {pattern}. "
                    f"Command: {command[:100]}"
                )

        # Check for suspicious characters
        if "$((" in command or "$(()" in command:
            logger.warning(f"Suspicious command syntax: {command[:100]}")

        return True

    def validate_file_path(self, file_path: str) -> bool:
        """
        Validate a file path for safety.

        Args:
            file_path: Path to validate

        Returns:
            True if safe, False otherwise

        Raises:
            ValueError: If path is dangerous
        """
        if not self.enabled:
            return True

        # Check for dangerous paths
        for dangerous_path in self.DANGEROUS_PATHS:
            if file_path.startswith(dangerous_path):
                raise ValueError(
                    f"Access to path is restricted: {file_path}. "
                    f"Cannot access system directory: {dangerous_path}"
                )

        # Check for path traversal
        if ".." in file_path:
            logger.warning(f"Path contains ..: {file_path}")

        # Check for null bytes (common in injection attacks)
        if "\x00" in file_path:
            raise ValueError("Path contains null byte - potential injection attack")

        return True


    def validate_url(self, url: str, allowed_domains: list[str]) -> bool:
        """
        Validate a URL against allowed domains.

        Args:
            url: URL to validate
            allowed_domains: List of allowed domains

        Returns:
            True if safe, False otherwise

        Raises:
            ValueError: If URL is not allowed
        """
        if not self.enabled:
            return True

        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        for allowed_domain in allowed_domains:
            if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                return True

        raise ValueError(
            f"Domain not allowed: {domain}. "
            f"Allowed domains: {', '.join(allowed_domains)}"
        )

    def sanitize_log_output(self, output: str, max_length: int = 10000) -> str:
        """
        Sanitize log output to prevent log injection.

        Args:
            output: Output to sanitize
            max_length: Maximum length

        Returns:
            Sanitized output
        """
        # Remove control characters except newlines and tabs
        sanitized = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", output)

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "\n... (truncated)"

        return sanitized

    def validate_environment_variables(self, env_vars: Dict[str, Any]) -> bool:
        """
        Validate environment variables.

        Args:
            env_vars: Environment variables to validate

        Returns:
            True if safe, False otherwise
        """
        if not self.enabled:
            return True

        dangerous_vars = ["LD_PRELOAD", "LD_LIBRARY_PATH", "PATH"]

        for var_name in env_vars:
            if var_name in dangerous_vars:
                logger.warning(
                    f"Setting potentially dangerous environment variable: {var_name}"
                )

        return True
