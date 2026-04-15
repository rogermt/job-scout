"""Tests for CWJobs scraper."""
import pytest
from unittest.mock import MagicMock, patch

from src.config_manager import PlatformConfig
from src.discovery.platforms.cwjobs_scraper import CwjobsScraper


@pytest.fixture
def scraper():
    return CwjobsScraper("cwjobs", PlatformConfig(enabled=True, region="uk"))


class TestCwjobsInit:
    def test_init(self, scraper):
        assert scraper.platform_name == "cwjobs"
        assert scraper.base_url == "https://www.cwjobs.co.uk"
        assert scraper.jobs_per_page == 20


class TestCwjobsPlatformName:
    def test_get_platform_name(self, scraper):
        assert scraper.get_platform_name() == "CWJobs"


class TestCwjobsBuildSearchUrl:
    def test_build_search_url_basic(self, scraper):
        url = scraper.build_search_url("python")
        assert "python" in url

    def test_build_search_url_with_location(self, scraper):
        url = scraper.build_search_url("python", location="London")
        assert "london" in url

    def test_build_search_url_with_page(self, scraper):
        url = scraper.build_search_url("python", page=2)
        assert "page=2" in url


class TestCwjobsGetSearchUrl:
    def test_get_search_url(self, scraper):
        url = scraper.get_search_url("python")
        assert "python" in url


class TestCwjobsExtractJobListings:
    def test_extract_job_listings(self, scraper):
        soup = MagicMock()
        soup.select.return_value = [MagicMock()]
        assert len(scraper.extract_job_listings(soup)) == 1


class TestCwjobsParseJobListing:
    def test_parse_job_listing(self, scraper):
        html = "<html><article><h2><a>Dev</a></h2></article></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper.parse_job_listing(soup.article)
        assert result is not None


class TestCwjobsParseSalary:
    def test_parse_salary_empty(self, scraper):
        result = scraper._parse_salary("")
        assert result["min"] is None

    def test_parse_salary_with_value(self, scraper):
        result = scraper._parse_salary("£30,000 to £45,000")
        assert result["currency"] == "GBP"


class TestCwjobsParsePostedDate:
    def test_parse_posted_date_empty(self, scraper):
        result = scraper._parse_posted_date("")
        assert result is None


class TestCwjobsHasNextPage:
    def test_has_next_page_true(self, scraper):
        html = "<html><body><a class='next-page'>Next</a></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        assert scraper.has_next_page(soup, 0) is True


class TestCwjobsGetJobDetails:
    @patch.object(CwjobsScraper, "fetch_page")
    def test_get_job_details(self, mock_fetch, scraper):
        html = "<html><body><h1>Dev</h1></body></html>"
        from bs4 import BeautifulSoup

        mock_fetch.return_value = BeautifulSoup(html, "html.parser")
        result = scraper.get_job_details("http://test.com")
        assert result is not None
