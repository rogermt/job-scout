import sys

sys.path.append("/teamspace/studios/this_studio/job-scout/tests/mocks")

from hermes_agent.gateway.config import PlatformConfig
from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper


def test_totaljobs_scraper_initialization():
    scraper = TotaljobsScraper(platform_name="totaljobs", config=PlatformConfig())
    assert scraper.platform_name == "totaljobs"
