#!/usr/bin/env python3
"""Test script to verify imports work correctly."""

# ruff: noqa: F401

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    print("Testing imports...")

    # Test tracking module
    from src.tracking.database import init_database, get_session  # noqa: F401

    print("✓ Successfully imported from tracking.database")

    # Test discovery modules
    from src.discovery.platforms.base_scraper import BaseScraper  # noqa: F401

    print("✓ Successfully imported from discovery.platforms.base_scraper")

    import src.discovery.platforms  # noqa: F401

    print("✓ Successfully imported from discovery.platforms")

    from src.discovery.platforms.cvlibrary_scraper import CvlibraryScraper  # noqa: F401

    print("✓ Successfully imported from discovery.platforms.cvlibrary_scraper")

    from src.discovery.platforms.reed_scraper import ReedScraper  # noqa: F401

    print("✓ Successfully imported from discovery.platforms.reed_scraper")

    from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper  # noqa: F401

    print("✓ Successfully imported from discovery.platforms.totaljobs_scraper")

    from src.discovery.platforms.cwjobs_scraper import CwjobsScraper  # noqa: F401

    print("✓ Successfully imported from discovery.platforms.cwjobs_scraper")

    # Test config manager - use Settings instead of ConfigManager
    from src.config_manager import Settings, get_settings  # noqa: F401

    print("✓ Successfully imported from config_manager")

    print("\n✅ All imports successful!")

except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
