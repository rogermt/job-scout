"""Stack Overflow job scraper implementation."""

from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from src.config_manager import PlatformConfig
from .base_scraper import BaseScraper


class StackOverflowScraper(BaseScraper):
    """Scraper for Stack Overflow jobs."""

    def __init__(
        self, platform_name: str, config: PlatformConfig, rate_limit: int = 5
    ) -> None:
        """Initialize the Stack Overflow scraper.

        Args:
            platform_name: Name of the platform
            config: Platform configuration
            rate_limit: Requests per second limit
        """
        super().__init__(platform_name, config, rate_limit)

    def build_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Build search URL with parameters."""
        base_url = "https://stackoverflow.com/jobs"
        loc = location.replace(" ", "-").lower() if location else ""
        params = f"q={query.replace(' ', '+').lower()}&l={loc}"
        if page := kwargs.get("page", 0):
            params += f"&pg={page + 1}"
        return f"{base_url}?{params}"

    def get_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Get search URL (delegates to build_search_url)."""
        return self.build_search_url(query, location, **kwargs)

    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        """Extract job listing elements from search results."""
        return soup.select(".job-card, .single-job-result, [data-jobid]")

    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        """Parse a single job listing element."""
        job_id = element.get("data-jobid")
        if not job_id:
            return None
        return {"platform_id": job_id, "title": "Unknown"}

    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information."""
        soup = self.fetch_page(job_url)
        if soup:
            return {}
        return None
