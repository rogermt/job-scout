import sys

sys.path.append("/teamspace/studios/this_studio/job-scout/tests/mocks")

from src.config_manager import PlatformConfig
from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper


def test_totaljobs_scraper_initialization():
    scraper = TotaljobsScraper(platform_name="totaljobs", config=PlatformConfig())
    assert scraper.platform_name == "totaljobs"
