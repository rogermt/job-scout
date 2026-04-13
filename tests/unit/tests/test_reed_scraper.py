import sys

sys.path.append("/teamspace/studios/this_studio/job-scout/tests/mocks")

from src.config_manager import PlatformConfig
from src.discovery.platforms.reed_scraper import ReedScraper


def test_reed_scraper_initialization():
    scraper = ReedScraper(platform_name="reed", config=PlatformConfig())
    assert scraper.platform_name == "reed"
