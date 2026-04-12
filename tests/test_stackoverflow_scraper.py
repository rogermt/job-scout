"""Unit tests for StackOverflowScraper.

Tests Stack Overflow job scraping logic with mocked HTTP requests.
Unit tests do NOT make real HTTP requests.
"""

from unittest.mock import Mock, patch
from typing import Dict, Any

import pytest
import httpx

from src.discovery.platforms.stackoverflow_scraper import StackOverflowScraper


class TestStackOverflowScraper:
    """Test StackOverflowScraper functionality."""

    @pytest.fixture
    def scraper(self) -> StackOverflowScraper:
        """Provide test instance."""
        return StackOverflowScraper()

    @pytest.fixture
    def mock_html(self):
        """HTML mock matching StackOverflowScraper pattern."""
        return '''
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
        '''

    def test_instantiation(self, scraper):
        """Test instantiation."""
        assert scraper is not None

    @patch('httpx.Client.get')
    def test_make_request_success(self, mock_get, scraper):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.text = "<html>Test</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper.get_job_count("python", "remote")
        mock_get.assert_called_once()
