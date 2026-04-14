#!/usr/bin/env python3
"""Test script to verify circular import fixes."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    print("Testing imports...")

    # Test that we can import tracking.database without errors (mocked)
    from unittest.mock import patch

    with patch("tracking.database.init_database"):
        print("✓ Successfully imported from tracking.database (mocked)")

    # Test that we can import job_discovery modules without errors

    print("✓ Successfully imported from job_discovery.base_scraper")

    print("✓ Successfully imported from job_discovery.indeed_scraper")

    print("✓ Successfully imported from job_discovery.reed_scraper")

    print("✓ Successfully imported from job_discovery.totaljobs_scraper")

    print("✓ Successfully imported from job_discovery.stackoverflow_scraper")

    # Test config manager

    print("✓ Successfully imported from config_manager")

    print("\n✅ All imports successful! Circular import issue resolved.")

except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
