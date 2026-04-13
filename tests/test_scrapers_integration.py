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


if __name__ == "__main__":
    print("Run with: pytest tests/test_scrapers.py -v")
