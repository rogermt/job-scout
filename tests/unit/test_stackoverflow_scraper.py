"""Unit tests for StackOverflowScraper.

Tests Stack Overflow job scraping logic with mocked HTTP requests.
Unit tests do NOT make real HTTP requests.
"""

from unittest.mock import Mock, patch

import pytest

from src.discovery.platforms.stackoverflow_scraper import StackOverflowScraper


class TestStackOverflowScraper:
    """Test StackOverflowScraper functionality."""

    @pytest.fixture
    def scraper(self) -> StackOverflowScraper:
        """Provide test instance."""
        return StackOverflowScraper("stackoverflow", Mock())

    @pytest.fixture
    def mock_html(self):
        """HTML mock matching StackOverflowScraper pattern."""
        return """
        <html>
        <body>
        <div class="job-item">
        <h2 class="job-link">Senior Python Developer</h2>
        <div class="employer">Tech Startup Ltd</div>
        <div class="location">Remote (US)</div>
        <div class="salary">$120,000 - $150,000</div>
        <a class="job-link" href="/jobs/12345">View Job</a>
        <div class="tags">
        <span class="post-tag">python</span>
        <span class="post-tag">django</span>
        <span class="post-tag">postgresql</span>
        </div>
        </div>
        </body>
        </html>
        """

    def test_instantiation(self, scraper):
        """Test instantiation."""
        assert scraper is not None

    @patch.object(StackOverflowScraper, "fetch_page")
    def test_make_request_success(self, mock_fetch, scraper):
        """Test successful HTTP request."""
        from bs4 import BeautifulSoup

        mock_fetch.return_value = BeautifulSoup("<html>Test</html>", "html.parser")

        scraper.get_job_details("https://stackoverflow.com/jobs/test")
        mock_fetch.assert_called_once()
