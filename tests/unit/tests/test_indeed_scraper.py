import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mocks"))

from src.config_manager import PlatformConfig
from src.discovery.platforms.indeed_scraper import IndeedScraper


def test_indeed_scraper_initialization():
    scraper = IndeedScraper(
        platform_name="indeed", config=PlatformConfig(), rate_limit=10
    )
    assert scraper.platform_name == "indeed"
    assert scraper.rate_limit == 10
