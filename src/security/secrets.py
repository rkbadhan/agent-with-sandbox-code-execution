"""Secret detection to prevent credential leaks."""

import re
from typing import Dict, List, Tuple

from src.utils import logger


class SecretDetector:
    """Detects secrets and credentials in code and files."""

    # Common secret patterns (regex)
    PATTERNS = {
        "api_key": r"(?i)(api[_-]?key|apikey|api[_-]?token)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "aws_key": r"(?i)(aws[_-]?access[_-]?key[_-]?id)['\"]?\s*[:=]\s*['\"]?([A-Z0-9]{20})['\"]?",
        "aws_secret": r"(?i)(aws[_-]?secret[_-]?access[_-]?key)['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        "github_token": r"(?i)(github[_-]?token|gh[_-]?token)['\"]?\s*[:=]\s*['\"]?(ghp_[a-zA-Z0-9]{36})['\"]?",
        "slack_token": r"(xox[pborsa]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32})",
        "jwt": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "password": r"(?i)(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?([^'\"\s]{8,})['\"]?",
        "private_key": r"-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----",
        "connection_string": r"(?i)(mongodb|mysql|postgres|redis)://[^\s]+",
    }

    # Files that commonly contain secrets
    SUSPICIOUS_FILES = {
        ".env",
        ".env.local",
        ".env.production",
        "credentials.json",
        "secrets.json",
        "config.json",
        "auth.json",
        ".aws/credentials",
        ".ssh/id_rsa",
        ".ssh/id_ed25519",
        "keyfile",
        "private.key",
    }

    def __init__(self, enabled: bool = True):
        """Initialize secret detector."""
        self.enabled = enabled

    def scan_content(self, content: str) -> List[Dict[str, any]]:
        """
        Scan content for potential secrets.

        Args:
            content: Content to scan

        Returns:
            List of detected secrets with type and location
        """
        if not self.enabled:
            return []

        secrets = []

        for secret_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                secrets.append({
                    "type": secret_type,
                    "match": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "line": content[:match.start()].count("\n") + 1,
                })

        return secrets

    def scan_file(self, file_path: str) -> List[Dict[str, any]]:
        """
        Scan a file for potential secrets.

        Args:
            file_path: Path to file

        Returns:
            List of detected secrets
        """
        if not self.enabled:
            return []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            return self.scan_content(content)

        except Exception as e:
            logger.error(f"Error scanning file for secrets: {e}")
            return []

    def is_suspicious_file(self, file_path: str) -> bool:
        """Check if a file name is commonly used for secrets."""
        from pathlib import Path

        path = Path(file_path)

        # Check if filename matches suspicious patterns
        if path.name in self.SUSPICIOUS_FILES:
            return True

        # Check if path contains any suspicious parts
        for suspicious in self.SUSPICIOUS_FILES:
            if suspicious in str(path):
                return True

        return False

    def validate_commit(self, file_paths: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate files before commit.

        Args:
            file_paths: List of file paths to validate

        Returns:
            Tuple of (is_safe, list_of_warnings)
        """
        if not self.enabled:
            return True, []

        warnings = []

        for file_path in file_paths:
            # Check for suspicious filenames
            if self.is_suspicious_file(file_path):
                warnings.append(
                    f"Suspicious file: {file_path} (commonly contains secrets)"
                )

            # Scan file content
            secrets = self.scan_file(file_path)
            if secrets:
                warnings.append(
                    f"Potential secrets found in {file_path}: "
                    f"{len(secrets)} matches"
                )
                for secret in secrets[:3]:  # Show first 3
                    warnings.append(
                        f"  - Line {secret['line']}: {secret['type']}"
                    )

        is_safe = len(warnings) == 0
        return is_safe, warnings

    def redact_secrets(self, content: str) -> str:
        """
        Redact detected secrets from content.

        Args:
            content: Content to redact

        Returns:
            Content with secrets redacted
        """
        if not self.enabled:
            return content

        redacted = content

        for secret_type, pattern in self.PATTERNS.items():
            redacted = re.sub(
                pattern,
                lambda m: m.group(0)[:10] + "*" * 10 + "***REDACTED***",
                redacted,
                flags=re.MULTILINE
            )

        return redacted
