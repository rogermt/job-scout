import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mocks"))

from src.config_manager import PlatformConfig
from src.discovery.platforms.stackoverflow_scraper import StackOverflowScraper


def test_stackoverflow_scraper_initialization():
    scraper = StackOverflowScraper(
        platform_name="stackoverflow", config=PlatformConfig()
    )
    assert scraper.platform_name == "stackoverflow"
