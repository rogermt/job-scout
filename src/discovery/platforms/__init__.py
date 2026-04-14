from typing import Dict, Type, Any
from .totaljobs_scraper import TotaljobsScraper
from .reed_scraper import ReedScraper
from .cvlibrary_scraper import CvlibraryScraper
from .cwjobs_scraper import CwjobsScraper

_scrapers: Dict[str, Type[Any]] = {
    "totaljobs": TotaljobsScraper,
    "reed": ReedScraper,
    "cvlibrary": CvlibraryScraper,
    "cwjobs": CwjobsScraper,
}


def list_scrapers() -> list[str]:
    return list(_scrapers.keys())


def get_scraper(name: str, config: Dict[str, Any]) -> Any:
    if name not in _scrapers:
        raise ValueError(f"Unknown scraper: {name}")
    return _scrapers[name](platform_name=name, config=config)
