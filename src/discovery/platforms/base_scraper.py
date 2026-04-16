"""Base scraper class for all job discovery platforms."""

import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, NotRequired, Optional, TypedDict

import requests
from bs4 import BeautifulSoup, Tag
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config_manager import PlatformConfig

logger = logging.getLogger(__name__)


class SalaryPeriod(str, Enum):
    """Salary period enumeration."""

    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    HOURLY = "hourly"


# Period-to-yearly multipliers (data-driven, no if-elif ladder)
# Using only string keys since SalaryPeriod is a str-subclass, enum values match string lookups
PERIOD_TO_YEARLY_MULTIPLIERS: dict[str | None, Decimal] = {
    "yearly": Decimal("1"),
    "monthly": Decimal("12"),
    "weekly": Decimal("52"),
    "daily": Decimal("260"),
    "hourly": Decimal("2080"),
    None: Decimal("1"),
}


class SalaryData(TypedDict, total=False):
    """Structured salary data with Decimal precision."""

    min: Decimal | None
    max: Decimal | None
    currency: str | None
    period: str | None
    original: NotRequired[str]


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
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
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
    ) -> list[dict[str, Any]]:
        """Scrape jobs from the platform. Returns list for compatibility."""
        jobs = []
        current_page = 0
        while current_page < max_pages:
            search_url = self.get_search_url(query, location, page=current_page)
            soup = self.fetch_page(search_url)
            if not soup:
                # If no response, try sample fallback
                if hasattr(self, "_get_sample_jobs"):
                    sample_jobs = self._get_sample_jobs(query, location)
                    if sample_jobs:
                        return sample_jobs
                break
            job_elements = self.extract_job_listings(soup)
            if not job_elements:
                # Try sample fallback if no jobs found
                if hasattr(self, "_get_sample_jobs"):
                    sample_jobs = self._get_sample_jobs(query, location)
                    if sample_jobs:
                        return sample_jobs
                break
            for element in job_elements:
                job_data = self.parse_job_listing(element)
                if job_data:
                    jobs.append(job_data)
            current_page += 1

        return jobs

    def has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there are more pages to scrape."""
        pagination_links = soup.select("a[href*='page'], a[href*='next']")
        return len(pagination_links) > 0

    def parse_salary(self, salary_text: str) -> SalaryData:
        """Parse salary text into Decimal min/max + currency + period.

        Args:
            salary_text: Raw salary string (e.g., "£30k - £40k per annum")

        Returns:
            SalaryData with Decimal precision for financial values
        """
        if not salary_text:
            return {
                "min": None,
                "max": None,
                "currency": None,
                "period": None,
                "original": "",
            }

        text_lower = salary_text.lower()

        # Currency detection (data-driven)
        currency_indicators = {
            "GBP": ["£", "gbp"],
            "USD": ["$", "usd"],
            "EUR": ["€", "eur"],
        }
        currency: str | None = None
        for curr, indicators in currency_indicators.items():
            if any(ind in salary_text or ind in text_lower for ind in indicators):
                currency = curr
                break

        # Period detection (data-driven)
        period_keywords = {
            SalaryPeriod.DAILY: ["per day", "/day", "daily"],
            SalaryPeriod.WEEKLY: ["per week", "/week", "weekly"],
            SalaryPeriod.MONTHLY: ["per month", "/month", "monthly"],
            SalaryPeriod.HOURLY: ["per hour", "/hour", "hourly"],
        }
        period: str = SalaryPeriod.YEARLY.value  # Default
        for prd, keywords in period_keywords.items():
            if any(kw in text_lower for kw in keywords):
                period = prd.value
                break

        # Normalize and extract numbers
        normalized = (
            salary_text.replace(",", "")
            .replace("£", "")
            .replace("$", "")
            .replace("€", "")
        )

        # Remove percentage tokens (e.g. "10% bonus") before salary extraction
        cleaned = re.sub(r"\d+(?:\.\d+)?\s*%", "", normalized)
        # Capture numbers with optional k/m suffix
        matches = re.findall(r"(\d+(?:\.\d+)?)\s*([kKmM])?", cleaned)
        amounts: list[Decimal] = []
        for value, suffix in matches:
            d = Decimal(value)
            if suffix and suffix.lower() == "k":
                d *= Decimal("1000")
            elif suffix and suffix.lower() == "m":
                d *= Decimal("1000000")
            amounts.append(d)

        if not amounts:
            return {
                "min": None,
                "max": None,
                "currency": currency,
                "period": period,
                "original": salary_text,
            }

        min_sal = min(amounts)
        max_sal = max(amounts)
        return {
            "min": min_sal,
            "max": max_sal,
            "currency": currency,
            "period": period,
            "original": salary_text,
        }

    def parse_posted_date(self, text: str) -> Optional[datetime]:
        """Parse 'posted X days ago' text into datetime."""
        import re
        from dateutil.relativedelta import relativedelta

        now = datetime.utcnow()
        times = re.findall(r"(\d+)\s+(day|week|month|hour)", text, re.IGNORECASE)
        if times:
            amount = int(times[0][0])
            unit = times[0][1].lower()
            if "day" in unit:
                return now - relativedelta(days=amount)
            elif "week" in unit:
                return now - relativedelta(weeks=amount)
            elif "month" in unit:
                return now - relativedelta(months=amount)
            elif "hour" in unit:
                return now - relativedelta(hours=amount)
        return None


_scrapers: dict[str, type["BaseScraper"]] = {}


def register_scraper(platform_name: str):
    """Decorator to register a scraper class."""

    def decorator(cls: type["BaseScraper"]) -> type["BaseScraper"]:
        if not issubclass(cls, BaseScraper):
            raise TypeError(f"{cls.__name__} must be a subclass of BaseScraper")
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
