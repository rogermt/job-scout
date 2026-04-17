import logging

import pytest

from src.config_manager import PlatformConfig
from src.discovery.platforms import get_scraper, list_scrapers

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def platform_configs():
    return {
        "reed": PlatformConfig(enabled=True, region="uk"),
        "totaljobs": PlatformConfig(enabled=True, region="uk"),
        "cvlibrary": PlatformConfig(enabled=True, region="uk"),
    }


class TestScraperStandards:
    def test_all_scrapers_registered(self):
        available_scrapers = list_scrapers()
        expected_scrapers = {"reed", "totaljobs", "cvlibrary"}
        assert expected_scrapers.issubset(set(available_scrapers))

    def test_scraper_imports(self, platform_configs):
        for platform_name, config in platform_configs.items():
            scraper = get_scraper(platform_name, config)
            assert scraper is not None
            assert scraper.platform_name == platform_name
            assert hasattr(scraper, "scrape_jobs")
            assert hasattr(scraper, "get_search_url")
            assert hasattr(scraper, "extract_job_listings")
            assert hasattr(scraper, "parse_job_listing")

    def test_no_print_statements_in_scrapers(self):
        import os
        import re

        scraper_dir = "src/discovery/platforms"
        for filename in os.listdir(scraper_dir):
            if filename.endswith("_scraper.py"):
                filepath = os.path.join(scraper_dir, filename)
                with open(filepath, "r") as f:
                    content = f.read()
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if re.search(r"^\t*print", line) and "__repr__" not in line:
                        pytest.fail(f"{filename}:{i} uses print() instead of logging")


class TestReedScraper:
    @pytest.fixture
    def reed_scraper(self, platform_configs):
        from src.discovery.platforms.reed_scraper import ReedScraper

        return ReedScraper("reed", config=platform_configs["reed"])

    def test_salary_parsing(self, reed_scraper):
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
            assert result == expected, f"Failed for {salary_text}"


class TestErrorHandling:
    def test_invalid_platform(self):
        config = PlatformConfig()
        result = get_scraper("invalid_platform", config)
        assert result is None

    def test_error_handling_works(self, platform_configs):
        scraper = get_scraper("reed", platform_configs["reed"])
        result = scraper.fetch_page("https://invalid-url-12345.com")
        assert result is None


class TestReedScraperMethods:
    @pytest.fixture
    def reed_scraper(self, platform_configs):
        from src.discovery.platforms.reed_scraper import ReedScraper

        return ReedScraper("reed", platform_configs["reed"])

    def test_parse_contract_type_fixed_term(self, reed_scraper):
        result = reed_scraper._parse_contract_type("Fixed Term Contract")
        assert result == "contract"

    def test_parse_contract_type_part_time(self, reed_scraper):
        result = reed_scraper._parse_contract_type("Part-Time")
        assert result == "part-time"

    def test_parse_contract_type_freelance(self, reed_scraper):
        result = reed_scraper._parse_contract_type("Freelance")
        assert result == "contract"

    def test_is_remote_job_remote_in_title(self, reed_scraper):
        assert reed_scraper._is_remote_job("Remote Python Developer", "London") is True

    def test_is_remote_job_anywhere(self, reed_scraper):
        assert reed_scraper._is_remote_job("Developer", "Anywhere") is True

    def test_platform_name(self, reed_scraper):
        assert reed_scraper.get_platform_name() == "Reed"


class TestTotaljobsScraperMethods:
    @pytest.fixture
    def totaljobs_scraper(self, platform_configs):
        from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper

        return TotaljobsScraper("totaljobs", platform_configs["totaljobs"])

    def test_platform_name(self, totaljobs_scraper):
        name = totaljobs_scraper.get_platform_name()
        assert "totaljobs" in name.lower()
