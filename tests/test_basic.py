"""Basic tests for the sandboxed agent."""

import pytest

from src.config import config
from src.tools import get_tool, list_tools
from src.utils import calculate_hash, format_duration, truncate_output


class TestConfiguration:
    """Test configuration loading."""

    def test_config_loaded(self):
        """Test that config is properly loaded."""
        assert config is not None
        assert config.llm_provider is not None
        assert config.sandbox_image is not None
        assert config.enable_secret_detection is not None

    def test_config_values(self):
        """Test specific config values."""
        assert config.sandbox_image == "sandbox-agent:latest"
        assert config.sandbox_timeout == 3600
        assert len(config.allowed_domains) > 0


class TestTools:
    """Test tool system."""

    def test_list_tools(self):
        """Test listing available tools."""
        tools = list_tools()
        assert len(tools) > 0
        assert "Read" in tools
        assert "Write" in tools
        assert "Bash" in tools

    def test_get_tool(self):
        """Test getting a tool by name."""
        read_tool = get_tool("Read")
        assert read_tool is not None
        assert read_tool.name == "Read"

    def test_unknown_tool(self):
        """Test getting unknown tool raises error."""
        with pytest.raises(ValueError):
            get_tool("UnknownTool")


class TestUtils:
    """Test utility functions."""

    def test_calculate_hash(self):
        """Test hash calculation."""
        content = "Hello, World!"
        hash1 = calculate_hash(content)
        hash2 = calculate_hash(content)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_format_duration(self):
        """Test duration formatting."""
        assert "ms" in format_duration(0.5)
        assert "s" in format_duration(30)
        assert "m" in format_duration(90)
        assert "h" in format_duration(3700)

    def test_truncate_output(self):
        """Test output truncation."""
        long_output = "\n".join([f"Line {i}" for i in range(2000)])
        truncated = truncate_output(long_output, max_lines=10)
        assert "truncated" in truncated.lower()
        assert len(truncated.split("\n")) <= 12  # 10 lines + truncation message


@pytest.mark.asyncio
class TestToolExecution:
    """Test tool execution (without container)."""

    async def test_read_tool_parameters(self):
        """Test Read tool parameter validation."""
        from src.tools import ReadTool

        tool = ReadTool()
        params = tool.validate_parameters({"file_path": "/tmp/test.txt"})
        assert params.file_path == "/tmp/test.txt"

    async def test_bash_tool_parameters(self):
        """Test Bash tool parameter validation."""
        from src.tools import BashTool

        tool = BashTool()
        params = tool.validate_parameters({"command": "echo hello"})
        assert params.command == "echo hello"
        assert params.timeout == 120000  # Default


class TestSecurity:
    """Test security components."""

    def test_filesystem_boundaries(self):
        """Test filesystem boundary checks."""
        from src.security import FilesystemBoundaries

        boundaries = FilesystemBoundaries()
        assert boundaries.is_read_only("/mnt/user-data/file.txt")
        assert not boundaries.is_read_only("/home/user/workspace/file.txt")

    def test_secret_detector(self):
        """Test secret detection."""
        from src.security import SecretDetector

        detector = SecretDetector()

        # Test API key detection
        content = "API_KEY=sk-1234567890abcdefghij"
        secrets = detector.scan_content(content)
        assert len(secrets) > 0

    def test_input_validator(self):
        """Test input validation."""
        from src.security import InputValidator

        validator = InputValidator()

        # Test safe command
        assert validator.validate_command("ls -la")

        # Test dangerous command
        with pytest.raises(ValueError):
            validator.validate_command("rm -rf /")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
