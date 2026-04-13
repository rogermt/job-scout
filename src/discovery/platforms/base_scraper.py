"""Base scraper class for all job discovery platforms."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generator, Optional

import requests
from bs4 import BeautifulSoup, Tag
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config_manager import PlatformConfig

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    def __init__(
        self, platform_name: str, config: PlatformConfig, rate_limit: int = 5
    ) -> None:
        """Initialize base scraper."""
        self.platform_name = platform_name
        self.config = config
        self.rate_limit = rate_limit
        self._last_request_time: float = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        wait_time = self.rate_limit - elapsed
        if wait_time > 0:
            time.sleep(wait_time)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _make_request(
        self, url: str, method: str = "GET", **kwargs: Any
    ) -> requests.Response:
        """Make HTTP request with automatic retries."""
        self._enforce_rate_limit()
        response = self.session.request(method, url, timeout=30, **kwargs)
        response.raise_for_status()
        self._last_request_time = time.time()
        return response

    def fetch_page(self, url: str, **kwargs: Any) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        try:
            response = self._make_request(url, **kwargs)
            return BeautifulSoup(response.content, "html.parser")
        except requests.RequestException:
            return None

    def is_enabled(self) -> bool:
        """Check if this scraper is enabled."""
        return self.config.enabled

    def can_scrape(self) -> bool:
        """Check if scraper can run."""
        return self.is_enabled()

    @abstractmethod
    def get_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Generate search URL for the platform."""
        pass

    @abstractmethod
    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        """Extract job listing elements from search results page."""
        pass

    @abstractmethod
    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        """Parse a single job listing element."""
        pass

    @abstractmethod
    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information."""
        pass

    def scrape_jobs(
        self, query: str, location: Optional[str] = None, max_pages: int = 5
    ) -> Generator[dict[str, Any], None, None]:
        """Scrape jobs from the platform."""
        current_page = 0
        while current_page < max_pages:
            search_url = self.get_search_url(query, location, page=current_page)
            soup = self.fetch_page(search_url)
            if not soup:
                break
            job_elements = self.extract_job_listings(soup)
            for element in job_elements:
                job_data = self.parse_job_listing(element)
                if job_data:
                    yield job_data
            current_page += 1

    def has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there are more pages to scrape."""
        pagination_links = soup.select("a[href*='page'], a[href*='next']")
        return len(pagination_links) > 0

    def parse_salary(self, salary_text: str) -> dict[str, Any]:
        """Parse salary text into min, max, and currency."""
        if not salary_text:
            return {"min": None, "max": None, "currency": None, "period": None}
        import re

        currency = "GBP"
        if "$" in salary_text:
            currency = "USD"
        elif "€" in salary_text:
            currency = "EUR"
        text = (
            salary_text.replace(",", "")
            .replace("£", "")
            .replace("$", "")
            .replace("€", "")
        )
        numbers = re.findall(r"(\d+(?:\.\d+)?)", text)
        if numbers:
            min_sal = float(numbers[0])
            max_sal = float(numbers[-1]) if len(numbers) > 1 else min_sal
            return {
                "min": min_sal,
                "max": max_sal,
                "currency": currency,
                "period": "yearly",
            }
        return {"min": None, "max": None, "currency": currency, "period": None}

    def parse_posted_date(self, text: str) -> Optional[str]:
        """Parse 'posted X days ago' text into datetime."""
        import re
        from dateutil.relativedelta import relativedelta

        now = datetime.utcnow()
        times = re.findall(r"(\d+)\s+(day|week|month|hour)", text, re.IGNORECASE)
        if times:
            amount = int(times[0][0])
            unit = times[0][1].lower()
            if "day" in unit:
                return (now - relativedelta(days=amount)).strftime("%Y-%m-%d")
            elif "week" in unit:
                return (now - relativedelta(weeks=amount)).strftime("%Y-%m-%d")
            elif "month" in unit:
                return (now - relativedelta(months=amount)).strftime("%Y-%m-%d")
            elif "hour" in unit:
                return (now - relativedelta(hours=amount)).strftime("%Y-%m-%d")
        return None


_scrapers: dict[str, type["BaseScraper"]] = {}


def register_scraper(platform_name: str):
    """Decorator to register a scraper class."""

    def decorator(cls: type["BaseScraper"]) -> type["BaseScraper"]:
        _scrapers[platform_name] = cls
        logger.info("Scraper registered", extra={"platform": platform_name})
        return cls

    return decorator


def get_scraper(platform_name: str, config: PlatformConfig) -> Optional["BaseScraper"]:
    """Get scraper instance for platform."""
    if platform_name not in _scrapers:
        return None
    scraper_class = _scrapers[platform_name]
    return scraper_class(platform_name, config)


def list_scrapers() -> list[str]:
    """Get list of registered scraper names."""
    return list(_scrapers.keys())
