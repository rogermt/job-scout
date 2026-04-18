"""Integration tests for Scrapling browser automation on job sites.

Tests that browser-based scraping works for each supported platform.
Uses StealthySession for persistent browser.
"""

import pytest

from scrapling.fetchers import StealthySession

pytestmark = pytest.mark.integration


class TestScraplingBrowser:
    """Integration tests for browser-based scraping via Scrapling."""

    @pytest.mark.parametrize(
        "name,url",
        [
            (
                "Reed",
                "https://www.reed.co.uk/jobs?keywords=python&location=london",
            ),
            (
                "Totaljobs",
                "https://www.totaljobs.com/jobs/python-jobs/in-london",
            ),
            (
                "CVLibrary",
                "https://www.cvlibrary.co.uk/jobs?keywords=python&location=london",
            ),
        ],
        ids=["reed", "totaljobs", "cvlibrary"],
    )
    def test_site_returns_jobs(self, name, url):
        """Test that site returns job listings via browser."""
        with StealthySession(headless=True) as session:
            page = session.fetch(url, timeout=30000, network_idle=True)

            assert page is not None
            assert page.status == 200

            # Use Scrapling's CSS selector (no BeautifulSoup) - support multiple selectors
            articles = page.css(
                "article, .job-item, .job-card, .job-result, .job-listing"
            )
            assert len(articles) > 0, f"{name}: No jobs found"

    @pytest.mark.parametrize(
        "name,url",
        [
            (
                "Reed",
                "https://www.reed.co.uk/jobs?keywords=python&location=london",
            ),
        ],
        ids=["reed"],
    )
    def test_reed_extracts_job_titles(self, name, url):
        """Test extraction of job titles from Reed."""
        with StealthySession(headless=True) as session:
            page = session.fetch(url, timeout=30000, network_idle=True)

            articles = page.css("article")
            assert len(articles) > 0

            # Extract title from first article
            title_elem = articles[0].css("a")
            assert len(title_elem) > 0

            title = title_elem[0].text
            assert len(title) > 0, "Job title should not be empty"
