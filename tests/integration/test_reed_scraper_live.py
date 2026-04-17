"""Live Reed.co.uk integration test.

Tests against REAL Reed.co.uk to verify selectors work.
NOTE: Reed.co.uk uses JS rendering so we use browser (Scrapling) not HTTP.
"""

import pytest
from scrapling.fetchers import StealthySession


@pytest.mark.integration
def test_reed_live_scraping() -> None:
    """Test scraping real Reed.co.uk using browser to verify selectors work."""
    url = "https://www.reed.co.uk/jobs?keywords=python&location=london"
    
    with StealthySession(headless=True) as session:
        page = session.fetch(url, timeout=30000, network_idle=True)
        assert page is not None, "Page should load"
        assert page.status == 200, f"Expected 200, got {page.status}"

        # Current selectors in reed_scraper.py
        articles = page.css("article.job-result, article.job-card, article")
        assert len(articles) > 0, f"No job elements found"


if __name__ == "__main__":
    test_reed_live_scraping()