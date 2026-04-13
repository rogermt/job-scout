
import sys
sys.path.append("/teamspace/studios/this_studio/job-scout/tests/mocks")

from src.discovery.platforms import TotaljobsScraper, ReedScraper, StackOverflowScraper, IndeedScraper
from hermes_agent.gateway.config import PlatformConfig

def test_scraper_initialization():
    totaljobs = TotaljobsScraper(platform_name="totaljobs", config=PlatformConfig())
    reed = ReedScraper(platform_name="reed", config=PlatformConfig())
    stackoverflow = StackOverflowScraper(platform_name="stackoverflow", config=PlatformConfig())
    indeed = IndeedScraper(platform_name="indeed", config=PlatformConfig(), rate_limit=10)
    assert totaljobs.platform_name == "totaljobs"
    assert reed.platform_name == "reed"
    assert stackoverflow.platform_name == "stackoverflow"
    assert indeed.platform_name == "indeed"
