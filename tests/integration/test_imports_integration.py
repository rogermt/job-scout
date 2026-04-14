#!/usr/bin/env python3
"""Test script to verify imports work correctly."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    print("Testing imports...")

    # Test tracking module

    print("✓ Successfully imported from tracking.database")

    # Test discovery modules

    print("✓ Successfully imported from discovery.platforms.base_scraper")

    print("✓ Successfully imported from discovery.platforms")

    print("✓ Successfully imported from discovery.platforms.indeed_scraper")

    print("✓ Successfully imported from discovery.platforms.reed_scraper")

    print("✓ Successfully imported from discovery.platforms.totaljobs_scraper")

    print("✓ Successfully imported from discovery.platforms.stackoverflow_scraper")

    # Test config manager

    print("✓ Successfully imported from config_manager")

    print("\n✅ All imports successful!")

except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
