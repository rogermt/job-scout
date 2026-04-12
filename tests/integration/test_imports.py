#!/usr/bin/env python3
"""Test script to verify circular import fixes."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("Testing imports...")
    
    # Test that we can import tracking.database without errors
    from tracking.database import Job, get_database, DatabaseManager
    print("✓ Successfully imported from tracking.database")
    
    # Test that we can import job_discovery modules without errors
    from job_discovery.base_scraper import BaseScraper
    print("✓ Successfully imported from job_discovery.base_scraper")
    
    from job_discovery.indeed_scraper import IndeedScraper
    print("✓ Successfully imported from job_discovery.indeed_scraper")
    
    from job_discovery.reed_scraper import ReedScraper
    print("✓ Successfully imported from job_discovery.reed_scraper")
    
    from job_discovery.totaljobs_scraper import TotalJobsScraper
    print("✓ Successfully imported from job_discovery.totaljobs_scraper")
    
    from job_discovery.stackoverflow_scraper import StackOverflowScraper
    print("✓ Successfully imported from job_discovery.stackoverflow_scraper")
    
    # Test config manager
    from config_manager import Settings, PlatformConfig
    print("✓ Successfully imported from config_manager")
    
    print("\n✅ All imports successful! Circular import issue resolved.")
    
except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)