"""Unit tests for IndeedScraper.

These tests verify the IndeedScraper logic without making real HTTP requests.
All external dependencies (requests, BeautifulSoup) are mocked.
"""

from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup, Tag

from src.config_manager import PlatformConfig
from src.discovery.platforms.indeed_scraper import IndeedScraper


@pytest.fixture
def config() -> PlatformConfig:
    """Fixture providing test configuration."""
    return PlatformConfig(
        enabled=True,
        region="uk",
        keywords="software engineer",
        location="London",
        max_results=50,
        api_key=None,
        endpoint=None,
        extra_config={},
    )


@pytest.fixture
def scraper(config: PlatformConfig) -> IndeedScraper:
    """Fixture providing test scraper instance."""
    scraper = IndeedScraper("indeed", config)
    return scraper


class TestIndeedScraperInit:
    """Test scraper initialization."""

    def test_init_sets_correct_attributes(self, config: PlatformConfig) -> None:
        """Test that scraper initializes with correct attributes."""
        scraper = IndeedScraper("indeed", config)
        assert scraper.platform_name == "indeed"
        assert scraper.config == config
        assert scraper.rate_limit == 5  # Default from BaseScraper

    def test_init_inherits_rate_limit(self, config: PlatformConfig) -> None:
        """Test that rate limit is inherited from BaseScraper."""
        scraper = IndeedScraper("indeed", config)
        assert hasattr(scraper, "_last_request_time")
        assert hasattr(scraper, "session")
        assert scraper.session.headers["User-Agent"].startswith("Mozilla/5.0")  # type: ignore[arg-type]


class TestGetSearchUrl:
    """Test URL generation."""

    def test_get_search_url_basic(self, scraper: IndeedScraper) -> None:
        """Test basic URL generation without location."""
        url = scraper.get_search_url("software engineer")
        assert url.startswith("https://uk.indeed.com/jobs?q=software+engineer")
        assert "sort=date" in url

    def test_get_search_url_with_location(self, scraper: IndeedScraper) -> None:
        """Test URL with UK location."""
        url = scraper.get_search_url("software engineer", "London")
        assert "q=software+engineer" in url
        assert "l=London" in url
        assert "sort=date" in url
        assert "remote=true" not in url

    def test_get_search_url_remote(self, scraper: IndeedScraper) -> None:
        """Test URL generation with remote location."""
        url = scraper.get_search_url("software engineer", "remote")
        assert "remote=true" in url

    def test_get_search_url_with_pagination(self, scraper: IndeedScraper) -> None:
        """Test URL with pagination offset."""
        url = scraper.get_search_url("software engineer", "London", page=2)
        assert "start=20" in url  # Page 2 (2 * 10 offset)


class TestExtractJobListings:
    """Test job listing extraction."""

    def test_extract_job_listings_finds_cards(self, scraper: IndeedScraper) -> None:
        """Test extraction with mock BeautifulSoup containing job cards."""
        soup = BeautifulSoup(
            """
            <html>
                <div class="job_seen_beacon">Job 1</div>
                <div class="jobsearch-SerpJobCard">Job 2</div>
                <div class="job_seen_beacon">Job 3</div>
            </html>
            """,
            "html.parser",
        )

        cards = scraper.extract_job_listings(soup)
        assert len(cards) == 3
        assert all(isinstance(card, Tag) for card in cards)

    def test_extract_job_listings_empty_no_cards(self, scraper: IndeedScraper) -> None:
        """Test extraction with HTML containing no job cards."""
        soup = BeautifulSoup("<html><body>No jobs here</body></html>", "html.parser")
        cards = scraper.extract_job_listings(soup)
        assert len(cards) == 0

    def test_extract_job_listings_different_css_classes(
        self, scraper: IndeedScraper
    ) -> None:
        """Test extraction with various known CSS class variations."""
        soup = BeautifulSoup(
            """
            <html>
                <div data-jobid="123" class="job_seen_beacon test-class">Job 1</div>
                <div class="jobsearch-SerpJobCard mobile">Job 2</div>
            </html>
            """,
            "html.parser",
        )

        cards = scraper.extract_job_listings(soup)
        assert len(cards) == 2


class TestParseJobListing:
    """Test parsing single job listings."""

    def test_parse_job_listing_complete_card(self, scraper: IndeedScraper) -> None:
        """Test parsing a complete job card with all fields."""
        # Note: The parser expects job cards to be INSIDE a container, not to BE the container
        element = BeautifulSoup(
            """
            <div>
                <div class="job_seen_beacon" data-jk="abc123">
                    <h2 class="jobTitle"><span>Software Engineer</span></h2>
                    <span data-testid="company-name">Tech Corp</span>
                    <div data-testid="text-location">London, UK (Hybrid)</div>
                    <div class="salary-snippet">£50,000 - £70,000 a year</div>
                    <span class="date">1 day ago</span>
                </div>
            </div>
            """,
            "html.parser",
        )

        result = scraper.parse_job_listing(element)

        assert result is not None
        assert result["platform_id"] == "abc123"
        assert result["title"] == "Software Engineer"
        assert result["company"] == "Tech Corp"
        assert result["location"] == "London, UK (Hybrid)"
        assert result["salary_text"] == "£50,000 - £70,000 a year"
        assert "remote_policy" in result


class TestGetJobDetails:
    """Test fetching detailed job information."""

    @patch.object(IndeedScraper, "fetch_page")
    def test_get_job_details_success(
        self, mock_fetch: Mock, scraper: IndeedScraper
    ) -> None:
        """Test successful parsing of job details page."""
        mock_html = """
            <html>
                <div id="jobDescriptionText">
                    <p>We are looking for a senior developer.</p>
                    <ul><li>Python</li><li>Django</li></ul>
                </div>
                <div class="jobsearch-JobMetadataHeader-item">Remote</div>
            </html>
        """
        soup = BeautifulSoup(mock_html, "html.parser")
        mock_fetch.return_value = soup

        result = scraper.get_job_details("https://uk.indeed.com/viewjob?jk=abc123")

        assert result is not None
        assert "We are looking for a senior developer" in result["description"]
        assert "Python" in result["description"]
        assert result["remote_policy"] == "fully-remote"
        mock_fetch.assert_called_once_with("https://uk.indeed.com/viewjob?jk=abc123")

    @patch.object(IndeedScraper, "fetch_page")
    def test_get_job_details_fetch_failure(
        self, mock_fetch: Mock, scraper: IndeedScraper
    ) -> None:
        """Test handling when fetch_page returns None."""
        mock_fetch.return_value = None

        result = scraper.get_job_details("https://uk.indeed.com/viewjob?jk=abc123")

        assert result is None


class TestBuildJobUrl:
    """Test job URL construction."""

    def test_build_job_url_valid_id(self, scraper: IndeedScraper) -> None:
        """Test building job URL from valid platform ID."""
        url = scraper._build_job_url("abc123")
        assert url == "https://uk.indeed.com/viewjob?jk=abc123"

    def test_build_job_url_empty_id(self, scraper: IndeedScraper) -> None:
        """Test building job URL with empty ID."""
        url = scraper._build_job_url("")
        assert url == "https://uk.indeed.com/viewjob?jk="
