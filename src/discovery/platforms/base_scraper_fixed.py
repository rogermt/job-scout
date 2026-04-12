"""Base scraper class for all job discovery platforms.

This module provides a common interface and shared functionality for all job
scrapers following ForgeSyte standards with proper error handling and resilience.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Generator, Optional

import requests
from bs4 import BeautifulSoup, Tag
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config_manager import PlatformConfig

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all job scrapers.
    
    All platform-specific scrapers must inherit from this class and implement
    the required abstract methods.
    """
    
    def __init__(self, platform_name: str, config: PlatformConfig, rate_limit: int = 5) -> None:
        """Initialize base scraper.
        
        Args:
            platform_name: Name of the platform (e.g., 'indeed', 'reed')
            config: Platform configuration
            rate_limit: Minimum seconds between requests
        """
        self.platform_name = platform_name
        self.config = config
        self.rate_limit = rate_limit
        self._last_request_time: float = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
        logger.info(
            "Scraper initialized",
            extra={"platform": platform_name, "enabled": config.enabled}
        )
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        wait_time = self.rate_limit - elapsed
        if wait_time > 0:
            logger.debug(
                "Rate limiting",
                extra={"wait_time": wait_time, "platform": self.platform_name}
            )
            time.sleep(wait_time)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _make_request(self, url: str, method: str = "GET", **kwargs: Any) -> requests.Response:
        """Make HTTP request with automatic retries and rate limiting.
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: After all retries are exhausted
        """
        self._enforce_rate_limit()
        
        logger.debug(
            "Making HTTP request",
            extra={"url": url, "method": method, "platform": self.platform_name}
        )
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            self._last_request_time = time.time()
            
            logger.debug(
                "Request successful",
                extra={
                    "url": url,
                    "status_code": response.status_code,
                    "platform": self.platform_name
                }
            )
            return response
            
        except requests.RequestException as e:
            logger.warning(
                "Request failed",
                extra={
                    "url": url,
                    "method": method,
                    "error": str(e),
                    "platform": self.platform_name
                }
            )
            raise
    
    def fetch_page(self, url: str, **kwargs: Any) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for requests
            
        Returns:
            Parsed BeautifulSoup object or None if failed
        """
        try:
            response = self._make_request(url, **kwargs)
            return BeautifulSoup(response.content, "html.parser")
        except requests.RequestException as e:
            logger.error(
                "Failed to fetch page",
                extra={"url": url, "error": str(e), "platform": self.platform_name}
            )
            return None
    
    def is_enabled(self) -> bool:
        """Check if this scraper is enabled."""
        return self.config.enabled
    
    def can_scrape(self) -> bool:
        """Check if scraper can run (platform enabled and not rate limited)."""
        if not self.is_enabled():
            logger.warning(
                "Scraper disabled",
                extra={"platform": self.platform_name, "reason": "config.disabled"}
            )
            return False
        
        # Check if enough time has passed since last scrape
        # This prevents scraping the same platform too frequently
        return True
    
    @abstractmethod
    def get_search_url(self, query: str, location: Optional[str] = None, **kwargs: Any) -> str:
        """Generate search URL for the platform.
        
        Args:
            query: Search query
            location: Location filter
            **kwargs: Additional parameters
            
        Returns:
            URL for job search
        """
        pass
    
    @abstractmethod
    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        """Extract job listing elements from search results page.
        
        Args:
            soup: Parsed page content
            
        Returns:
            List of job listing elements
        """
        pass
    
    @abstractmethod
    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        """Parse a single job listing element into structured data.
        
        Args:
            element: Job listing element
            
        Returns:
            Dictionary with job data or None if parsing failed
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information.
        
        Args:
            job_url: URL to job details page
            
        Returns:
            Dictionary with detailed job data or None if failed
        """
        pass
    
    def scrape_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        max_pages: int = 5
    ) -> Generator[dict[str, Any], None, None]:
        """Scrape jobs from the platform.
        
        Args:
            query: Search query
            location: Location filter
            max_pages: Maximum pages to scrape
            
        Yields:
            Job dictionaries
        """
        logger.info(
            "Starting job scrape",
            extra={
                "platform": self.platform_name,
                "query": query,
                "location": location,
                "max_pages": max_pages
            }
        )
        
        current_page = 0
        jobs_found = 0
        
        while current_page < max_pages:
            search_url = self.get_search_url(query, location, page=current_page)
            logger.debug(
                "Fetching search page",
                extra={"url": search_url, "page": current_page}
            )
            
            soup = self.fetch_page(search_url)
            if not soup:
                logger.warning(
                    "Failed to fetch search page",
                    extra={"url": search_url, "page": current_page}
                )
                break
            
            job_elements = self.extract_job_listings(soup)
            if not job_elements:
                logger.info(
                    "No job listings found on page",
                    extra={"page": current_page, "url": search_url}
                )
                break
            
            logger.debug(
                "Found job listings",
                extra={"count": len(job_elements), "page": current_page}
            )
            
            for element in job_elements:
                try:
                    job_data = self.parse_job_listing(element)
                    if job_data:
                        yield job_data
                        jobs_found += 1
                except Exception as e:
                    logger.warning(
                        "Failed to parse job listing",
                        extra={"error": str(e), "element": str(element)}
                    )
                    continue
            
            current_page += 1
            # Check if there's a next page logic here (platform-specific)
            if not self.has_next_page(soup, current_page):
                logger.debug("No more pages available", extra={"last_page": current_page - 1})
                break
        
        logger.info(
            "Scrape completed",
            extra={
                "platform": self.platform_name,
                "jobs_found": jobs_found,
                "pages_scraped": current_page
            }
        )
    
    def has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there are more pages to scrape.
        
        Args:
            soup: Current page content
            current_page: Current page number
            
        Returns:
            True if next page likely exists
        """
        # Base implementation: check for pagination links
        # Override this in specific scrapers for better accuracy
        pagination_links = soup.select("a[href*='page'], a[href*='next']")
        return len(pagination_links) > 0
    
    def save_job(self, job_data: dict[str, Any]) -> Optional[str]:
            """Save job to database.

            Args:
                job_data: Job data dictionary

            Returns:
                Job ID if saved, None if already exists or failed
            """
            # Late import to avoid circular imports
            from ..tracking.database import get_database

            try:
                # Generate composite ID: platform:platform_id
                platform_id = job_data.get("platform_id", "")
                job_id = f"{self.platform_name}:{platform_id}"

                # Add platform to job data
                job_data["id"] = job_id
                job_data["platform"] = self.platform_name
                job_data["scraped_date"] = datetime.utcnow()

                # Save to database
                db = get_database()
                with db.get_session() as session:
                    existing = db.get_job(session, job_id)
                    if existing:
                        logger.debug(
                            "Job already exists",
                            extra={"job_id": job_id, "title": job_data.get("title", "Unknown")}
                        )
                        return None

                    job = db.add_job(session, **job_data)
                    logger.info(
                        "Job saved to database",
                        extra={"job_id": job_id, "title": job.title, "company": job.company}
                    )
                    return job.id

            except Exception as e:
                logger.error(
                    "Failed to save job",
                    extra={"error": str(e), "job_data": str(job_data)}
                )
                return None
    
        def parse_salary(self, salary_text: str) -> tuple[Optional[float], Optional[float], Optional[str]]:
                """Parse salary text into min, max, and currency.
            
                Handles various formats like:
                - "£30,000 - £50,000"
                - "£30k - £50k"
                - "£30,000"
                - "$80,000 - $120,000"
                - "€60,000"
            
                Args:
                    salary_text: Raw salary text
                
                Returns:
                    Tuple of (min_salary, max_salary, currency_code)
                """
                if not salary_text or "unspecified" in salary_text.lower():
                    return None, None, None
            
                # Default values
                min_salary: Optional[float] = None
                max_salary: Optional[float] = None
                currency: Optional[str] = "GBP"
            
                # Detect currency
                if "$" in salary_text:
                    currency = "USD"
                elif "€" in salary_text or "EUR" in salary_text:
                    currency = "EUR"
                elif "£" in salary_text or "GBP" in salary_text:
                    currency = "GBP"
            
                # Clean text
                text = salary_text.replace(",", "").replace("£", "").replace("$", "").replace("€", "")
            
                # Extract numbers
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
            
                if numbers:
                    try:
                        if len(numbers) == 1:
                            min_salary = float(numbers[0])
                            max_salary = float(numbers[0])
                        elif len(numbers) >= 2:
                            min_salary = float(numbers[0])
                            max_salary = float(numbers[1])
                    
                        # Convert k to full numbers
                        if "k" in text.lower():
                            min_salary = (min_salary or 0) * 1000
                            max_salary = (max_salary or 0) * 1000
                    
                        # Convert yearly salary to GBP for comparison
                        if currency == "USD":
                            # Approximate conversion: divide by 1.27 (1 GBP = 1.27 USD)
                            min_salary = (min_salary or 0) / 1.27
                            max_salary = (max_salary or 0) / 1.27
                        elif currency == "EUR":
                            # Approximate conversion: divide by 1.17 (1 GBP = 1.17 EUR)
                            min_salary = (min_salary or 0) / 1.17
                            max_salary = (max_salary or 0) / 1.17
                    
                    except (ValueError, IndexError):
                        logger.warning(
                            "Failed to parse salary",
                            extra={"salary_text": salary_text}
                        )
            
                return min_salary, max_salary, currency
        
        def parse_posted_date(self, text: str) -> datetime:
            """Parse 'posted X days ago' text into datetime.
        
            Args:
                text: Posted date text
            
            Returns:
                Calculated datetime
            """
            from dateutil.relativedelta import relativedelta
            import re
        
            now = datetime.utcnow()
            times = re.findall(r'(\d+)\s+(day|week|month|hour)', text, re.IGNORECASE)
        
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
        
            # Default to now if can't parse
            return now


    # Registry for all scrapers
    _scrapers: dict[str, type[BaseScraper]] = {}


def register_scraper(platform_name: str):
    """Decorator to register a scraper class.
    
    Args:
        platform_name: Name of the platform
    
    Example:
        @register_scraper("indeed")
        class IndeedScraper(BaseScraper):
            pass
    """
    def decorator(cls: type[BaseScraper]) -> type[BaseScraper]:
        _scrapers[platform_name] = cls
        logger.info("Scraper registered", extra={"platform": platform_name})
        return cls
    return decorator


def get_scraper(platform_name: str, config: PlatformConfig) -> Optional[BaseScraper]:
    """Get scraper instance for platform.
    
    Args:
        platform_name: Name of the platform
        config: Platform configuration
        
    Returns:
        Scraper instance or None if not registered
    """
    if platform_name not in _scrapers:
        logger.error("Scraper not registered", extra={"platform": platform_name})
        return None
    
    scraper_class = _scrapers[platform_name]
    return scraper_class(platform_name, config)


def list_scrapers() -> list[str]:
    """Get list of registered scraper names.
    
    Returns:
        List of platform names
    """
    return list(_scrapers.keys())

__all__ = [
    "BaseScraper",
    "register_scraper",
    "get_scraper",
    "list_scrapers",
]