from datetime import datetime, timedelta
import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from src.config_manager import PlatformConfig
from .base_scraper import BaseScraper


class CvlibraryScraper(BaseScraper):
    base_url = "https://www.cvlibrary.co.uk"
    jobs_per_page = 20

    def __init__(self, platform_name: str, config: PlatformConfig, rate_limit: int = 5):
        super().__init__(platform_name, config, rate_limit)

    def get_platform_name(self) -> str:
        return "CV-Library"

    def build_search_url(
        self, query: str, location: Optional[str] = None, **kwargs
    ) -> str:
        base_url = "https://www.cvlibrary.co.uk/search-jobs"
        keywords = query.replace(" ", "+")
        query_params = f"?keywords={keywords}"
        if location:
            loc = location.replace(" ", "+")
            query_params += f"&location={loc}"
        if page := kwargs.get("page", 0):
            query_params += f"&page={page}"
        return f"{base_url}{query_params}"

    def get_search_url(
        self, query: str, location: Optional[str] = None, **kwargs
    ) -> str:
        return self.build_search_url(query, location, **kwargs)

    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        return soup.select("article.job-card, div.job-results-item")

    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        job_id = element.get("data-job-id") or element.get("id", "")

        title_elem = element.select_one("h3.title a, h2 a.job-title")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        company_elem = element.select_one("span.company-name, a.company")
        company = company_elem.get_text(strip=True) if company_elem else ""

        location_elem = element.select_one("span.location, li.location")
        location_text = location_elem.get_text(strip=True) if location_elem else ""
        location = {"original": location_text}

        salary_elem = element.select_one("span.salary, li.salary")
        salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
        salary = self._parse_salary(salary_text)

        url_elem = element.select_one("h3.title a, a.job-title")
        url = url_elem.get("href", "") if url_elem else ""
        if url and not url.startswith("http"):
            url = f"{self.base_url}{url}"

        posted_elem = element.select_one("span.posted-date, .date-posted")
        posted_text = posted_elem.get_text(strip=True) if posted_elem else ""
        posted_date = self._parse_posted_date(posted_text)

        description_elem = element.select_one("p.summary, .job-description")
        description = description_elem.get_text(strip=True) if description_elem else ""

        return {
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "url": url,
            "posted_date": posted_date,
            "description": description,
            "platform_id": str(job_id),
            "platform": self.platform_name,
        }

    def _parse_salary(self, salary_text: str) -> dict[str, Any]:
        if not salary_text:
            return {"min": None, "max": None, "currency": "GBP", "period": "yearly"}

        numbers = re.findall(r"[\n,]+", salary_text.replace(",", ""))
        if numbers:
            min_salary = int(numbers[0])
            max_salary = int(numbers[-1]) if len(numbers) > 1 else min_salary

            period = "yearly"
            if "day" in salary_text.lower():
                period = "daily"
            elif "week" in salary_text.lower():
                period = "weekly"
            elif "month" in salary_text.lower():
                period = "monthly"

            return {
                "min": min_salary,
                "max": max_salary,
                "currency": "GBP",
                "period": period,
            }

        return {"min": None, "max": None, "currency": "GBP", "period": "yearly"}

    def _parse_posted_date(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        days_match = re.search(r"(\d+)\s*day", text_lower)
        if days_match:
            days = int(days_match.group(1))
            return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        weeks_match = re.search(r"(\d+)\s*week", text_lower)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")

        return None

    def has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        next_btn = soup.select_one("a.next-page, li.next a")
        return next_btn is not None

    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        soup = self.fetch_page(job_url)
        if not soup:
            return None

        title_elem = soup.select_one("h1.job-title, h1")
        title = title_elem.get_text(strip=True) if title_elem else ""

        company_elem = soup.select_one("span.company-name, .company")
        company = company_elem.get_text(strip=True) if company_elem else ""

        description_elem = soup.select_one("div.job-description, .description")
        description = description_elem.get_text(strip=True) if description_elem else ""

        return {
            "title": title,
            "company": company,
            "description": description,
            "url": job_url,
        }
