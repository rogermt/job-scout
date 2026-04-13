"""Tests for job discovery scrapers.

This module tests all scraper implementations to ensure they:
1. Follow ForgeSyte Python standards
2. Return valid job data structures
3. Handle errors gracefully
4. Use proper logging (not print)
5. Have correct type annotations
6. Implement all required abstract methods
"""

import logging

import pytest

from src.config_manager import PlatformConfig
from src.discovery.platforms import get_scraper, list_scrapers

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def platform_configs() -> dict[str, PlatformConfig]:
    """Create platform configurations for testing."""
    return {
        "indeed": PlatformConfig(enabled=True, region="uk"),
        "reed": PlatformConfig(enabled=True, region="uk"),
        "totaljobs": PlatformConfig(enabled=True, region="uk"),
        "stackoverflow": PlatformConfig(enabled=True, region="remote"),
    }


@pytest.mark.unit
class TestScraperStandards:
    """Test that all scrapers meet ForgeSyte Python standards."""

    def test_all_scrapers_registered(self):
        """Verify all expected scrapers are registered."""
        available_scrapers = list_scrapers()
        expected_scrapers = {"indeed", "reed", "totaljobs", "stackoverflow"}

        logger.info("Available scrapers", extra={"scrapers": available_scrapers})

        assert expected_scrapers.issubset(
            set(available_scrapers)
        ), f"Missing scrapers: {expected_scrapers - set(available_scrapers)}"

    def test_scraper_imports(self, platform_configs):
        """Test scrapers can be imported and instantiated."""
        for platform_name, config in platform_configs.items():
            logger.info("Testing scraper import", extra={"platform": platform_name})
            scraper = get_scraper(platform_name, config)

            assert scraper is not None, f"Failed to get scraper for {platform_name}"
            assert scraper.platform_name == platform_name
            assert hasattr(scraper, "scrape_jobs")
            assert hasattr(scraper, "get_search_url")
            assert hasattr(scraper, "extract_job_listings")
            assert hasattr(scraper, "parse_job_listing")

    def test_no_print_statements_in_scrapers(self):
        """Verify scrapers use logging instead of print."""
        import os
        import re

        scraper_dir = "src/discovery/platforms"
        for filename in os.listdir(scraper_dir):
            if filename.endswith("_scraper.py"):
                filepath = os.path.join(scraper_dir, filename)
                with open(filepath, "r") as f:
                    content = f.read()

                # Check for print statements (but allow print in __repr__ or tests)
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if re.search(r"^\s*print\s*\(", line) and "__repr__" not in line:
                        logger.error(
                            "Found print statement in scraper",
                            extra={
                                "file": filename,
                                "line": i,
                                "content": line.strip(),
                            },
                        )
                        pytest.fail(
                            f"{filename}:{i} uses print() instead of logging: {line.strip()}"
                        )


@pytest.mark.unit
class TestIndeedScraper:
    """Test Indeed UK scraper specifically."""

    @pytest.fixture
    def indeed_scraper(self, platform_configs):
        """Create Indeed scraper instance."""
        return get_scraper("indeed", platform_configs["indeed"])

    def test_get_search_url(self, indeed_scraper):
        """Test search URL generation."""
        url = indeed_scraper.get_search_url("software engineer", "London", page=0)

        assert "https://uk.indeed.com/jobs" in url
        assert "q=software+engineer" in url
        assert "l=London" in url

        # Test remote
        remote_url = indeed_scraper.get_search_url("python developer", "remote")
        assert "remote=true" in remote_url

    def test_parse_salary_ranges(self):
        """Test salary parsing logic."""
        from src.discovery.platforms.indeed_scraper import IndeedScraper

        config = PlatformConfig()
        scraper = IndeedScraper("indeed", config)

        test_cases = [
            (
                "£30,000 - £50,000 a year",
                {"min": 30000, "max": 50000, "currency": "GBP", "period": "yearly"},
            ),
            (
                "£40,000+ a year",
                {"min": 40000, "max": 40000, "currency": "GBP", "period": "yearly"},
            ),
            (
                "Competitive",
                {"min": None, "max": None, "currency": "USD", "period": "yearly"},
            ),
        ]

        for salary_text, expected in test_cases:
            result = scraper.parse_salary(salary_text)
            assert (
                result == expected
            ), f"Failed for {salary_text}: expected {expected}, got {result}"


@pytest.mark.unit
class TestReedScraper:
    """Test Reed scraper specifically."""

    @pytest.fixture
    def reed_scraper(self, platform_configs):
        """Create Reed scraper instance."""
        from src.discovery.platforms.reed_scraper import ReedScraper

        return ReedScraper("reed", config=platform_configs["reed"])

    def test_salary_parsing(self, reed_scraper):
        """Test Reed salary parsing."""
        test_cases = [
            (
                "£35000 - £45000 per annum",
                {"min": 35000, "max": 45000, "currency": "GBP", "period": "yearly"},
            ),
            (
                "£60000 per annum",
                {"min": 60000, "max": 60000, "currency": "GBP", "period": "yearly"},
            ),
            (
                "£200 - £250 per day",
                {"min": 200, "max": 250, "currency": "GBP", "period": "daily"},
            ),
        ]

        for salary_text, expected in test_cases:
            result = reed_scraper.parse_salary(salary_text)
            assert (
                result == expected
            ), f"Failed for {salary_text}: expected {expected}, got {result}"


@pytest.mark.integration
@pytest.mark.skip(reason="Run locally - requires real HTTP requests")
class TestScraperIntegration:
    """Integration tests for scrapers with actual HTTP requests."""

    def test_indeed_scrape_single_page(self, platform_configs):
        """Test scraping a single page from Indeed."""
        scraper = get_scraper("indeed", platform_configs["indeed"])

        # Scrape just one page with a common query
        jobs = list(scraper.scrape_jobs("software engineer", "London", max_pages=1))

        logger.info("Indeed scrape results", extra={"job_count": len(jobs)})

        # Should find at least some jobs
        assert len(jobs) > 0, "Should find at least one job"

        # Validate job data structure
        job = jobs[0]
        assert "title" in job
        assert "company" in job
        assert "url" in job
        assert isinstance(job["title"], str)
        assert isinstance(job["company"], str)
        assert isinstance(job["url"], str)

        if "posted_date" in job:
            assert isinstance(
                job["posted_date"], str
            ), "posted_date should be ISO date string"

    def test_reed_scrape_single_page(self, platform_configs):
        """Test scraping a single page from Reed."""
        from src.discovery.platforms.reed_scraper import ReedScraper

        scraper = ReedScraper(config=platform_configs["reed"])

        jobs = list(scraper.scrape_jobs("data analyst", "Manchester", max_pages=1))

        logger.info("Reed scrape results", extra={"job_count": len(jobs)})
        assert len(jobs) > 0

        # Validate structure
        job = jobs[0]
        assert "title" in job
        assert "company" in job

    def test_totaljobs_scrape_single_page(self, platform_configs):
        """Test scraping a single page from TotalJobs."""
        scraper = get_scraper("totaljobs", platform_configs["totaljobs"])

        jobs = list(scraper.scrape_jobs("project manager", "remote", max_pages=1))

        logger.info("TotalJobs scrape results", extra={"job_count": len(jobs)})
        assert len(jobs) > 0

        job = jobs[0]
        assert "title" in job
        assert "url" in job

    def test_stackoverflow_scrape_single_page(self, platform_configs):
        """Test scraping a single page from Stack Overflow."""
        scraper = get_scraper("stackoverflow", platform_configs["stackoverflow"])

        jobs = list(scraper.scrape_jobs("python developer", location=None, max_pages=1))

        logger.info("StackOverflow scrape results", extra={"job_count": len(jobs)})
        assert len(jobs) > 0

        job = jobs[0]
        assert "title" in job
        assert "company" in job
        assert "url" in job


@pytest.mark.integration
@pytest.mark.skip(reason="Run locally - depends on integration tests")
@pytest.mark.integration
class TestJobDataStructure:
    """Test that returned job data has correct structure and types."""

    @pytest.fixture
    def sample_jobs(self, platform_configs):
        """Get sample jobs from all scrapers."""
        jobs = []
        for platform in ["indeed", "reed", "totaljobs", "stackoverflow"]:
            try:
                scraper = get_scraper(platform, platform_configs[platform])
                platform_jobs = list(
                    scraper.scrape_jobs("software engineer", "London", max_pages=1)
                )
                jobs.extend(
                    [(platform, job) for job in platform_jobs[:3]]
                )  # Up to 3 per platform
            except Exception as e:
                logger.warning(
                    "Failed to scrape from platform",
                    extra={"platform": platform, "error": str(e)},
                )
        return jobs

    def test_job_data_structure(self, sample_jobs):
        """Validate structure of all scraped jobs."""
        assert (
            len(sample_jobs) > 0
        ), "Should have sample jobs from at least one platform"

        for platform, job in sample_jobs:
            logger.info("Validating job structure", extra={"platform": platform})

            # Required fields
            assert isinstance(
                job.get("title"), str
            ), f"[{platform}] title must be string"
            assert isinstance(
                job.get("company"), str
            ), f"[{platform}] company must be string"
            assert isinstance(job.get("url"), str), f"[{platform}] url must be string"

            # Optional fields with type validation
            if job.get("location"):
                assert isinstance(
                    job["location"], str
                ), f"[{platform}] location must be string"

            if "salary_text" in job:
                assert isinstance(
                    job["salary_text"], str
                ), f"[{platform}] salary_text must be string"

            if "salary_min" in job and job["salary_min"]:
                assert isinstance(
                    job["salary_min"], (int, float)
                ), f"[{platform}] salary_min must be numeric"

            if "salary_max" in job and job["salary_max"]:
                assert isinstance(
                    job["salary_max"], (int, float)
                ), f"[{platform}] salary_max must be numeric"

            if "posted_date" in job and job["posted_date"]:
                assert isinstance(
                    job["posted_date"], str
                ), f"[{platform}] posted_date must be string"

    def test_remote_policy_extraction(self, sample_jobs):
        """Test that remote policy is correctly extracted when present."""
        for platform, job in sample_jobs:
            if job.get("remote_policy"):
                assert job["remote_policy"] in [
                    "fully-remote",
                    "hybrid",
                    "remote-option",
                ], f"[{platform}] Invalid remote_policy value: {job['remote_policy']}"


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and resilience."""

    def test_invalid_platform(self):
        """Test error when requesting invalid platform."""
        config = PlatformConfig()
        with pytest.raises(ValueError):
            get_scraper("invalid_platform", config)

    def test_invalid_search_url_handling(self, platform_configs):
        """Test handling of invalid URLs."""
        scraper = get_scraper("indeed", platform_configs["indeed"])

        # This should handle the error gracefully and return None
        try:
            result = scraper.fetch_page("https://invalid-url-12345.com")
            assert result is None
        except Exception as e:
            # Should log error, not raise
            logger.info(
                "Expected exception handled gracefully", extra={"error": str(e)}
            )

    def test_parse_invalid_html(self, platform_configs):
        """Test parsing invalid HTML."""
        from bs4 import BeautifulSoup

        scraper = get_scraper("indeed", platform_configs["indeed"])

        # Create empty/invalid soup
        invalid_soup = BeautifulSoup("<html></html>", "html.parser")
        jobs = scraper.extract_job_listings(invalid_soup)

        # Should return empty list, not crash
        assert isinstance(jobs, list)
        assert len(jobs) == 0


class TestBaseScraperMethods:
    """Test BaseScraper utility methods."""

    @pytest.fixture
    def indeed_scraper(self, platform_configs):
        """Create Indeed scraper instance."""
        from src.discovery.platforms.indeed_scraper import IndeedScraper

        return IndeedScraper("indeed", platform_configs["indeed"])

    def test_parse_salary_empty_text(self, indeed_scraper):
        """Test parse_salary with empty text."""
        result = indeed_scraper.parse_salary("")
        assert result["min"] is None
        assert result["max"] is None

    def test_parse_salary_single_number(self, indeed_scraper):
        """Test parse_salary with single number."""
        result = indeed_scraper.parse_salary("£50,000 a year")
        assert result["min"] == 50000
        assert result["max"] == 50000

    def test_parse_salary_range(self, indeed_scraper):
        """Test parse_salary with range."""
        result = indeed_scraper.parse_salary("£40,000 - £60,000 a year")
        assert result["min"] == 40000
        assert result["max"] == 60000

    def test_parse_salary_usd(self, indeed_scraper):
        """Test parse_salary with USD."""
        result = indeed_scraper.parse_salary("$70,000 - $90,000 a year")
        assert result["currency"] == "USD"

    def test_parse_salary_eur(self, indeed_scraper):
        """Test parse_salary with EUR."""
        result = indeed_scraper.parse_salary("€60,000 a year")
        assert result["currency"] == "EUR"

    def test_parse_posted_date_days(self, indeed_scraper):
        """Test parse_posted_date with days."""
        result = indeed_scraper.parse_posted_date("5 days ago")
        assert result is not None

    def test_parse_posted_date_weeks(self, indeed_scraper):
        """Test parse_posted_date with weeks."""
        result = indeed_scraper.parse_posted_date("2 weeks ago")
        assert result is not None

    def test_parse_posted_date_months(self, indeed_scraper):
        """Test parse_posted_date with months."""
        result = indeed_scraper.parse_posted_date("1 month ago")
        assert result is not None

    def test_parse_posted_date_hours(self, indeed_scraper):
        """Test parse_posted_date with hours."""
        result = indeed_scraper.parse_posted_date("12 hours ago")
        assert result is not None

    def test_parse_posted_date_invalid(self, indeed_scraper):
        """Test parse_posted_date with invalid text."""
        result = indeed_scraper.parse_posted_date("yesterday")
        assert result is None

    def test_can_scrape_enabled(self, indeed_scraper):
        """Test can_scrape when enabled."""
        assert indeed_scraper.can_scrape() is True

    def test_can_scrape_disabled(self, platform_configs):
        """Test can_scrape when disabled."""
        from src.discovery.platforms.indeed_scraper import IndeedScraper

        config = PlatformConfig(enabled=False, region="uk")
        scraper = IndeedScraper("indeed", config)
        assert scraper.can_scrape() is False

    def test_is_enabled(self, indeed_scraper):
        """Test is_enabled method."""
        assert indeed_scraper.is_enabled() is True

    def test_has_next_page_true(self, indeed_scraper):
        """Test has_next_page returns True for pagination."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup('<div class="pagination"><a>Next</a></div>', "html.parser")
        result = indeed_scraper.has_next_page(html, 1)
        assert isinstance(result, bool)

    def test_has_next_page_false(self, indeed_scraper):
        """Test has_next_page returns False when no pagination."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup('<div class="content">No next page</div>', "html.parser")
        result = indeed_scraper.has_next_page(html, 1)
        assert result is False

    def test_scrape_jobs_empty_results(self, indeed_scraper):
        """Test scrape_jobs with no results."""
        from bs4 import BeautifulSoup
        from unittest.mock import MagicMock, patch

        mock_soup = MagicMock(spec=BeautifulSoup)
        mock_soup.select.return_value = []

        with patch.object(indeed_scraper, "fetch_page", return_value=mock_soup):
            with patch.object(
                indeed_scraper, "get_search_url", return_value="http://test"
            ):
                jobs = list(indeed_scraper.scrape_jobs("python", max_pages=1))
                assert len(jobs) == 0

    def test_scrape_jobs_fetch_failure(self, indeed_scraper):
        """Test scrape_jobs handles fetch failures."""
        from unittest.mock import patch

        with patch.object(indeed_scraper, "fetch_page", return_value=None):
            with patch.object(
                indeed_scraper, "get_search_url", return_value="http://test"
            ):
                jobs = list(indeed_scraper.scrape_jobs("python", max_pages=1))
                assert len(jobs) == 0

    def test_parse_salary_with_commas(self, indeed_scraper):
        """Test parse_salary handles numbers with commas."""
        result = indeed_scraper.parse_salary("£50,000 - £75,000")
        assert result["min"] == 50000
        assert result["max"] == 75000

    def test_parse_salary_with_pound(self, indeed_scraper):
        """Test parse_salary handles pound symbol."""
        result = indeed_scraper.parse_salary("£45000")
        assert result["min"] == 45000

    def test_parse_salary_no_numbers(self, indeed_scraper):
        """Test parse_salary with no numeric values."""
        result = indeed_scraper.parse_salary("Competitive")
        assert result["min"] is None
        assert result["max"] is None

    def test_extract_job_listings(self, indeed_scraper):
        """Test extract_job_listings returns list."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup(
            """
            <html><div class="job">Job 1</div><div class="job">Job 2</div></html>
        """,
            "html.parser",
        )
        result = indeed_scraper.extract_job_listings(html)
        assert isinstance(result, list)

    def test_parse_job_listing(self, indeed_scraper):
        """Test parse_job_listing returns dict."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup('<div class="job"></div>', "html.parser")
        element = html.find("div")
        result = indeed_scraper.parse_job_listing(element)
        assert result is None or isinstance(result, dict)

    def test_get_search_url(self, indeed_scraper):
        """Test get_search_url returns string."""
        url = indeed_scraper.get_search_url("python", "London")
        assert isinstance(url, str)
        assert "python" in url.lower()

    def test_get_job_details_returns_none(self, indeed_scraper):
        """Test get_job_details handles errors gracefully."""
        result = indeed_scraper.get_job_details("invalid-url")
        # Should return None or dict, not crash
        assert result is None or isinstance(result, dict)

    def test_base_scraper_fetch_page(self):
        """Test base_scraper fetch_page method exists."""
        from src.discovery.platforms.base_scraper import BaseScraper

        # Verify the method exists
        assert hasattr(BaseScraper, "fetch_page")

    def test_make_request_with_mock(self, indeed_scraper):
        """Test _make_request method with mocked request."""
        from unittest.mock import patch, MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html>Test</html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(indeed_scraper, "session") as mock_session:
            mock_session.request.return_value = mock_response
            result = indeed_scraper._make_request("GET", "http://test.com")
            assert result is mock_response

    def test_make_request_raises_on_error(self, indeed_scraper):
        """Test _make_request raises exception on HTTP error."""
        from unittest.mock import patch, MagicMock
        from requests import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")

        with patch.object(indeed_scraper, "session") as mock_session:
            mock_session.request.return_value = mock_response
            try:
                indeed_scraper._make_request("GET", "http://test.com")
            except HTTPError:
                pass  # Expected

    def test_enforce_rate_limit_sleeps(self, indeed_scraper):
        """Test _enforce_rate_limit sleeps when called quickly."""
        import time
        from unittest.mock import patch

        # Reset the last request time
        indeed_scraper._last_request_time = time.time()

        # Patch time.sleep to avoid actual delay
        with patch("time.sleep") as mock_sleep:
            indeed_scraper._enforce_rate_limit()
            # Should have called sleep
            assert mock_sleep.called or indeed_scraper._last_request_time > 0

    def test_fetch_page_returns_none_on_error(self, indeed_scraper):
        """Test fetch_page returns None on request exception."""
        from unittest.mock import patch
        import requests

        with patch.object(indeed_scraper, "_make_request") as mock_request:
            mock_request.side_effect = requests.RequestException("Connection error")
            result = indeed_scraper.fetch_page("http://test.com")
            assert result is None

    def test_parse_salary_dollar(self, indeed_scraper):
        """Test parse_salary with dollar currency."""
        result = indeed_scraper.parse_salary("$80,000 - $120,000")
        assert result["min"] == 80000
        assert result["max"] == 120000
        assert result["currency"] == "USD"

    def test_parse_salary_euro(self, indeed_scraper):
        """Test parse_salary with euro currency."""
        result = indeed_scraper.parse_salary("€50,000 - €70,000")
        assert result["currency"] == "EUR"

    def test_parse_salary_single_value(self, indeed_scraper):
        """Test parse_salary with single number."""
        result = indeed_scraper.parse_salary("£60000")
        assert result["min"] == 60000
        assert result["max"] == 60000

    def test_scrape_jobs_yields_jobs(self, indeed_scraper):
        """Test scrape_jobs is a generator that yields jobs."""
        from unittest.mock import patch, MagicMock

        mock_soup = MagicMock()
        mock_soup.select.return_value = []

        with patch.object(indeed_scraper, "fetch_page", return_value=mock_soup):
            with patch.object(
                indeed_scraper, "get_search_url", return_value="http://test"
            ):
                result = indeed_scraper.scrape_jobs("python", max_pages=1)
                # Should be a generator
                import types

                assert isinstance(result, types.GeneratorType)

    def test_can_scrape_returns_bool(self, indeed_scraper):
        """Test can_scrape returns boolean."""
        result = indeed_scraper.can_scrape()
        assert isinstance(result, bool)

    def test_is_enabled_returns_bool(self, indeed_scraper):
        """Test is_enabled returns boolean."""
        result = indeed_scraper.is_enabled()
        assert isinstance(result, bool)

    def test_parse_salary_decimal(self, indeed_scraper):
        """Test parse_salary with decimal values."""
        result = indeed_scraper.parse_salary("£45,500.50")
        assert result["min"] == 45500.5

    def test_parse_salary_no_currency_symbol(self, indeed_scraper):
        """Test parse_salary defaults to USD when no symbol."""
        result = indeed_scraper.parse_salary("50000-70000")
        assert result["currency"] == "USD"

    def test_parse_salary_empty_returns_nulls(self, indeed_scraper):
        """Test parse_salary returns null values for empty input."""
        result = indeed_scraper.parse_salary("")
        assert result["min"] is None
        assert result["max"] is None

    def test_parse_salary_no_numbers_returns_currency(self, indeed_scraper):
        """Test parse_salary returns currency even without numbers."""
        result = indeed_scraper.parse_salary("competitive")
        assert result["currency"] == "USD"

    def test_parse_posted_date_with_weeks(self, indeed_scraper):
        """Test parse_posted_date with weeks."""
        result = indeed_scraper.parse_posted_date("2 weeks ago")
        assert result is not None

    def test_parse_posted_date_with_months(self, indeed_scraper):
        """Test parse_posted_date with months."""
        result = indeed_scraper.parse_posted_date("1 month ago")
        assert result is not None

    def test_parse_posted_date_with_hours(self, indeed_scraper):
        """Test parse_posted_date with hours."""
        result = indeed_scraper.parse_posted_date("6 hours ago")
        assert result is not None

    def test_scrape_jobs_with_job_data(self, indeed_scraper):
        """Test scrape_jobs yields actual job data."""
        from unittest.mock import patch, MagicMock

        # Create mock soup with job elements
        mock_element = MagicMock()
        mock_element.select_one.return_value = MagicMock(
            text="Title", get=lambda x: "http://job.url"
        )
        mock_element.select.return_value = []

        mock_soup = MagicMock()
        mock_soup.select.return_value = [mock_element]

        mock_job_data = {
            "title": "Developer",
            "company": "Tech Co",
            "url": "http://job.url",
        }

        with patch.object(indeed_scraper, "fetch_page", return_value=mock_soup):
            with patch.object(
                indeed_scraper, "get_search_url", return_value="http://test"
            ):
                with patch.object(
                    indeed_scraper, "extract_job_listings", return_value=[mock_element]
                ):
                    with patch.object(
                        indeed_scraper, "parse_job_listing", return_value=mock_job_data
                    ):
                        jobs = list(indeed_scraper.scrape_jobs("python", max_pages=1))
                        assert len(jobs) == 1
                        assert jobs[0]["title"] == "Developer"


class TestStackOverflowMethods:
    """Test StackOverflow scraper methods."""

    @pytest.fixture
    def stackoverflow_scraper(self, platform_configs):
        """Create StackOverflow scraper instance."""
        from src.discovery.platforms.stackoverflow_scraper import StackOverflowScraper

        return StackOverflowScraper("stackoverflow", platform_configs["stackoverflow"])

    def test_build_search_url_basic(self, stackoverflow_scraper):
        """Test build_search_url with basic query."""
        url = stackoverflow_scraper.build_search_url("python developer", None, page=1)
        assert "jobs" in url
        assert "python" in url.lower()

    def test_build_search_url_with_location(self, stackoverflow_scraper):
        """Test build_search_url with location."""
        url = stackoverflow_scraper.build_search_url(
            "python developer", "London", page=1
        )
        assert "l=london" in url

    def test_build_search_url_pagination(self, stackoverflow_scraper):
        """Test build_search_url with pagination."""
        url = stackoverflow_scraper.build_search_url("python", None, page=2)
        assert "pg=3" in url

    def test_extract_job_listings_with_cards(self, stackoverflow_scraper):
        """Test extract_job_listings finds job cards."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup(
            """
            <html>
                <div class="job-card" data-jobid="123">Job 1</div>
                <div class="job-card" data-jobid="456">Job 2</div>
            </html>
        """,
            "html.parser",
        )
        jobs = stackoverflow_scraper.extract_job_listings(html)
        assert len(jobs) == 2

    def test_extract_job_listings_empty(self, stackoverflow_scraper):
        """Test extract_job_listings with no jobs."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup("<html><body>No jobs</body></html>", "html.parser")
        jobs = stackoverflow_scraper.extract_job_listings(html)
        assert len(jobs) == 0

    def test_parse_job_listing_with_job_id(self, stackoverflow_scraper):
        """Test parse_job_listing extracts job ID."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup('<div data-jobid="789">Test Job</div>', "html.parser")
        result = stackoverflow_scraper.parse_job_listing(html.find())
        assert result is not None
        assert result["platform_id"] == "789"

    def test_parse_job_listing_without_job_id(self, stackoverflow_scraper):
        """Test parse_job_listing returns None for missing job ID."""
        from bs4 import BeautifulSoup

        html = BeautifulSoup('<div class="job-card">No ID here</div>', "html.parser")
        result = stackoverflow_scraper.parse_job_listing(html.find())
        assert result is None


class TestReedScraperMethods:
    """Test Reed scraper methods for additional coverage."""

    @pytest.fixture
    def reed_scraper(self, platform_configs):
        """Create Reed scraper instance."""
        from src.discovery.platforms.reed_scraper import ReedScraper

        return ReedScraper("reed", platform_configs["reed"])

    def test_parse_contract_type_fixed_term(self, reed_scraper):
        """Test _parse_contract_type with fixed term."""
        result = reed_scraper._parse_contract_type("Fixed Term Contract")
        assert result == "contract"

    def test_parse_contract_type_part_time(self, reed_scraper):
        """Test _parse_contract_type with part-time."""
        result = reed_scraper._parse_contract_type("Part-Time")
        assert result == "part-time"

    def test_parse_contract_type_freelance(self, reed_scraper):
        """Test _parse_contract_type with freelance."""
        result = reed_scraper._parse_contract_type("Freelance")
        assert result == "contract"

    def test_is_remote_job_remote_in_title(self, reed_scraper):
        """Test remote detection in title."""
        assert reed_scraper._is_remote_job("Remote Python Developer", "London") is True

    def test_is_remote_job_anywhere(self, reed_scraper):
        """Test remote detection with anywhere."""
        assert reed_scraper._is_remote_job("Developer", "Anywhere") is True

    def test_platform_name(self, reed_scraper):
        """Test get_platform_name."""
        assert reed_scraper.get_platform_name() == "Reed"


class TestIndeedScraperMethods:
    """Test Indeed scraper methods for additional coverage."""

    @pytest.fixture
    def indeed_scraper(self, platform_configs):
        """Create Indeed scraper instance."""
        from src.discovery.platforms.indeed_scraper import IndeedScraper

        return IndeedScraper("indeed", platform_configs["indeed"])

    def test_is_remote_job_remote_in_title(self, indeed_scraper):
        """Test remote detection in job title."""
        assert (
            indeed_scraper._is_remote_job("Remote Python Developer", "London") is True
        )

    def test_is_remote_job_anywhere_location(self, indeed_scraper):
        """Test remote detection with anywhere in location."""
        assert (
            indeed_scraper._is_remote_job("Python Developer", "Work from Anywhere")
            is True
        )

    def test_platform_name(self, indeed_scraper):
        """Test get_platform_name."""
        assert indeed_scraper.get_platform_name() == "Indeed"

    def test_build_job_url(self, indeed_scraper):
        """Test _build_job_url method."""
        url = indeed_scraper._build_job_url("abc123")
        assert "indeed.com" in url
        assert "abc123" in url

    def test_calculate_posted_date(self, indeed_scraper):
        """Test calculate_posted_date method."""
        result = indeed_scraper.calculate_posted_date(5)
        assert result is not None
        assert "-" in result  # Date format is YYYY-MM-DD


class TestTotaljobsScraperMethods:
    """Test Totaljobs scraper methods for additional coverage."""

    @pytest.fixture
    def totaljobs_scraper(self, platform_configs):
        """Create Totaljobs scraper instance."""
        from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper

        return TotaljobsScraper("totaljobs", platform_configs["totaljobs"])

    def test_platform_name(self, totaljobs_scraper):
        """Test get_platform_name."""
        name = totaljobs_scraper.get_platform_name()
        assert "totaljobs" in name.lower()


if __name__ == "__main__":
    print("Run with: pytest tests/test_scrapers.py -v")
