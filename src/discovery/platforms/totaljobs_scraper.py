"""Totaljobs job scraper implementation."""

import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from src.config_manager import PlatformConfig
from .base_scraper import BaseScraper, register_scraper


@register_scraper("totaljobs")
class TotaljobsScraper(BaseScraper):
    """Scraper for Totaljobs job postings."""

    base_url = "https://www.totaljobs.com"
    jobs_per_page = 20

    def __init__(
        self, platform_name: str, config: PlatformConfig, rate_limit: int = 5
    ) -> None:
        """Initialize the Totaljobs scraper."""
        super().__init__(platform_name, config, rate_limit)

    def get_platform_name(self) -> str:
        """Get display name for platform."""
        return "Totaljobs"

    def build_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Build search URL with parameters."""
        base_url = "https://www.totaljobs.com/jobs"
        safe_query = query.replace(" ", "-")
        path = f"{safe_query}-jobs"
        if location:
            safe_loc = location.replace(" ", "-")
            path += f"/in-{safe_loc}"
        page = kwargs.get("page", 0)
        if page:
            path += f"?page={page}"
        return f"{base_url}/{path}"

    def get_search_url(
        self, query: str, location: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Get search URL (delegates to build_search_url)."""
        return self.build_search_url(query, location, **kwargs)

    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        """Extract job listing elements from search results."""
        return soup.select(".job-item, .job-card, .job-listing")

    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        """Parse a single job listing element."""
        job_id = (
            element.get("data-id") or element.get("data-job-id") or element.get("id")
        )
        title_elem = element.select_one("h2.job-title, .job-title, h2 a, h3 a")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"
        company_elem = element.select_one(".company, .employer")
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
        location_elem = element.select_one(".location, [itemprop=jobLocation]")
        location_text = (
            location_elem.get_text(strip=True) if location_elem else "Unknown"
        )
        salary_elem = element.select_one(".salary, [itemprop=baseSalary]")
        salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
        type_elem = element.select_one(".job-type, .type, .contract-type")
        type_text = type_elem.get_text(strip=True) if type_elem else ""
        return {
            "platform_id": job_id or "",
            "title": title,
            "company": company,
            "location": {"original": location_text},
            "salary": {**self._parse_salary(salary_text), "original": salary_text},
            "contract_type": self._parse_contract_type(type_text),
        }

    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information."""
        soup = self.fetch_page(job_url)
        if not soup:
            return None
        return {}

    def parse_salary(self, salary_text: str) -> dict[str, Any]:
        """Parse salary text into min, max, and currency."""
        return self._parse_salary(salary_text)

    def _parse_salary(self, salary_text: str) -> dict[str, Any]:
        """Parse salary text into min, max, and currency."""
        if not salary_text:
            return {"min": None, "max": None, "currency": None, "period": None}
        currency = "GBP"
        if "$" in salary_text:
            currency = "USD"
        elif "€" in salary_text:
            currency = "EUR"
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
        if "freelance" in lower or "contractor" in lower:
            return "contract"
        return None

    def calculate_posted_date(self, days_ago: int) -> str:
        """Calculate posted date based on days ago."""
        from datetime import datetime, timedelta

        date = datetime.now() - timedelta(days=days_ago)
        return date.strftime("%Y-%m-%d")
