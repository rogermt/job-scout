"""Stack Overflow Jobs scraper for UK and remote positions.

This module provides a scraper for Stack Overflow Jobs with UK location filtering.
Primarily focused on tech/engineering roles (perfect for the UK market).
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_scraper import BaseScraper, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("stackoverflow")
class StackOverflowScraper(BaseScraper):
    """Scraper for Stack Overflow Jobs with UK and remote focus."""
    
    def __init__(self, platform_name: str, config: Dict[str, Any]) -> None:
        """Initialize StackOverflow scraper.
        
        Args:
            config: Configuration dictionary for StackOverflow scraper
        """
        super().__init__(config)
        self.base_url = "https://stackoverflow.com/jobs"
        self.api_url = "https://stackoverflow.com/jobs/feed"
        logger.info("StackOverflow scraper initialized")
    
    def build_search_url(self, query: str, location: Optional[str], page: int = 1) -> str:
        """Build Stack Overflow Jobs search URL.
        
        Args:
            query: Job search query
            location: Location filter (will prioritize UK/remote)
            page: Page number (1-indexed)
            
        Returns:
            Stack Overflow Jobs search URL
        """
        # Stack Overflow uses q query parameter
        params = {
            "q": query,
        }
        
        # Set UK location filter or use provided location
        if location:
            params["l"] = location
        elif self.config.get("uk_focus", True):
            params["l"] = "United Kingdom"
        
        # Remote filter
        if self.config.get("remote_only", False):
            params["r"] = "true"
        
        url = f"{self.base_url}?{urlencode(params)}"
        
        if page > 1:
            url += f"&pg={page}"
        
        return url
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _fetch_page(self, url: str) -> str:
        """Fetch page with retry logic."""
        return super()._fetch_page(url)
    
    def scrape_jobs(self, query: str, location: Optional[str], max_pages: int = 3) -> Generator[Dict[str, Any], None, None]:
        """Scrape jobs from Stack Overflow.
        
        Args:
            query: Job search query
            location: Location filter
            max_pages: Maximum pages to scrape
            
        Yields:
            Job data dictionaries
        """
        for page in range(1, max_pages + 1):
            url = self.build_search_url(query, location, page)
            logger.debug("Fetching Stack Overflow page", extra={"url": url, "page": page})
            
            try:
                html = self._fetch_page(url)
                jobs_found = 0
                
                for job_data in self._parse_jobs(html):
                    jobs_found += 1
                    # Filter for UK or remote jobs
                    if self._meets_uk_criteria(job_data):
                        yield job_data
                
                logger.debug("Stack Overflow page scraped", extra={"page": page, "jobs": jobs_found})
                
                # Check if there are more pages by looking for pagination
                if not self._has_more_pages(html, page):
                    break
                    
            except Exception as e:
                logger.error("Error scraping Stack Overflow page", extra={
                    "page": page,
                    "error": str(e),
                    "url": url
                }, exc_info=True)
                break
    
    def _has_more_pages(self, html: str, current_page: int) -> bool:
        """Check if there are more pages available.
        
        Args:
            html: HTML content to parse
            current_page: Current page number
            
        Returns:
            True if more pages exist
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Look for pagination controls
        pagination = soup.find("div", class_="s-pagination")
        if not pagination:
            return False
        
        # Check next button
        next_button = pagination.find("a", rel="next")
        if not next_button or "disabled" in next_button.get("class", []):
            return False
        
        return True
    
    def _parse_jobs(self, html: str) -> Generator[Dict[str, Any], None, None]:
        """Parse job listings from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Stack Overflow job cards have class "-job"
        job_cards = soup.find_all("div", class_="-job")
        
        for card in job_cards:
            try:
                job_data = self._parse_job_card(card)
                if job_data:
                    yield job_data
            except Exception as e:
                logger.warning("Failed to parse Stack Overflow job card", 
                              extra={"error": str(e)}, exc_info=True)
                continue
    
    def _parse_job_card(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse individual job card.
        
        Args:
            card: BeautifulSoup job card element
            
        Returns:
            Job data dictionary or None if parsing failed
        """
        # Check if it's a job listing (not an ad)
        if card.get("data-jobid"):
            job_id_from_page = card["data-jobid"]
        else:
            job_id_from_page = None
        
        # Extract job title and link
        title_link = card.find("h2", class_="mb4").find("a", href=True) if card.find("h2", class_="mb4") else None
        if not title_link:
            title_link = card.find("a", class_="s-link", href=True)
        
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        job_path = title_link["href"]
        
        if job_path.startswith("/jobs/"):
            job_url = urljoin("https://stackoverflow.com", job_path)
        else:
            job_url = job_path
        
        # Extract company
        company_elem = card.find("div", class_="fc-black-700").find("span") if card.find("div", class_="fc-black-700") else None
        if not company_elem:
            company_elem = card.find("h3", class_="fc-black-700")
        company = company_elem.get_text(strip=True) if company_elem else ""
        
        # Extract location
        location_elem = card.find("span", class_="fc-black-500")
        location = location_elem.get_text(strip=True) if location_elem else ""
        
        # Extract tags/technologies
        tags_container = card.find("div", class_="mt12")
        tags = []
        if tags_container:
            tag_elems = tags_container.find_all("a", class_="s-tag")
            tags = [tag.get_text(strip=True) for tag in tag_elems]
        
        # Determine remote policy
        remote_policy = "none"
        remote_types = []
        
        if location and "remote" in location.lower():
            remote_policy = "remote"
            remote_types = ["remote"]
        
        # Check for remote symbol
        remote_symbol = card.find("svg", class_="fc-blue-500")
        if remote_symbol or (location and "anywhere"):
            remote_policy = "remote"
            remote_types = ["remote"]
        
        # Extract salary (Stack Overflow has limited salary info)
        salary_elem = card.find("span", class_="salary") or card.find(text=re.compile(r"£|\$|€|,000"))
        salary_str = salary_elem if isinstance(salary_elem, str) else salary_elem.get_text(strip=True) if salary_elem else ""
        salary_data = self._parse_salary(salary_str)
        
        # Extract posted date
        posted_elem = card.find("span", class_="fc-orange-400")
        posted_date = self._parse_relative_time(posted_elem.get_text(strip=True)) if posted_elem else datetime.now(timezone.utc)
        
        # Extract job type/contract
        job_type = "permanent"  # Most SO jobs are permanent, but we'll parse if available
        
        # Generate unique job ID
        job_id = job_id_from_page or self._generate_id(job_url, title, company)
        
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "url": job_url,
            "location": {
                "original": location,
                "city": None,
                "country": "United Kingdom" if "UK" in location or "United Kingdom" in location else None,
            },
            "salary": salary_data,
            "remote_policy": remote_policy,
            "remote_types": remote_types,
            "contract_type": job_type,
            "posted_date": posted_date,
            "description": f"Technologies: {', '.join(tags[:5])}",  # Basic description from tags
            "platform": self.platform_name,
            "industry": "technology",
            "experience_level": None,
            "skills": tags[:10],  # First 10 tags as skills
        }
    
    def _parse_salary(self, salary_str: str) -> Dict[str, Any]:
        """Parse salary string into structured data.
        
        Stack Overflow rarely shows salary, but parse if available.
        """
        salary_data = {
            "min": None,
            "max": None,
            "currency": None,
            "period": None,
            "original": salary_str,
        }
        
        if not salary_str:
            return salary_data
        
        # Extract currency
        if "£" in salary_str:
            currency = "GBP"
        elif "$" in salary_str:
            currency = "USD"
        elif "€" in salary_str:
            currency = "EUR"
        else:
            currency = None
        
        # Extract period
        period_weights = {
            "per annum": "yearly",
            "per year": "yearly",
            "per month": "monthly",
            "per day": "daily",
            "per hour": "hourly",
        }
        
        period = None
        for keyword, p in period_weights.items():
            if keyword in salary_str.lower():
                period = p
                break
        
        # Extract numbers
        numbers = re.findall(r'\d+\.?\d*', salary_str.replace(",", ""))
        
        if len(numbers) >= 2:
            salary_data["min"] = int(float(numbers[0]))
            salary_data["max"] = int(float(numbers[1]))
        elif len(numbers) == 1:
            salary_data["min"] = int(float(numbers[0]))
            salary_data["max"] = int(float(numbers[0]))
        
        salary_data["currency"] = currency
        salary_data["period"] = period
        
        return salary_data
    
    def _parse_relative_time(self, time_text: str) -> datetime:
        """Parse relative time like '2 days ago' or 'posted 3 hours ago'."""
        now = datetime.now(timezone.utc)
        
        # Extract numbers and units
        matches = re.findall(r'(\d+)?\s*(minute|hour|day|week|month)s?\s*ago', time_text, re.I)
        
        if not matches:
            return now
        
        amount_str, unit = matches[0]
        amount = int(amount_str) if amount_str else 1
        
        unit = unit.lower()
        
        if unit.startswith("minute"):
            return now - timedelta(minutes=amount)
        elif unit.startswith("hour"):
            return now - timedelta(hours=amount)
        elif unit.startswith("day"):
            return now - timedelta(days=amount)
        elif unit.startswith("week"):
            return now - timedelta(weeks=amount)
        elif unit.startswith("month"):
            return now - timedelta(days=amount * 30)  # Approximate
        
        return now
    
    def _meets_uk_criteria(self, job_data: Dict[str, Any]) -> bool:
        """Check if job meets UK criteria.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            True if job is UK-based or remote
        """
        location = job_data.get("location", {}).get("original", "")
        
        # Check if UK location
        uk_indicators = ["UK", "United Kingdom", "Britain", "England", "Scotland", "Wales", "Northern Ireland"]
        for indicator in uk_indicators:
            if indicator in location:
                return True
        
        # Check if remote
        remote_policy = job_data.get("remote_policy", "none")
        remote_types = job_data.get("remote_types", [])
        
        if remote_policy != "none" or len(remote_types) > 0:
            return True
        
        # Default: return True for Stack Overflow (high quality tech jobs)
        return True
    
    def _generate_id(self, url: str, title: str, company: str) -> str:
        """Generate unique job ID."""
        return super()._generate_id(url, title, company)
    
    def scrape_job_details(self, job_url: str) -> Optional[str]:
        """Scrape full job description from job detail page."""
        try:
            html = self._fetch_page(job_url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Stack Overflow job description container
            desc_elem = soup.find("div", class_="job-description")
            
            if not doc_elem:
                # Alternative selectors
                desc_elem = soup.find("section", class_=re.compile("description", re.I))
            
            if not desc_elem:
                desc_elem = soup.find("div", {"itemprop": "description"})
            
            if desc_elem:
                return desc_elem.get_text("\n", strip=True)
            
            return None
        except Exception as e:
            logger.error("Failed to scrape job details", 
                        extra={"url": job_url, "error": str(e)}, exc_info=True)
            return None
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Stack Overflow Jobs"