from typing import Dict, Type, Any
from .totaljobs_scraper import TotaljobsScraper
from .reed_scraper import ReedScraper
from .stackoverflow_scraper import StackOverflowScraper
from .indeed_scraper import IndeedScraper

# Registry of available scrapers
_scrapers: Dict[str, Type[Any]] = {
    "totaljobs": TotaljobsScraper,
    "reed": ReedScraper,
    "stackoverflow": StackOverflowScraper,
    "indeed": IndeedScraper,
}

def list_scrapers() -> list[str]:
    """List all available scrapers."""
    return list(_scrapers.keys())

def get_scraper(name: str, config: Dict[str, Any]) -> Any:
    """Get a scraper instance by name."""
    if name not in _scrapers:
        raise ValueError(f"Unknown scraper: {name}")
    return _scrapers[name](platform_name=name, config=config)