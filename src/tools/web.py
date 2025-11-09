"""Web access tools: WebFetch and WebSearch."""

from typing import Optional

import httpx
from pydantic import Field

from src.config import config
from src.tools.base import BaseTool, ToolParameters, ToolResult
from src.utils import logger


class WebFetchParameters(ToolParameters):
    """Parameters for WebFetch tool."""

    url: str = Field(description="URL to fetch content from")
    prompt: str = Field(description="Prompt to process the fetched content")


class WebFetchTool(BaseTool):
    """Tool for fetching web content."""

    name = "WebFetch"
    description = (
        "Fetches content from a URL and processes it with a prompt. "
        "Converts HTML to markdown for better readability. "
        "Only works with allowed domains."
    )
    parameters_class = WebFetchParameters

    def _check_domain_allowed(self, url: str) -> bool:
        """Check if domain is in allowed list."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        for allowed_domain in config.allowed_domains:
            if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                return True

        return False

    async def execute(self, url: str, prompt: str, **kwargs) -> ToolResult:
        """Fetch web content."""
        try:
            # Check if domain is allowed
            if not self._check_domain_allowed(url):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Domain not in allowed list. Allowed domains: {', '.join(config.allowed_domains)}",
                )

            # Upgrade HTTP to HTTPS
            if url.startswith("http://"):
                url = url.replace("http://", "https://", 1)
                logger.info(f"Upgraded HTTP to HTTPS: {url}")

            logger.info(f"Fetching URL: {url}")

            # Fetch content
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                # For HTML, convert to markdown (simplified)
                if "text/html" in content_type:
                    # Simple HTML to text conversion
                    # In production, you'd use a library like markdownify or beautifulsoup
                    text = response.text
                    # Remove script and style tags
                    import re

                    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                    # Remove HTML tags
                    text = re.sub(r"<[^>]+>", " ", text)
                    # Clean up whitespace
                    text = re.sub(r"\s+", " ", text)
                    content = text.strip()
                else:
                    content = response.text

            # Truncate if too large
            max_length = 50000
            if len(content) > max_length:
                content = content[:max_length] + "\n\n[Content truncated...]"

            output = f"URL: {url}\n\nContent:\n{content}\n\nPrompt: {prompt}"

            metadata = {
                "url": url,
                "status_code": response.status_code,
                "content_length": len(content),
            }

            logger.info(f"Successfully fetched {len(content)} characters from {url}")

            return ToolResult(success=True, output=output, metadata=metadata)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to fetch URL: {str(e)}",
            )


class WebSearchParameters(ToolParameters):
    """Parameters for WebSearch tool."""

    query: str = Field(description="Search query")
    allowed_domains: Optional[list[str]] = Field(
        default=None, description="Only include results from these domains"
    )
    blocked_domains: Optional[list[str]] = Field(
        default=None, description="Never include results from these domains"
    )


class WebSearchTool(BaseTool):
    """Tool for web search."""

    name = "WebSearch"
    description = (
        "Performs web search and returns results. "
        "Supports domain filtering. "
        "Note: This is a simplified implementation."
    )
    parameters_class = WebSearchParameters

    async def execute(
        self,
        query: str,
        allowed_domains: Optional[list[str]] = None,
        blocked_domains: Optional[list[str]] = None,
        **kwargs,
    ) -> ToolResult:
        """Perform web search."""
        try:
            # Note: This is a placeholder implementation
            # In production, you would integrate with a search API like:
            # - Google Custom Search API
            # - Bing Search API
            # - DuckDuckGo API
            # - Serper API

            logger.info(f"Web search: {query}")

            output = (
                f"Search query: {query}\n\n"
                f"Note: Web search requires API integration. "
                f"Please integrate with a search provider (Google, Bing, DuckDuckGo, etc.) "
                f"in the WebSearchTool.execute() method."
            )

            return ToolResult(
                success=False,
                output=output,
                error="Web search not implemented. Please configure a search API provider.",
            )

        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Web search failed: {str(e)}",
            )
