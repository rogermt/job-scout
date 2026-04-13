"""Unit tests for TotaljobsScraper.

Tests Totaljobs job scraping logic with mocked external dependencies.
Unit tests do NOT make real HTTP requests.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper


class TestInit:
    """Test initialization."""

    def test_init_sets_correct_attributes(self) -> None:
        """Test that scraper initializes with correct attributes."""
        mock_config = Mock()
        mock_config.enabled = True

        scraper = TotaljobsScraper("totaljobs", mock_config)

        assert scraper.base_url == "https://www.totaljobs.com"
        assert scraper.jobs_per_page == 20
        assert scraper.platform_name == "totaljobs"


class TestBuildSearchUrl:
    """Test URL generation."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_build_search_url_basic(self, scraper: TotaljobsScraper) -> None:
        """Test basic URL generation without location."""
        url = scraper.build_search_url("software engineer", None, page=1)
        assert "https://www.totaljobs.com/jobs" in url
        assert "software-engineer-jobs" in url

    def test_build_search_url_with_location(self, scraper: TotaljobsScraper) -> None:
        """Test URL with location."""
        url = scraper.build_search_url("software engineer", "London", page=1)
        assert "software-engineer-jobs" in url
        assert "in-london" in url or "london" in url.lower()

    def test_build_search_url_pagination(self, scraper: TotaljobsScraper) -> None:
        """Test URL pagination."""
        url_page25 = scraper.build_search_url("python", "Manchester", page=25)
        assert "page=25" in url_page25 or "25" in url_page25

    def test_build_search_url_special_characters(
        self, scraper: TotaljobsScraper
    ) -> None:
        """Test URL encoding with special characters."""
        url = scraper.build_search_url("senior python developer", "Birmingham", page=1)
        assert "senior" in url and "python" in url and "developer" in url


class TestGetSearchUrl:
    """Test get_search_url (abstract method)."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_get_search_url_delegates_to_build(self, scraper: TotaljobsScraper) -> None:
        """Test that get_search_url delegates to build_search_url."""
        url = scraper.get_search_url("python", "London", page=3)
        assert "page=3" in url
        assert "python" in url


class TestExtractJobListings:
    """Test extract_job_listings (abstract method)."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_extract_job_listings_finds_items(self, scraper: TotaljobsScraper) -> None:
        """Test extraction of job items."""
        html = """
        <html>
        <body>
        <div class="job-item">Job 1</div>
        <div class="job-item">Job 2</div>
        <div class="other-item">Not a job</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = scraper.extract_job_listings(soup)

        assert len(jobs) == 2
        assert all(hasattr(job, "get") for job in jobs)


class TestParseJobListing:
    """Test parse_job_listing (abstract method)."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_parse_job_listing_complete_card(self, scraper: TotaljobsScraper) -> None:
        """Test parsing a complete job card."""
        html = """
        <div class="job-item">
        <h2 class="job-title">Senior Python Developer</h2>
        <div class="company">Tech Corp Ltd</div>
        <div class="location">London, UK</div>
        <div class="salary">£40,000 - £50,000 per annum</div>
        <div class="job-type">Permanent</div>
        <time datetime="2024-01-15">2 days ago</time>
        <div class="job-description">Exciting Python developer role...</div>
        <a href="/job/senior-python-developer">View Job</a>
        </div>
        """
        card = BeautifulSoup(html, "html.parser")
        result = scraper.parse_job_listing(card)

        assert result is not None
        assert result["title"] == "Senior Python Developer"
        assert result["company"] == "Tech Corp Ltd"
        assert result["location"]["original"] == "London, UK"
        assert result["salary"]["original"] == "£40,000 - £50,000 per annum"
        assert result["contract_type"] == "permanent"

    def test_parse_job_listing_minimal_card(self, scraper: TotaljobsScraper) -> None:
        """Test parsing a minimal job card with few fields."""
        html = """
        <div class="job-item">
        <h2 class="job-title">Developer</h2>
        </div>
        """
        card = BeautifulSoup(html, "html.parser")
        result = scraper.parse_job_listing(card)

        assert result is not None
        assert result["title"] == "Developer"
        assert result["company"] == "Unknown"
        assert result["location"]["original"] == "Unknown"


class TestParseSalary:
    """Test salary parsing."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_parse_salary_range(self, scraper: TotaljobsScraper) -> None:
        """Test parsing salary range."""
        result = scraper._parse_salary("£40,000 - £50,000 per annum")

        assert result["min"] == 40000
        assert result["max"] == 50000
        assert result["currency"] == "GBP"
        assert result["period"] == "yearly"

    def test_parse_salary_single_value(self, scraper: TotaljobsScraper) -> None:
        """Test parsing single salary value."""
        result = scraper._parse_salary("£45000 per annum")

        assert result["min"] == 45000
        assert result["max"] == 45000
        assert result["currency"] == "GBP"

    def test_parse_salary_daily(self, scraper: TotaljobsScraper) -> None:
        """Test parsing daily rate."""
        result = scraper._parse_salary("£300 - £400 per day")

        assert result["min"] == 300
        assert result["max"] == 400
        assert result["period"] == "daily"

    def test_parse_salary_negotiable(self, scraper: TotaljobsScraper) -> None:
        """Test parsing negotiable salary."""
        result = scraper._parse_salary("Competitive")

        assert result["min"] is None
        assert result["max"] is None


class TestOtherMethods:
    """Test other utility methods."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_parse_contract_type(self, scraper: TotaljobsScraper) -> None:
        """Test contract type parsing."""
        assert scraper._parse_contract_type("Permanent") == "permanent"
        assert scraper._parse_contract_type("Contract") == "contract"
        assert scraper._parse_contract_type("Temporary") == "temporary"
        assert scraper._parse_contract_type("Unknown") is None

    def test_is_remote_job_detects_remote(self, scraper: TotaljobsScraper) -> None:
        """Test remote job detection."""
        assert scraper._is_remote_job("Remote Developer", "Anywhere") is True
        assert scraper._is_remote_job("Python Developer", "London") is False
        assert scraper._is_remote_job("Work from home role", "UK") is True

    def testparse_posted_date_with_valid_days_ago(
        self, scraper: TotaljobsScraper
    ) -> None:
        """Test posted date calculation."""
        # "2 days ago" should create a date 2 days in the past
        result = scraper.parse_posted_date("2 days ago")

        # Should return a datetime object
        assert isinstance(result, datetime)

        # For "2 days ago", it should be roughly 2 days old
        import datetime as dt

        age = (dt.datetime.now() - result).days
        assert 1 <= age <= 3  # Allow some flexibility

    def test_platform_name(self, scraper: TotaljobsScraper) -> None:
        """Test platform name."""
        assert scraper.get_platform_name() == "Totaljobs"


class TestGetJobDetails:
    """Test get_job_details (abstract method)."""

    @pytest.fixture
    def scraper(self) -> TotaljobsScraper:
        """Fixture for scraper instance."""
        mock_config = Mock()
        mock_config.enabled = True
        return TotaljobsScraper("totaljobs", mock_config)

    def test_get_job_details_delegates(self, scraper: TotaljobsScraper) -> None:
        """Test that get_job_details delegates to scrape_job_details."""
        # Mock the internal method
        with patch.object(
            scraper, "scrape_job_details", return_value="Test description"
        ):
            result = scraper.get_job_details("https://test.com/job/123")

            assert result is not None
            assert result["description"] == "Test description"
            assert result["url"] == "https://test.com/job/123"
