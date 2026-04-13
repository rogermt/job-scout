
import sys
sys.path.append("/teamspace/studios/this_studio/job-scout/tests/mocks")

from hermes_agent.gateway.config import PlatformConfig
from src.discovery.platforms.stackoverflow_scraper import StackOverflowScraper

def test_stackoverflow_scraper_initialization():
    scraper = StackOverflowScraper(platform_name="stackoverflow", config=PlatformConfig())
    assert scraper.platform_name == "stackoverflow"
