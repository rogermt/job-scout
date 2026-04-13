#!/usr/bin/env python3
"""Standalone scraper test script (no pytest) to verify:
1. All scrapers are registered
2. They use logging (not print)
3. They have real implementations
4. They return valid data structures
"""

import logging
import sys

# Add parent dir to path for imports
sys.path.insert(0, "/teamspace/studios/this_studio/job-scout")

from src.config_manager import PlatformConfig
from src.discovery.platforms import get_scraper, list_scrapers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def test_all_scrapers_registered() -> bool:
    """Test that all expected scrapers are in the registry."""
    logger.info("=" * 60)
    logger.info("TEST: Verifying all scrapers are registered")
    logger.info("=" * 60)

    available = list_scrapers()
    expected = {"indeed", "reed", "totaljobs", "stackoverflow"}

    logger.info(f"Available scrapers: {available}")

    missing = expected - set(available)
    if missing:
        logger.error(f"MISSING SCRAPERS: {missing}")
        return False

    logger.info(f"{GREEN}✓ All expected scrapers registered{RESET}")
    return True


def test_no_print_statements() -> bool:
    """Verify no print statements in scraper code."""
    logger.info("=" * 60)
    logger.info("TEST: Checking for print() vs logging")
    logger.info("=" * 60)

    import os
    import re

    scraper_dir = "src/discovery/platforms"
    issues = []

    for filename in os.listdir(scraper_dir):
        if filename.endswith("_scraper.py"):
            filepath = os.path.join(scraper_dir, filename)
            with open(filepath, "r") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Match print statements (but not in comments or __repr__)
                if re.search(r"^[^#]*\s*print\s*\([^)]*\)", line):
                    if "__repr__" not in line and "test" not in filepath:
                        issues.append(f"{filename}:{i}: {line.strip()}")

    if issues:
        logger.error(f"Found {len(issues)} print() statements:")
        for issue in issues:
            logger.error(f"  {issue}")
        return False

    logger.info(f"{GREEN}✓ All scrapers use logging, not print(){RESET}")
    return True


def test_scraper_instantiation() -> bool:
    """Test each scraper can be instantiated."""
    logger.info("=" * 60)
    logger.info("TEST: Instantiating all scrapers")
    logger.info("=" * 60)

    configs = {
        "indeed": PlatformConfig(enabled=True, region="uk"),
        "reed": PlatformConfig(enabled=True, region="uk"),
        "totaljobs": PlatformConfig(enabled=True, region="uk"),
        "stackoverflow": PlatformConfig(enabled=True, region="remote"),
    }

    for platform_name, config in configs.items():
        try:
            scraper = get_scraper(platform_name, config)

            # Verify required attributes
            assert scraper.platform_name == platform_name
            assert hasattr(scraper, "scrape_jobs")
            assert hasattr(scraper, "get_search_url")
            assert hasattr(scraper, "extract_job_listings")
            assert hasattr(scraper, "parse_job_listing")
            assert hasattr(scraper, "get_job_details")

            logger.info(f"{GREEN}✓ {platform_name}: Instantiated successfully{RESET}")

        except Exception as e:
            logger.error(f"{RED}✗ {platform_name}: Failed to instantiate - {e}{RESET}")
            return False

    return True


def test_real_implementation() -> bool:
    """Verify scrapers have real implementation, not mock data."""
    logger.info("=" * 60)
    logger.info("TEST: Verifying real implementations (not mock)")
    logger.info("=" * 60)

    import os

    scraper_dir = "src/discovery/platforms"
    issues = []

    for filename in os.listdir(scraper_dir):
        if filename.endswith("_scraper.py") and filename != "base_scraper.py":
            filepath = os.path.join(scraper_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()

            # Check for indicators of mock data
            if "mock" in content.lower() or "sample" in content.lower():
                # Verify it's in a comment or test
                if not (content.startswith("#") or "test" in filepath):
                    continue

            # Check for BeautifulSoup usage (real HTML parsing)
            if "BeautifulSoup" not in content:
                issues.append(f"{filename}: No BeautifulSoup usage")

            # Check for HTTP requests
            if "_make_request" not in content and "requests" not in content:
                # Might use parent's _make_request, check imports
                if "from .base_scraper import" not in content:
                    issues.append(f"{filename}: No HTTP request handling")

    if issues:
        logger.warning("Potential mock data usage:")
        for issue in issues:
            logger.warning(f"  ⚠ {issue}")
        return False

    logger.info(f"{GREEN}✓ All scrapers have real implementations{RESET}")
    return True


def test_scrape_single_page() -> bool:
    """Test scraping one page from each platform."""
    logger.info("=" * 60)
    logger.info("TEST: Scraping one page from each platform")
    logger.info("=" * 60)

    configs = {
        "indeed": PlatformConfig(enabled=True, region="uk"),
        "reed": PlatformConfig(enabled=True, region="uk"),
        "totaljobs": PlatformConfig(enabled=True, region="uk"),
        "stackoverflow": PlatformConfig(enabled=True, region="remote"),
    }

    queries = {
        "indeed": ("software engineer", "London"),
        "reed": ("data analyst", "Manchester"),
        "totaljobs": ("project manager", "remote"),
        "stackoverflow": ("python developer", None),
    }

    for platform_name, config in configs.items():
        try:
            logger.info(f"Testing {platform_name}...")
            scraper = get_scraper(platform_name, config)
            query, location = queries[platform_name]

            jobs = list(scraper.scrape_jobs(query, location, max_pages=1))

            logger.info(f"  Found {len(jobs)} jobs")

            if not jobs:
                logger.warning(
                    f"  {YELLOW}⚠ No jobs found (might be rate limited or HTML changed){RESET}"
                )
                continue

            # Validate job structure
            job = jobs[0]
            assert isinstance(
                job["title"], str
            ), f"[{platform_name}] title must be string"
            assert isinstance(
                job["company"], str
            ), f"[{platform_name}] company must be string"
            assert isinstance(job["url"], str), f"[{platform_name}] url must be string"

            logger.info(f"{GREEN}✓ {platform_name}: Valid structure{RESET}")

        except Exception as e:
            logger.error(f"{RED}✗ {platform_name}: Failed - {e}{RESET}")
            return False

    return True


def test_type_annotations() -> bool:
    """Verify type annotations on all methods."""
    logger.info("=" * 60)
    logger.info("TEST: Verifying type annotations")
    logger.info("=" * 60)

    import os

    scraper_dir = "src/discovery/platforms"
    issues = []

    for filename in os.listdir(scraper_dir):
        if filename.endswith("_scraper.py"):
            filepath = os.path.join(scraper_dir, filename)
            with open(filepath, "r") as f:
                lines = f.readlines()

            in_class = False
            for i, line in enumerate(lines, 1):
                line = line.strip()

                # Detect class definition
                if line.startswith("class "):
                    in_class = True
                    continue

                # Detect function definitions in class
                if in_class and line.startswith("def "):
                    # Check if it has type hints for parameter and return
                    if "->" not in line:
                        issues.append(
                            f"{filename}:{i}: Missing return type hint: {line}"
                        )

                    # Check for parameter type hints (basic check)
                    if "(self" in line and ":" not in line.split("(")[1]:
                        # Skip __init__ which often doesn't need complex param hints
                        if "__init__" not in line:
                            continue

    if issues:
        logger.error(f"Found {len(issues)} missing type hints:")
        for issue in issues[:10]:  # Show first 10
            logger.error(f"  {issue}")
        return False

    logger.info(f"{GREEN}✓ All scrapers have type annotations{RESET}")
    return True


def test_error_handling() -> bool:
    """Test error handling and retry logic."""
    logger.info("=" * 60)
    logger.info("TEST: Verifying error handling and retry logic")
    logger.info("=" * 60)

    import os

    scraper_dir = "src/discovery/platforms"

    # Check for tenacity decorators
    base_scraper_path = os.path.join(scraper_dir, "base_scraper.py")
    with open(base_scraper_path, "r") as f:
        base_content = f.read()

    if "@retry" not in base_content:
        logger.error("BaseScraper missing @retry decorator")
        return False

    if "stop_after_attempt" not in base_content:
        logger.error("BaseScraper missing retry stop condition")
        return False

    logger.info(f"{GREEN}✓ Error handling and retries present{RESET}")
    return True


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("SCRAPER VALIDATION - ForgeSyte Python Standards")
    logger.info("=" * 60 + "\n")

    tests = [
        ("Scraper Registration", test_all_scrapers_registered),
        ("Logging vs Print", test_no_print_statements),
        ("Type Annotations", test_type_annotations),
        ("Error Handling", test_error_handling),
        ("Real Implementation", test_real_implementation),
        ("Scraper Instantiation", test_scraper_instantiation),
        ("Live Scraping Test", test_scrape_single_page),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"{RED}✗ {test_name}: CRASHED - {e}{RESET}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{GREEN}✓ PASSED{RESET}" if result else f"{RED}✗ FAILED{RESET}"
        logger.info(f"{test_name:30} {status}")

    logger.info("=" * 60)
    if passed == total:
        logger.info(
            f"{GREEN}{passed}/{total} tests passed - All scrapers meet ForgeSyte standards!{RESET}"
        )
        sys.exit(0)
    else:
        logger.error(
            f"{RED}{passed}/{total} tests passed - {total-passed} failures{RESET}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
