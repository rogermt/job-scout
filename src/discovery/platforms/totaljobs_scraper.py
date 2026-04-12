"""Totaljobs scraper for UK job listings.

This module provides a scraper for Totaljobs.co.uk, a major UK job platform.
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


@register_scraper("totaljobs")
class TotaljobsScraper(BaseScraper):
    """Scraper for Totaljobs.co.uk job listings."""
    
    def __init__(self, platform_name: str, config: Dict[str, Any]) -> None:
        """Initialize Totaljobs scraper.
        
        Args:
            config: Configuration dictionary for Totaljobs scraper
        """
        # BaseScraper expects platform_name first, then config
        super().__init__(platform_name, config)
        self.base_url = "https://www.totaljobs.com"
        self.jobs_per_page = 20    
    def build_search_url(self, query: str, location: Optional[str], page: int = 1) -> str:
        """Build Totaljobs search URL.
        
        Args:
            query: Job search query
            location: Location filter
            page: Page number (1-indexed)
            
        Returns:
            Totaljobs search URL
        """
        # Totaljobs uses /jobs query parameters
        params = {
            "q": query,
        }
        
        if location:
            params["l"] = location
        
        url = f"{self.base_url}/jobs?{urlencode(params)}"
        
        if page > 1:
            url += f"&page={page}"
        
        return url
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _fetch_page(self, url: str) -> str:
        """Fetch page with retry logic."""
        return super()._fetch_page(url)
    
    def scrape_jobs(self, query: str, location: Optional[str], max_pages: int = 3) -> Generator[Dict[str, Any], None, None]:
        """Scrape jobs from Totaljobs.
        
        Args:
            query: Job search query
            location: Location filter
            max_pages: Maximum pages to scrape
            
        Yields:
            Job data dictionaries
        """
        for page in range(1, max_pages + 1):
            url = self.build_search_url(query, location, page)
            logger.debug("Fetching Totaljobs page", extra={"url": url, "page": page})
            
            try:
                html = self._fetch_page(url)
                jobs_found = 0
                
                for job_data in self._parse_jobs(html):
                    jobs_found += 1
                    yield job_data
                
                logger.debug("Totaljobs page scraped", extra={"page": page, "jobs": jobs_found})
                
                # Stop if no jobs found on page
                if jobs_found == 0:
                    break
                    
            except Exception as e:
                logger.error("Error scraping Totaljobs page", extra={
                    "page": page,
                    "error": str(e),
                    "url": url
                }, exc_info=True)
                break
    
    def _parse_jobs(self, html: str) -> Generator[Dict[str, Any], None, None]:
        """Parse job listings from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Totaljobs job cards have data-test="job-card" or class job-title
        job_cards = soup.find_all("article", attrs={"data-test": "job-card"})
        
        # Fallback: look for job-title class
        if not job_cards:
            job_cards = soup.find_all("div", class_="job-title")
        
        for card in job_cards:
            try:
                job_data = self._parse_job_card(card)
                if job_data:
                    yield job_data
            except Exception as e:
                logger.warning("Failed to parse Totaljobs job card", 
                              extra={"error": str(e)}, exc_info=True)
                continue
    
    def _parse_job_card(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse individual job card.
        
        Args:
            card: BeautifulSoup job card element
            
        Returns:
            Job data dictionary or None if parsing failed
        """
        # Look for job title link
        title_link = card.find("a", href=True)
        if not title_link:
            # Try alternative selectors
            title_link = card.find("h2").find("a", href=True) if card.find("h2") else None
        
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        job_url = urljoin(self.base_url, title_link["href"])
        
        # Extract company (usually in a span near the title)
        company_elem = card.find("span", class_=re.compile("company|employer", re.I))
        if not company_elem:
            # Try other selectors
            company_elem = card.find("li")
        company = company_elem.get_text(strip=True) if company_elem else ""
        
        # Extract location
        location_elem = card.find("span", class_=re.compile("location", re.I))
        if not location_elem:
            location_elem = card.find("li", text=re.compile(".*,.*|London|UK"))
        location = location_elem.get_text(strip=True) if location_elem else ""
        
        # Extract salary
        salary_elem = card.find("li", text=re.compile("£|\$|€|salary", re.I))
        if not salary_elem:
            salary_elem = card.find("span", style=re.compile("color.*red"))
        salary_str = salary_elem.get_text(strip=True) if salary_elem else ""
        salary_data = self._parse_salary(salary_str)
        
        # Extract job type
        job_type_elem = card.find("li", class_=lambda x: x and "time" in x)
        job_type = job_type_elem.get_text(strip=True) if job_type_elem else ""
        
        # Check if remote
        is_remote = self._is_remote_job(title, location)
        remote_policy = "remote" if is_remote else "none"
        
        # Extract description snippet
        desc_elem = card.find("p", class_=re.compile("description", re.I))
        if not desc_elem:
            desc_elem = card.find("p")
        description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""
        
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
            "posted_date": self._extract_posted_date(card) or datetime.now(timezone.utc),
            "description": description,
            "platform": self.platform_name,
            "industry": None,
            "experience_level": None,
            "skills": [],
        }
    
    def _parse_salary(self, salary_str: str) -> Dict[str, Any]:
        """Parse salary string into structured data.
        
        Totaljobs examples:
        - "£35,000 per annum"
        - "£300 - £400 per day"
        - "£50k - £60k"
        - "Competitive"
        """
        salary_data = {
            "min": None,
            "max": None,
            "currency": None,
            "period": None,
            "original": salary_str,
        }
        
        if not salary_str or "negotiable" in salary_str.lower() or "competitive" in salary_str.lower():
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
            "daily": "daily",
            "hourly": "hourly",
        }
        
        period = None
        for keyword, p in period_weights.items():
            if keyword in salary_str.lower():
                period = p
                break
        
        # Handle k notation (e.g., "£50k")
        salary_clean = salary_str.replace(",", "")
        numbers = re.findall(r'\d+\.?\d*', salary_clean)
        
        # Check for k notation
        k_matches = re.findall(r'(\d+)k', salary_clean, re.I)
        if k_matches:
            numbers = [int(k) * 1000 for k in k_matches] + [n for n in numbers if float(n) <= 100]
        
        if len(numbers) >= 2:
            salary_data["min"] = int(float(numbers[0]))
            salary_data["max"] = int(float(numbers[1]))
        elif len(numbers) == 1:
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
        elif "full-time" in job_type_lower:
            return "permanent"
        elif "part-time" in job_type_lower:
            return "part-time"
        elif "permanent" in job_type_lower:
            return "permanent"
        elif "temporary" in job_type_lower:
            return "temporary"
        
        return None
    
    def _extract_posted_date(self, card: BeautifulSoup) -> Optional[datetime]:
        """Extract posted date from card."""
        # Look for relative time indicator
        time_elem = card.find("time")
        if time_elem and "datetime" in time_elem.attrs:
            datetime_str = time_elem["datetime"]
            try:
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        
        # Look for text like "posted today", "posted 3 days ago"
        posted_text = card.find(text=re.compile(r"posted.*today|posted.*day|posted.*week", re.I))
        if posted_text:
            now = datetime.now(timezone.utc)
            if "today" in posted_text.lower():
                return now
            
            # Try to extract days
            matches = re.findall(r'(\d+)\s+day', posted_text)
            if matches:
                days = int(matches[0])
                return datetime(now.year, now.month, now.day) - timedelta(days=days)
        
        return None
    
    def _is_remote_job(self, title: str, location: str) -> bool:
        """Determine if job is remote based on title/location."""
        text = (title + " " + location).lower()
        remote_keywords = ["remote", "work from home", "wfh", "home based"]
        
        return any(keyword in text for keyword in remote_keywords)
    
    def _generate_id(self, url: str, title: str, company: str) -> str:
        """Generate unique job ID."""
        import hashlib
        id_string = f"{url}_{title}_{company}".encode('utf-8')
        return hashlib.md5(id_string).hexdigest()

    # Abstract method implementations for BaseScraper compatibility
    def get_search_url(self, query: str, location: str, **kwargs: Any) -> str:
        """Get search URL - delegates to build_search_url."""
        page = kwargs.get("page", 1)
        return self.build_search_url(query, location, page=page)

    def extract_job_listings(self, soup: Any) -> Any:
        """Extract job listings."""
        return soup.find_all("div", class_="job-item")

    def parse_job_listing(self, element: Any) -> Optional[Dict[str, Any]]:
        """Parse job listing."""
        return self._parse_job_card(element)

    def get_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Get job details."""
        description = self.scrape_job_details(job_url)
        if description is None:
            return None
        return {"description": description, "url": job_url}
    
    def scrape_job_details(self, job_url: str) -> Optional[str]:
        """Scrape full job description from job detail page."""
        try:
            html = self._fetch_page(job_url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Totaljobs job description is in various formats
            desc_elem = soup.find("div", class_=re.compile("job-description", re.I))
            
            if not desc_elem:
                # Try other selectors
                desc_elem = soup.find("div", {"itemprop": "description"})
            
            if not desc_elem:
                desc_elem = soup.find("section", class_=re.compile("description", re.I))
            
            if desc_elem:
                return desc_elem.get_text("\n", strip=True)
            
            return None
        except Exception as e:
            logger.error("Failed to scrape job details", 
                        extra={"url": job_url, "error": str(e)}, exc_info=True)
            return None
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Totaljobs"