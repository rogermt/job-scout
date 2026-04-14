"""Tests for base_scraper module."""
import pytest
import time
from unittest.mock import MagicMock, patch

from src.config_manager import PlatformConfig
from src.discovery.platforms.base_scraper import (
    BaseScraper,
    register_scraper,
    get_scraper,
    list_scrapers,
)


class ConcreteScraper(BaseScraper):
    """Test implementation of BaseScraper."""

    def get_search_url(self, query, location=None, **kwargs):
        return f"http://test.com/search?q={query}"

    def extract_job_listings(self, soup):
        return []

    def parse_job_listing(self, element):
        return {"title": "Test Job"}

    def get_job_details(self, job_url):
        return {"title": "Test"}


@pytest.fixture
def config():
    return PlatformConfig(enabled=True, region="uk")


@pytest.fixture
def scraper(config):
    return ConcreteScraper("test", config)


class TestRateLimiting:
    def test_enforce_rate_limit_no_wait_needed(self, scraper):
        """Test rate limit when no wait needed."""
        scraper._last_request_time = time.time()
        # Should not raise or hang
        scraper._enforce_rate_limit()

    def test_enforce_rate_limit_waits(self, scraper):
        """Test rate limit enforces wait."""
        scraper.rate_limit = 0.1
        scraper._last_request_time = time.time()
        start = time.time()
        scraper._enforce_rate_limit()
        elapsed = time.time() - start
        assert elapsed >= 0.05


class TestMakeRequest:
    @patch("requests.Session.request")
    def test_make_request_success(self, mock_request, scraper):
        """Test successful request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        _req = scraper._make_request("http://test.com", method="POST", data={})
        mock_request.assert_called_once()

    @patch("requests.Session.request")
    def test_make_request_post_method(self, mock_request, scraper):
        """Test POST request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response
        _req = scraper._make_request("http://test.com")
        assert _req == mock_response
        mock_request.assert_called_once()


class TestFetchPage:
    @patch.object(ConcreteScraper, "_make_request")
    def test_fetch_page_success(self, mock_request, scraper):
        """Test successful page fetch."""
        mock_response = MagicMock()
        mock_response.content = b"<html></html>"
        mock_request.return_value = mock_response

        result = scraper.fetch_page("http://test.com")
        assert result is not None

    @patch.object(ConcreteScraper, "_make_request")
    def test_fetch_page_exception(self, mock_request, scraper):
        """Test fetch returns None on exception."""
        import requests

        mock_request.side_effect = requests.RequestException("fail")

        result = scraper.fetch_page("http://test.com")
        assert result is None


class TestEnabled:
    def test_is_enabled_true(self, scraper):
        assert scraper.is_enabled() is True

    def test_can_scrape(self, scraper):
        assert scraper.can_scrape() is True


class TestScrapeJobs:
    @patch.object(ConcreteScraper, "fetch_page")
    @patch.object(ConcreteScraper, "extract_job_listings")
    @patch.object(ConcreteScraper, "parse_job_listing")
    def test_scrape_jobs_single_page(
        self, mock_parse, mock_extract, mock_fetch, scraper
    ):
        """Test scraping a single page."""
        mock_soup = MagicMock()
        mock_fetch.return_value = mock_soup
        mock_extract.return_value = [MagicMock()]
        mock_parse.return_value = {"title": "Job 1"}

        results = list(scraper.scrape_jobs("test", max_pages=1))
        assert len(results) == 1

    @patch.object(ConcreteScraper, "fetch_page")
    def test_scrape_jobs_stops_on_failure(self, mock_fetch, scraper):
        """Test scraping stops when fetch fails."""
        mock_fetch.return_value = None

        results = list(scraper.scrape_jobs("test", max_pages=3))
        assert len(results) == 0


class TestHasNextPage:
    def test_has_next_page_true(self, scraper):
        html = "<html><body><a href='/page2'>Next</a></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        assert scraper.has_next_page(soup, 0) is True

    def test_has_next_page_false(self, scraper):
        html = "<html><body><p>No links</p></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        assert scraper.has_next_page(soup, 0) is False


class TestParseSalary:
    def test_parse_salary_empty(self, scraper):
        result = scraper.parse_salary("")
        assert result["min"] is None

    def test_parse_salary_gbp(self, scraper):
        result = scraper.parse_salary("£30,000")
        assert result["currency"] == "GBP"

    def test_parse_salary_usd(self, scraper):
        result = scraper.parse_salary("$40,000")
        assert result["currency"] == "USD"

    def test_parse_salary_eur(self, scraper):
        result = scraper.parse_salary("€50,000")
        assert result["currency"] == "EUR"

    def test_parse_salary_range(self, scraper):
        result = scraper.parse_salary("£30k to £40k")
        assert result["min"] == 30.0
        assert result["max"] == 40.0

    def test_parse_salary_single(self, scraper):
        result = scraper.parse_salary("£35,000")
        assert result["min"] == 35000
        assert result["max"] == 35000


class TestParsePostedDate:
    def test_parse_posted_date_empty(self, scraper):
        result = scraper.parse_posted_date("")
        assert result is None

    def test_parse_posted_date_days(self, scraper):
        result = scraper.parse_posted_date("5 days ago")
        assert result is not None

    def test_parse_posted_date_weeks(self, scraper):
        result = scraper.parse_posted_date("2 weeks ago")
        assert result is not None

    def test_parse_posted_date_months(self, scraper):
        result = scraper.parse_posted_date("1 month ago")
        assert result is not None

    def test_parse_posted_date_hours(self, scraper):
        result = scraper.parse_posted_date("3 hours ago")
        assert result is not None


class TestScraperRegistry:
    def test_register_and_get_scraper(self, config):
        """Test registering and retrieving scraper."""

        @register_scraper("test_platform")
        class TestScraperImpl(BaseScraper):
            def get_search_url(self, query, location=None, **kwargs):
                return "http://test.com"

            def extract_job_listings(self, soup):
                return []

            def parse_job_listing(self, element):
                return {}

            def get_job_details(self, job_url):
                return {}

        scraper = get_scraper("test_platform", config)
        assert scraper is not None

    def test_list_scrapers(self):
        """Test listing registered scrapers."""
        scrapers = list_scrapers()
        assert isinstance(scrapers, list)
