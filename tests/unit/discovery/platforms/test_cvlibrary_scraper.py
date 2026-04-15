"""Tests for CV-Library scraper."""
import pytest
from unittest.mock import MagicMock, patch

from src.config_manager import PlatformConfig
from src.discovery.platforms.cvlibrary_scraper import CvlibraryScraper


@pytest.fixture
def scraper():
    return CvlibraryScraper("cvlibrary", PlatformConfig(enabled=True, region="uk"))


class TestCvlibraryInit:
    def test_init(self, scraper):
        assert scraper.platform_name == "cvlibrary"
        assert scraper.base_url == "https://www.cvlibrary.co.uk"
        assert scraper.jobs_per_page == 20


class TestCvlibraryPlatformName:
    def test_get_platform_name(self, scraper):
        assert scraper.get_platform_name() == "CV-Library"


class TestCvlibraryBuildSearchUrl:
    def test_build_search_url_basic(self, scraper):
        url = scraper.build_search_url("python")
        assert "python" in url

    def test_build_search_url_with_location(self, scraper):
        url = scraper.build_search_url("python", location="London")
        assert "London" in url

    def test_build_search_url_with_page(self, scraper):
        url = scraper.build_search_url("python", page=2)
        assert "page=2" in url


class TestCvlibraryGetSearchUrl:
    def test_get_search_url(self, scraper):
        url = scraper.get_search_url("python")
        assert "python" in url


class TestCvlibraryExtractJobListings:
    def test_extract_job_listings(self, scraper):
        soup = MagicMock()
        soup.select.return_value = [MagicMock()]
        assert len(scraper.extract_job_listings(soup)) == 1


class TestCvlibraryParseJobListing:
    def test_parse_job_listing(self, scraper):
        html = """<html><article class="job-result">
            <h3 class="title"><a href="/job/123">Senior Python Developer</a></h3>
            <span class="company-name">Tech Corp</span>
            <span class="location">London, UK</span>
            <span class="salary">GBP 50000 to 70000 per year</span>
            <span class="posted-date">3 days ago</span>
            <p class="summary">Great opportunity for a Python developer.</p>
        </article></html>"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper.parse_job_listing(soup.article)
        assert result is not None
        assert result["title"] == "Senior Python Developer"
        assert result["company"] == "Tech Corp"
        assert result["salary"]["currency"] == "GBP"
        assert result["salary"]["min"] == 50000
        assert result["salary"]["max"] == 70000


class TestCvlibraryParseSalary:
    def test_parse_salary_empty(self, scraper):
        result = scraper._parse_salary("")
        assert result["min"] is None

    def test_parse_salary_with_value(self, scraper):
        result = scraper._parse_salary("30,000 to 40,000")
        assert result["currency"] == "GBP"
        assert result["min"] == 30000
        assert result["max"] == 40000
        assert result["period"] == "yearly"


class TestCvlibraryParsePostedDate:
    def test_parse_posted_date_empty(self, scraper):
        result = scraper._parse_posted_date("")
        assert result is None


class TestCvlibraryHasNextPage:
    def test_has_next_page_true(self, scraper):
        html = "<html><body><a class='next-page'>Next</a></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        assert scraper.has_next_page(soup, 0) is True


class TestCvlibraryGetJobDetails:
    @patch.object(CvlibraryScraper, "fetch_page")
    def test_get_job_details(self, mock_fetch, scraper):
        html = "<html><body><h1>Dev</h1></body></html>"
        from bs4 import BeautifulSoup

        mock_fetch.return_value = BeautifulSoup(html, "html.parser")
        result = scraper.get_job_details("http://test.com")
        assert result is not None
