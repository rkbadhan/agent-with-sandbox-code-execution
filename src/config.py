"""Configuration management for the sandboxed agent."""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()


class Config(BaseSettings):
    """Main configuration with all settings flattened."""

    # LLM Configuration
    llm_provider: str = Field(default="anthropic", alias="LLM_PROVIDER")  # anthropic or azure

    # Anthropic Configuration
    api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    model_name: str = Field(default="claude-sonnet-4-5-20250929", alias="MODEL_NAME")
    max_tokens: int = Field(default=8192, alias="MAX_TOKENS")
    temperature: float = Field(default=0.7, alias="TEMPERATURE")

    # Azure OpenAI Configuration
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_API_VERSION")

    # Sandbox Configuration
    sandbox_image: str = Field(default="sandbox-agent:latest", alias="SANDBOX_IMAGE")
    sandbox_timeout: int = Field(default=3600, alias="SANDBOX_TIMEOUT")
    sandbox_cpu_limit: str = Field(default="2", alias="SANDBOX_CPU_LIMIT")
    sandbox_memory_limit: str = Field(default="4g", alias="SANDBOX_MEMORY_LIMIT")
    sandbox_disk_limit: str = Field(default="10g", alias="SANDBOX_DISK_LIMIT")
    sandbox_network_mode: str = Field(default="bridge", alias="SANDBOX_NETWORK_MODE")

    # Network Configuration
    allowed_domains: Optional[str] = Field(default=None, alias="ALLOWED_DOMAINS")
    network_proxy_enabled: bool = Field(default=True, alias="NETWORK_PROXY_ENABLED")
    network_proxy_port: int = Field(default=8888, alias="NETWORK_PROXY_PORT")
    network_proxy_host: str = Field(default="0.0.0.0", alias="NETWORK_PROXY_HOST")

    # Security Configuration
    enable_secret_detection: bool = Field(
        default=True, alias="ENABLE_SECRET_DETECTION"
    )
    enable_command_validation: bool = Field(
        default=True, alias="ENABLE_COMMAND_VALIDATION"
    )
    read_only_paths: Optional[str] = Field(default=None, alias="READ_ONLY_PATHS")
    max_file_size_mb: int = Field(default=100, alias="MAX_FILE_SIZE_MB")
    max_output_size_mb: int = Field(default=10, alias="MAX_OUTPUT_SIZE_MB")

    # Session Configuration
    session_cleanup_enabled: bool = Field(default=True, alias="SESSION_CLEANUP_ENABLED")
    session_max_idle_time: int = Field(default=1800, alias="SESSION_MAX_IDLE_TIME")
    max_concurrent_sessions: int = Field(
        default=10, alias="MAX_CONCURRENT_SESSIONS"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: Optional[str] = Field(default="logs/agent.log", alias="LOG_FILE")

    # General Configuration
    debug: bool = Field(default=False, alias="DEBUG")
    enable_profiling: bool = Field(default=False, alias="ENABLE_PROFILING")

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    logs_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "logs"
    )

    class ConfigDict:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):  # type: ignore
        super().__init__(**kwargs)

        # Parse allowed domains from env string or use defaults
        if self.allowed_domains:
            self.allowed_domains = [d.strip() for d in self.allowed_domains.split(",") if d.strip()]
        else:
            self.allowed_domains = [
                "github.com",
                "api.github.com",
                "npmjs.com",
                "registry.npmjs.org",
                "pypi.org",
                "files.pythonhosted.org",
                "archive.ubuntu.com",
                "security.ubuntu.com",
                "api.anthropic.com",
                "openai.azure.com",
                "*.openai.azure.com",
            ]

        # Parse read-only paths from env string or use defaults
        if self.read_only_paths:
            self.read_only_paths = [p.strip() for p in self.read_only_paths.split(",") if p.strip()]
        else:
            self.read_only_paths = ["/mnt/user-data", "/mnt/skills", "/mnt/transcripts"]

        # Create necessary directories
        self.logs_dir.mkdir(exist_ok=True, parents=True)


# Global configuration instance
config = Config()
