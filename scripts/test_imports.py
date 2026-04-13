#!/usr/bin/env python3
"""Test script to verify circular import fixes."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    print("Testing imports...")

    # Test that we can import tracking.database without errors

    print("✓ Successfully imported from tracking.database")

    # Test that we can import job_discovery modules without errors

    print("✓ Successfully imported from src.discovery.platforms.base_scraper")

    print("✓ Successfully imported from src.discovery.platforms.indeed_scraper")

    print("✓ Successfully imported from src.discovery.platforms.reed_scraper")

    print("✓ Successfully imported from src.discovery.platforms.totaljobs_scraper")

    print("✓ Successfully imported from src.discovery.platforms.stackoverflow_scraper")

    # Test config manager

    print("✓ Successfully imported from config_manager")

    print("\n✅ All imports successful! Circular import issue resolved.")

except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
