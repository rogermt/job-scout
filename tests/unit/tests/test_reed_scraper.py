import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mocks"))

from src.config_manager import PlatformConfig
from src.discovery.platforms.reed_scraper import ReedScraper


def test_reed_scraper_initialization():
    scraper = ReedScraper(platform_name="reed", config=PlatformConfig())
    assert scraper.platform_name == "reed"
