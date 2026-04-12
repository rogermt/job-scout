"""Indeed UK scraper for job discovery.

This module provides a scraper for Indeed UK (https://uk.indeed.com) following
ForgeSyte standards with proper error handling and rate limiting.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from .base_scraper import BaseScraper, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("indeed")
class IndeedScraper(BaseScraper):
    """Scraper for Indeed UK job listings."""
    
    BASE_URL = "https://uk.indeed.com"
    SEARCH_PATH = "/jobs"
    
    def __init__(self, platform_name: str, config: "PlatformConfig") -> None:
        """Initialize Indeed scraper.
        
        Args:
            platform_name: Platform name (should be 'indeed')
            config: Platform configuration
        """
        super().__init__(platform_name, config, rate_limit=5)
        logger.info("Indeed UK scraper initialized")
    
    def get_search_url(self, query: str, location: Optional[str] = None, **kwargs: Any) -> str:
        """Generate Indeed UK search URL.
        
        Args:
            query: Job search query (e.g., "software engineer")
            location: Location filter (e.g., "remote", "London")
            **kwargs: Additional parameters like 'page'
            
        Returns:
            Indeed UK search URL
            
        Examples:
            https://uk.indeed.com/jobs?q=software+engineer&l=London&sort=date
            https://uk.indeed.com/jobs?q=software+engineer&remote=true&sort=date
        """
        import urllib.parse
        
        params = {
            "q": query,
            "sort": "date",  # Sort by most recent
        }
        
        # Handle location and remote
        if location:
            if "remote" in location.lower() or self.config.region == "uk-remote":
                params["remote"] = "true"
            else:
                params["l"] = location
        
        # Pagination
        if page := kwargs.get("page", 0):
            params["start"] = page * 10  # Indeed uses offset
        
        query_string = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}{self.SEARCH_PATH}?{query_string}"
        
        logger.debug(
            "Generated search URL",
            extra={"url": url, "query": query, "location": location}
        )
        return url
    
    def extract_job_listings(self, soup: BeautifulSoup) -> list[Tag]:
        """Extract job listing elements from Indeed search results.
        
        Args:
            soup: Parsed search results page
            
        Returns:
            List of job card elements
        """
        # Indeed uses 'jobsearch-SerpJobCard' or 'job_seen_beacon' for job cards
        job_cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobsearch-SerpJobCard"))
        
        logger.debug(
            "Extracted job listings",
            extra={"count": len(job_cards), "css_classes_found": [card.get("class") for card in job_cards[:3]]}
        )
        
        return job_cards
    
    def parse_job_listing(self, element: Tag) -> Optional[dict[str, Any]]:
        """Parse a single Indeed job listing.
        
        Args:
            element: Job card element
            
        Returns:
            Dictionary with job data or None if parsing failed
        """
        try:
            job_data: dict[str, Any] = {}
            
            # Extract job ID from the element
            job_card = element.find("div", class_=re.compile(r"job_seen_beacon"))
            if job_card and "data-jk" in job_card.attrs:
                job_data["platform_id"] = job_card["data-jk"]
            else:
                # Fallback to extract from link
                link_elem = element.find("a")
                if link_elem and "href" in link_elem.attrs:
                    href = link_elem["href"]
                    match = re.search(r"vjk=([a-f0-9]+)", href)
                    if match:
                        job_data["platform_id"] = match.group(1)
            
            # Extract title
            title_elem = element.find("h2", class_=re.compile(r"jobTitle"))
            if title_elem:
                job_data["title"] = title_elem.get_text(strip=True)
            else:
                title_elem = element.find("a", attrs={"data-tn-element": "jobTitle"})
                if title_elem:
                    job_data["title"] = title_elem.get_text(strip=True)
            
            if not job_data.get("title"):
                logger.warning("Could not extract job title", extra={"element": str(element)[:200]})
                return None
            
            # Extract company
            company_elem = element.find("span", attrs={"data-testid": "company-name"})
            if not company_elem:
                company_elem = element.find("span", class_=re.compile(r"company"))
            if not company_elem:
                company_elem = element.find("div", class_=re.compile(r"company_location"))
                if company_elem:
                    company_elem = company_elem.find("span")
            
            job_data["company"] = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Extract location
            location_elem = element.find("div", attrs={"data-testid": "text-location"})
            if not location_elem:
                location_elem = element.find("div", class_=re.compile(r"company_location"))
            
            job_data["location"] = location_elem.get_text(strip=True) if location_elem else None
            
            # Extract remote policy from location or description
            location_text = (job_data["location"] or "").lower()
            job_data["remote_policy"] = None
            if "remote" in location_text or "work from home" in location_text:
                job_data["remote_policy"] = "fully-remote"
            
            # Extract salary if available
            salary_elem = element.find("div", class_=re.compile(r"salary.*snip"))
            if not salary_elem:
                salary_elem = element.find("span", class_=re.compile(r"salary"))
            
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
            if salary_text:
                min_salary, max_salary, currency = self.parse_salary(salary_text)
                if min_salary:
                    # Store all salary data
                    job_data["salary_min"] = min_salary
                    job_data["salary_max"] = max_salary
                    job_data["salary_currency"] = currency
                    job_data["salary_text"] = salary_text
            
            # Extract date posted
            date_elem = element.find("span", class_=re.compile(r"date"))
            if not date_elem:
                date_elem = element.find("div", class_=re.compile(r"date"))
            
            date_text = date_elem.get_text(strip=True) if date_elem else ""
            if date_text:
                try:
                    posted_date = self.parse_posted_date(date_text)
                    job_data["posted_date"] = posted_date
                except Exception as e:
                    logger.debug(
                        "Failed to parse posted date",
                        extra={"date_text": date_text, "error": str(e)}
                    )
            
            # Generate job URL
            job_data["url"] = self._build_job_url(job_data.get("platform_id", ""))
            
            logger.debug(
                "Parsed job listing",
                extra={
                    "title": job_data["title"],
                    "company": job_data["company"],
                    "has_salary": "salary_min" in job_data
                }
            )
            
            return job_data
        
        except Exception as e:
            logger.warning(
                "Failed to parse job listing",
                extra={"error": str(e), "element_snippet": str(element)[:200]}
            )
            return None
    
    def get_job_details(self, job_url: str) -> Optional[dict[str, Any]]:
        """Fetch and parse detailed job information.
        
        Args:
            job_url: Indeed job details URL
            
        Returns:
            Dictionary with detailed job data or None if failed
        """
        try:
            soup = self.fetch_page(job_url)
            if not soup:
                return None
            
            details: dict[str, Any] = {}
            
            # Extract detailed description
            desc_elem = soup.find("div", id="jobDescriptionText")
            if desc_elem:
                details["description"] = desc_elem.get_text("\n", strip=True)
            
            # Extract additional metadata
            metadata_elems = soup.find_all("div", class_="jobsearch-JobMetadataHeader-item")
            for elem in metadata_elems:
                text = elem.get_text(strip=True)
                if "remote" in text.lower():
                    details["remote_policy"] = "fully-remote"
                
            return details
        
        except Exception as e:
            logger.warning(
                "Failed to fetch job details",
                extra={"url": job_url, "error": str(e)}
            )
            return None
    
    def _build_job_url(self, platform_id: str) -> str:
        """Build full job URL from platform ID.
        
        Args:
            platform_id: Indeed job ID
            
        Returns:
            Full job details URL
        """
        return f"{self.BASE_URL}/viewjob?jk={platform_id}"
    
    def has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there's a next page.
        
        Args:
            soup: Current page content
            current_page: Current page number
            
        Returns:
            True if next page likely exists
        """
        # Look for next button/link
        next_link = soup.find("a", {"aria-label": re.compile(r"Next", re.I)})
        if not next_link:
            next_link = soup.find("a", class_=re.compile(r"pagination.*next", re.I))
        
        has_next = bool(next_link)
        logger.debug(
            "Next page check",
            extra={"current_page": current_page, "has_next": has_next}
        )
        return has_next


__all__ = ["IndeedScraper"]