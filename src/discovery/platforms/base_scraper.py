
from typing import Type, Optional, Generator, Any, Dict
from pathlib import Path

# Use absolute import for PlatformConfig
from hermes_agent.gateway.config import PlatformConfig

class BaseScraper:
    _scrapers: Dict[str, Type["BaseScraper"]] = {}

    def __init__(self, platform_name: str, config: PlatformConfig, rate_limit: Optional[int] = None):
        self.platform_name = platform_name
        self.config = config
        self.rate_limit = rate_limit

    @classmethod
    def register_scraper(cls, scraper_class: Type["BaseScraper"]):
        cls._scrapers[scraper_class.__name__] = scraper_class

    def _fetch_page(self, url: str) -> str:
        raise NotImplementedError

    def _generate_id(self) -> str:
        raise NotImplementedError

    def scrape_jobs(self, query: str, location: Optional[str] = None, max_pages: int = 1) -> Generator[Dict[str, Any], None, None]:
        raise NotImplementedError
