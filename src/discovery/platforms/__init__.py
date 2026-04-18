"""Platform scraper registry.

This package exposes a single registry API (decorator-based) implemented in
base_scraper.py, following ForgeSyte registry pattern guidance.
"""

# Import modules for side-effect registration via @register_scraper
from . import cvlibrary_scraper  # noqa: F401
from . import reed_scraper  # noqa: F401
from . import totaljobs_scraper  # noqa: F401

from .base_scraper import BaseScraper, get_scraper, list_scrapers, register_scraper

__all__ = ["BaseScraper", "get_scraper", "list_scrapers", "register_scraper"]
