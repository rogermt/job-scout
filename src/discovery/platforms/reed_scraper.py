"""Reed job scraper implementation."""

from datetime import datetime

import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from src.config_manager import PlatformConfig
from .base_scraper import BaseScraper, register_scraper


@register_scraper("reed")
class ReedScraper(BaseScraper):
    """Scraper for Reed job postings."""

    base_url = "https://www.reed.co.uk"
    jobs_per_page = 20

    def __init__(
        self, platform_name: str, config: PlatformConfig, rate_limit: int = 5
    ) -> None:
        """Initialize the Reed scraper."""
        super().__init__(platform_name, config, rate_limit)

    def get_platform_name(self) -> str:
        """Get display name for platform."""
        return "Reed"

    def build_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Build search URL with parameters."""
        base_url = "https://www.reed.co.uk/jobs"
        params = f'?keywords={query.replace(" ", "+")}'
        if location:
            params += f"&location={location}"
        if page := kwargs.get("page", 0):
            params += f"&page={page}"
        return f"{base_url}{params}"

    def get_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Get search URL (delegates to build_search_url)."""
        return self.build_search_url(query, location, **kwargs)

    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        """Extract job listing elements from search results."""
        return soup.select("article.job-result, article.job-card")

    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        """Parse a single job listing element."""
        # Try to get job ID from various sources
        job_id = (
            element.get("data-job-id") or element.get("data-id") or element.get("id")
        )

        # Get title
        title_elem = element.select_one(
            "h3.job-result-heading__title a, h2 a, .job-title a"
        )
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        # Get company
        company_elem = element.select_one("a.job-result-heading__employer, .company")
        company = company_elem.get_text(strip=True) if company_elem else ""

        # Get location
        location_elem = element.select_one("li.job-result-heading__meta, .location")
        location_text = location_elem.get_text(strip=True) if location_elem else ""
        location = {"original": location_text}

        # Get salary
        salary_elem = element.select_one("li.job-result-heading__salary, .salary")
        salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
        salary = self._parse_salary(salary_text)

        # Get contract type
        type_elem = element.select_one("li.job-result-heading__type, .type")
        type_text = type_elem.get_text(strip=True) if type_elem else ""
        contract_type = self._parse_contract_type(type_text)

        # Detect remote policy from location text
        remote_policy = ""
        remote_types = []
        if location_text:
            location_lower = location_text.lower()
            if "remote" in location_lower:
                if "hybrid" in location_lower:
                    remote_policy = "hybrid"
                    remote_types = ["partial"]
                else:
                    remote_policy = "fully-remote"
                    remote_types = ["full"]

        return {
            "platform_id": job_id or "",
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "contract_type": contract_type,
            "remote_policy": remote_policy or "",
            "remote_types": remote_types or [],
        }

    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information."""
        soup = self.fetch_page(job_url)
        if not soup:
            return None

        # Handle both BeautifulSoup and string (for mocked tests)
        if isinstance(soup, str):
            soup = BeautifulSoup(soup, "html.parser")

        # Extract job description
        desc_elem = soup.select_one(
            ".job-description__content, #job-description, .description"
        )
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract canonical URL if available, otherwise use job_url
        canonical_elem = soup.select_one("link[rel='canonical']")
        url = canonical_elem.get("href") if canonical_elem else job_url

        return {
            "url": url,
            "description": description,
        }

    def get_job_details_browser(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information using browser."""
        page = self.fetch_page_browser(job_url)
        if not page:
            return None

        # Use Scrapling's CSS selector - ::text applies to every selector
        desc_elem = page.css(
            ".job-description__content::text, #job-description::text, .description::text"
        )
        description = desc_elem[0].strip() if desc_elem else ""

        return {
            "url": job_url,
            "description": description,
        }

    def parse_salary(self, salary_text: str) -> dict[str, Any]:
        """Parse salary text into min, max, and currency."""
        return self._parse_salary(salary_text)

    def parse_job_listing_browser(self, element: Any) -> Optional[dict[str, Any]]:
        """Parse a job listing from browser page (Reed-specific)."""
        # Get title - use targeted selector like HTTP version
        links = element.css("h3.job-result-heading__title a, h2 a, .job-title a")
        title = links[0].text.strip() if links else "Unknown"

        # Get URL for platform_id
        url = links[0].attrib.get("href", "") if links else ""

        # Get company
        companies = element.css(".employer, .company")
        company = companies[0].text.strip() if companies else ""

        # Get location
        locs = element.css(".location, li.job-result-heading__meta")
        location_text = locs[0].text.strip() if locs else ""
        location = {"original": location_text}

        # Get salary
        salary_elem = element.css("li.job-result-heading__salary, .salary")
        salary_text = salary_elem[0].text.strip() if salary_elem else ""
        salary = self._parse_salary(salary_text)

        # Get contract type
        type_elem = element.css("li.job-result-heading__type, .type")
        type_text = type_elem[0].text.strip() if type_elem else ""
        contract_type = self._parse_contract_type(type_text)

        # Detect remote policy from location text
        remote_policy = ""
        remote_types = []
        if location_text:
            location_lower = location_text.lower()
            if "remote" in location_lower or "home" in location_lower:
                remote_policy = "remote"
                remote_types = ["remote"]

        # Extract platform_id from URL if possible
        platform_id = None
        if "job" in url:
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part == "job" and i + 1 < len(parts):
                    platform_id = parts[i + 1]
                    break

        return {
            "platform_id": platform_id,
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "contract_type": contract_type,
            "remote_policy": remote_policy,
            "remote_types": remote_types,
            "url": url,
            "platform": "reed",
        }

    def _parse_salary(self, salary_text: str) -> dict[str, Any]:
        """Parse salary text into min, max, and currency."""
        if not salary_text:
            return {"min": None, "max": None, "currency": None, "period": None}
        currency = "GBP"
        if "$" in salary_text:
            currency = "USD"
        elif "€" in salary_text:
            currency = "EUR"

        # Determine period
        period = "yearly"
        if "per day" in salary_text.lower() or "/day" in salary_text.lower():
            period = "daily"
        elif "per month" in salary_text.lower() or "/month" in salary_text.lower():
            period = "monthly"
        elif "hour" in salary_text.lower() or "/hour" in salary_text.lower():
            period = "hourly"

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
                "period": period,
            }
        return {"min": None, "max": None, "currency": currency, "period": period}

    def parse_posted_date(self, text: str) -> Optional[datetime]:
        """Parse posted date text into datetime."""
        match = re.search(r"(\d+)\s+days?\s+ago", text, re.IGNORECASE)
        if match:
            days = int(match.group(1))
            from datetime import timedelta

            return datetime.utcnow() - timedelta(days=days)
        return None

    def _parse_posted_date(self, text: str) -> Optional[str]:
        """Parse posted date text into date string."""
        match = re.search(r"(\d+)\s+days?\s+ago", text, re.IGNORECASE)
        if match:
            days = int(match.group(1))
            return self.calculate_posted_date(days)
        return None

    def is_remote_job(self, element: Tag) -> bool:
        """Check if job is remote."""
        return self._is_remote_job(element.get_text(strip=True), "")

    def _is_remote_job(self, title: str, location: str) -> bool:
        """Check if job is remote based on title and location."""
        title_lower = title.lower()
        location_lower = location.lower()
        if "remote" in title_lower or "work from home" in title_lower:
            return True
        # Use word boundary for "anywhere" to avoid false positives
        if re.search(r"\banywhere\b", location_lower):
            return True
        return False

    def _parse_contract_type(self, contract_type: str) -> Optional[str]:
        """Parse contract type string."""
        if not contract_type:
            return None
        lower = contract_type.lower()
        if "permanent" in lower:
            return "permanent"
        if "fixed term" in lower or "contract" in lower:
            return "contract"
        if "temporary" in lower:
            return "temporary"
        if "part" in lower:
            return "part-time"
        if "freelance" in lower or "contractor" in lower:
            return "contract"
        return None

    def calculate_posted_date(self, days_ago: int) -> str:
        """Calculate posted date based on days ago."""
        from datetime import datetime, timedelta

        date = datetime.now() - timedelta(days=days_ago)
        return date.strftime("%Y-%m-%d")
