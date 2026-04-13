import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mocks"))

from src.config_manager import PlatformConfig
from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper


def test_totaljobs_scraper_initialization():
    scraper = TotaljobsScraper(platform_name="totaljobs", config=PlatformConfig())
    assert scraper.platform_name == "totaljobs"
