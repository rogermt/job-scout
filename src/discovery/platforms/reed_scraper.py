"""Reed.co.uk scraper for UK job listings.

This module provides a scraper for Reed.co.uk, a major UK job platform.
It follows the BaseScraper pattern and implements all required methods.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_scraper import BaseScraper, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("reed")
class ReedScraper(BaseScraper):
    """Scraper for Reed.co.uk job listings."""
    
    def __init__(self, platform_name: str, config: Dict[str, Any]) -> None:
        """Initialize Reed scraper.
        
        Args:
            platform_name: Platform name (should be 'reed')
            config: Configuration dictionary for Reed scraper
        """
        # BaseScraper expects platform_name first, then config
        super().__init__(platform_name, config)
        self.base_url = "https://www.reed.co.uk"
        self.jobs_per_page = 20        
    def build_search_url(self, query: str, location: Optional[str], page: int = 1) -> str:
        """Build Reed search URL.
        
        Args:
            query: Job search query
            location: Location filter
            page: Page number (1-indexed)
            
        Returns:
            Reed search URL
        """
        params = {
            "keywords": query,
        }
        
        if location:
            params["location"] = location
        
        # Reed uses URL segments for pagination
        if page > 1:
            url = f"{self.base_url}/jobs?keywords={query}"
            if location:
                url += f"&location={location}"
            url += f"&page={page}"
        else:
            url = f"{self.base_url}/jobs?{urlencode(params)}"
        
        return url
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _fetch_page(self, url: str) -> str:
        """Fetch page with retry logic."""
        return super()._fetch_page(url)
    
    def scrape_jobs(self, query: str, location: Optional[str], max_pages: int = 3) -> Generator[Dict[str, Any], None, None]:
        """Scrape jobs from Reed.
        
        Args:
            query: Job search query
            location: Location filter
            max_pages: Maximum pages to scrape
            
        Yields:
            Job data dictionaries
        """
        for page in range(1, max_pages + 1):
            url = self.build_search_url(query, location, page)
            logger.debug("Fetching Reed page", extra={"url": url, "page": page})
            
            try:
                html = self._fetch_page(url)
                jobs_found = 0
                
                for job_data in self._parse_jobs(html):
                    jobs_found += 1
                    yield job_data
                
                logger.debug("Reed page scraped", extra={"page": page, "jobs": jobs_found})
                
                # Stop if no jobs found on page
                if jobs_found == 0:
                    break
                    
            except Exception as e:
                logger.error("Error scraping Reed page", extra={
                    "page": page,
                    "error": str(e),
                    "url": url
                }, exc_info=True)
                break
    
    def _parse_jobs(self, html: str) -> Generator[Dict[str, Any], None, None]:
        """Parse job listings from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Reed job cards have class "job-result"
        job_cards = soup.find_all("article", class_="job-result")
        
        for card in job_cards:
            try:
                job_data = self._parse_job_card(card)
                if job_data:
                    yield job_data
            except Exception as e:
                logger.warning("Failed to parse Reed job card", 
                              extra={"error": str(e)}, exc_info=True)
                continue
    
    def _parse_job_card(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse individual job card.
        
        Args:
            card: BeautifulSoup job card element
            
        Returns:
            Job data dictionary or None if parsing failed
        """
        # Extract job title and link
        title_elem = card.find("h3", class_="job-result-heading__title")
        if not title_elem or not title_elem.find("a"):
            return None
        
        title = title_elem.get_text(strip=True)
        job_path = title_elem.find("a")["href"]
        job_url = urljoin(self.base_url, job_path)
        
        # Extract company
        company_elem = card.find("a", class_="job-result-heading__employer")
        company = company_elem.get_text(strip=True) if company_elem else ""
        
        # Extract location
        location_elem = card.find("li", class_="job-result-heading__meta")
        location = location_elem.get_text(strip=True) if location_elem else ""
        
        # Extract salary
        salary_elem = card.find("li", class_="job-result-heading__salary")
        salary_str = salary_elem.get_text(strip=True) if salary_elem else ""
        salary_data = self._parse_salary(salary_str)
        
        # Extract job type (contract, permanent, etc.)
        job_type_elem = card.find("li", class_="job-result-heading__type")
        job_type = job_type_elem.get_text(strip=True) if job_type_elem else ""
        
        # Check if remote
        is_remote = self._is_remote_job(title, location)
        remote_policy = "remote" if is_remote else "none"
        
        # Extract posted date
        posted_elem = card.find("time", attrs={"datetime": True})
        posted_date = None
        if posted_elem:
            datetime_str = posted_elem["datetime"]
            try:
                posted_date = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        
        # Extract description snippet
        desc_elem = card.find("div", class_="job-result-description")
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Generate unique job ID
        job_id = self._generate_id(job_url, title, company)
        
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "url": job_url,
            "location": {
                "original": location,
                "city": None,
                "country": None,
            },
            "salary": salary_data,
            "remote_policy": remote_policy,
            "remote_types": ["remote"] if is_remote else [],
            "contract_type": self._parse_contract_type(job_type),
            "posted_date": posted_date or datetime.now(timezone.utc),
            "description": description,
            "platform": self.platform_name,
            "industry": None,
            "experience_level": None,
            "skills": [],
        }
    
    def _parse_salary(self, salary_str: str) -> Dict[str, Any]:
        """Parse salary string into structured data.
        
        Reed examples:
        - "£35,000 - £45,000 per annum"
        - "£300 - £400 per day"
        - "£50,000 per annum"
        """
        # Default salary data
        salary_data = {
            "min": None,
            "max": None,
            "currency": None,
            "period": None,
            "original": salary_str,
        }
        
        if not salary_str or "negotiable" in salary_str.lower():
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
        if "per annum" in salary_str or "per year" in salary_str:
            period = "yearly"
        elif "per month" in salary_str:
            period = "monthly"
        elif "per day" in salary_str or "daily" in salary_str:
            period = "daily"
        elif "per hour" in salary_str or "hourly" in salary_str:
            period = "hourly"
        else:
            period = None
        
        # Extract numbers using regex
        numbers = re.findall(r'\d+\.?\d*', salary_str.replace(",", ""))
        
        if len(numbers) >= 2:
            # Range provided (e.g., "30000 - 40000")
            salary_data["min"] = int(float(numbers[0]))
            salary_data["max"] = int(float(numbers[1]))
        elif len(numbers) == 1:
            # Single value
            salary_data["min"] = int(float(numbers[0]))
            salary_data["max"] = int(float(numbers[0]))
        
        salary_data["currency"] = currency
        salary_data["period"] = period
        
        return salary_data
    
    def _parse_contract_type(self, job_type: str) -> Optional[str]:
        """Parse contract type from job type string."""
        job_type_lower = job_type.lower()
        
        if "contract" in job_type_lower:
            return "contract"
        elif "permanent" in job_type_lower or "full-time" in job_type_lower:
            return "permanent"
        elif "part-time" in job_type_lower:
            return "part-time"
        elif "temporary" in job_type_lower:
            return "temporary"
        elif "internship" in job_type_lower:
            return "internship"
        
        return None
    
    def _is_remote_job(self, title: str, location: str) -> bool:
        """Determine if job is remote based on title/location."""
        text = (title + " " + location).lower()
        remote_keywords = ["remote", "work from home", "wfh", "home based"]
        
        return any(keyword in text for keyword in remote_keywords)
    
    def _generate_id(self, url: str, title: str, company: str) -> str:
        """Generate unique job ID from URL, title, and company."""
        import hashlib
        id_string = f"{url}_{title}_{company}".encode('utf-8')
        return hashlib.md5(id_string).hexdigest()
    
    def scrape_job_details(self, job_url: str) -> Optional[str]:
        """Scrape full job description from job detail page."""
        try:
            html = self._fetch_page(job_url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Reed job description is in div with class "job-description"
            desc_elem = soup.find("div", class_="job-description")
            
            if desc_elem:
                return desc_elem.get_text("\n", strip=True)
            
            return None
        except Exception as e:
            logger.error("Failed to scrape job details", 
                        extra={"url": job_url, "error": str(e)}, exc_info=True)
            return None
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Reed"

    # Abstract method implementations for BaseScraper compatibility
    def get_search_url(self, query: str, location: str, **kwargs: Any) -> str:
        """Get search URL - delegates to build_search_url.
        
        Args:
            query: Job search query
            location: Location filter
            **kwargs: Additional parameters (page)
            
        Returns:
            Reed search URL
        """
        page = kwargs.get("page", 1)
        return self.build_search_url(query, location, page=page)

    def extract_job_listings(self, soup: BeautifulSoup) -> Any:
        """Extract job listings - delegates to internal logic.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of job card elements
        """
        return soup.find_all("article", class_="job-result")

    def parse_job_listing(self, element: Any) -> Optional[Dict[str, Any]]:
        """Parse job listing - delegates to internal logic.
        
        Args:
            element: BeautifulSoup job card element
            
        Returns:
            Job data dictionary or None
        """
        return self._parse_job_card(element)

    def get_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Get job details - delegates to existing implementation.
        
        Args:
            job_url: Job details page URL
            
        Returns:
            Job details dictionary or None
        """
        description = self.scrape_job_details(job_url)
        if description is None:
            return None
        return {"description": description, "url": job_url}