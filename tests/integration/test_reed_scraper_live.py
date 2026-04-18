"""Live Reed.co.uk integration test.

Tests Scrapling integration with src/discovery/platforms/reed_scraper.py
"""

import pytest
from scrapling.fetchers import StealthySession

from src.discovery.platforms.reed_scraper import ReedScraper
from src.config_manager import PlatformConfig


@pytest.mark.integration
def test_reed_live_scraping() -> None:
    """Test scraping real Reed.co.uk using scraper from src."""
    config = PlatformConfig(enabled=True)
    scraper = ReedScraper("reed", config)

    # Use browser to fetch page
    with StealthySession(headless=True) as session:
        page = session.fetch(
            "https://www.reed.co.uk/jobs?keywords=python&location=london",
            timeout=30000,
            network_idle=True,
        )
        assert page is not None
        assert page.status == 200

        # Use scraper's parse method
        articles = page.css("article")
        assert len(articles) > 0, "No job articles found"

        # Parse using scraper's method
        job = scraper.parse_job_listing_browser(articles[0])
        assert job is not None
        assert "title" in job
        assert len(job["title"]) > 0


@pytest.mark.integration
def test_reed_scrape_jobs_browser() -> None:
    """Test full scrape_jobs_browser from src."""
    config = PlatformConfig(enabled=True)
    scraper = ReedScraper("reed", config)

    # Scrape jobs via browser
    jobs = list(scraper.scrape_jobs_browser("python", "london", max_pages=1))

    assert len(jobs) > 0, "Should find jobs"
    job = jobs[0]
    assert "title" in job
    assert "company" in job


if __name__ == "__main__":
    test_reed_live_scraping()
    test_reed_scrape_jobs_browser()
