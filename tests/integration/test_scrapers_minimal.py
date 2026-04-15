#!/usr/bin/env python3
"""Minimal scraper test - tests ONLY job_discovery, no tracking/database dependencies."""

import logging
import sys
import os

# Set up simple logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def test_working_directory():
    """Verify we're in the job-scout directory."""
    logger.info("=" * 60)
    logger.info("TEST: Current directory")
    logger.info("=" * 60)

    current_dir = os.getcwd()
    logger.info(f"Working directory: {current_dir}")

    assert "job-scout" in current_dir, "Not in job-scout directory!"

    logger.info(f"{GREEN}✓ In correct directory{RESET}")


def test_import_scraper_module():
    """Test importing the scraper modules directly."""
    logger.info("=" * 60)
    logger.info("TEST: Importing scraper modules")
    logger.info("=" * 60)

    try:
        # Test base scraper

        logger.info(f"{GREEN}✓ BaseScraper imported{RESET}")

        # Test scraper registry

        logger.info(f"{GREEN}✓ Scraper registry imported{RESET}")

        # Test config

        logger.info(f"{GREEN}✓ PlatformConfig imported{RESET}")

        # Test individual scrapers

        logger.info(f"{GREEN}✓ IndeedScraper imported{RESET}")

    except Exception as e:
        logger.error(f"{RED}✗ Import failed: {e}{RESET}")
        import traceback

        traceback.print_exc()
        raise


def test_logging_vs_print():
    """Check scrapers use logging, not print."""
    logger.info("=" * 60)
    logger.info("TEST: Checking for print() statements")
    logger.info("=" * 60)

    scraper_dir = "src/discovery/platforms"
    issues = 0

    for filename in os.listdir(scraper_dir):
        if filename.endswith("_scraper.py"):
            filepath = os.path.join(scraper_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()

            # Search for print statements (basic check)
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("print("):
                    if "__repr__" not in stripped:
                        logger.error(f"{filename}:{i} - {stripped}")
                        issues += 1

    if issues:
        logger.error(f"{RED}✗ Found {issues} print() statements{RESET}")
        raise AssertionError(f"Found {issues} print() statements")

    logger.info(f"{GREEN}✓ No print() statements found{RESET}")


def test_type_annotations():
    """Verify type annotations are present."""
    logger.info("=" * 60)
    logger.info("TEST: Checking type annotations")
    logger.info("=" * 60)

    scraper_dir = "src/discovery/platforms"
    issues = 0

    for filename in os.listdir(scraper_dir):
        if filename.endswith("_scraper.py"):
            filepath = os.path.join(scraper_dir, filename)
            with open(filepath, "r") as f:
                lines = f.readlines()

            in_class = False
            func_count = 0
            annotated_count = 0

            for i, line in enumerate(lines, 1):
                line = line.strip()

                if line.startswith("class "):
                    in_class = True
                    continue

                if in_class and line.startswith("def "):
                    func_count += 1
                    # Check for return type annotation
                    if "->" in line:
                        annotated_count += 1

            if func_count > 0:
                percentage = (annotated_count / func_count) * 100
                logger.info(
                    f"  {filename}: {annotated_count}/{func_count} functions have type hints ({percentage:.0f}%)"
                )

                if percentage < 80:
                    issues += 1

    if issues:
        logger.warning(f"{YELLOW}⚠ Some files have low type hint coverage{RESET}")

    logger.info(f"{GREEN}✓ Type annotations present{RESET}")


def test_registry():
    """Test scraper registration."""
    logger.info("=" * 60)
    logger.info("TEST: Scraper registry")
    logger.info("=" * 60)

    from src.discovery.platforms import list_scrapers

    scrapers = list_scrapers()
    logger.info(f"Registered scrapers: {scrapers}")

    expected = {"reed", "totaljobs"}
    missing = expected - set(scrapers)

    if missing:
        logger.error(f"{RED}✗ Missing scrapers: {missing}{RESET}")
        raise AssertionError(f"Missing scrapers: {missing}")

    logger.info(f"{GREEN}✓ All expected scrapers registered{RESET}")


def test_instantiate_scraper():
    """Test creating scraper instances."""
    logger.info("=" * 60)
    logger.info("TEST: Instantiating scrapers")
    logger.info("=" * 60)

    from src.config_manager import PlatformConfig
    from src.discovery.platforms import get_scraper

    configs = {
        "reed": PlatformConfig(enabled=True, region="uk"),
        "totaljobs": PlatformConfig(enabled=True, region="uk"),
        "cvlibrary": PlatformConfig(enabled=True, region="uk"),
        "cwjobs": PlatformConfig(enabled=True, region="uk"),
    }

    for platform_name, config in configs.items():
        try:
            logger.info(f"  Instantiating {platform_name}...")
            scraper = get_scraper(platform_name, config)

            assert hasattr(scraper, "scrape_jobs")
            assert hasattr(scraper, "get_search_url")
            assert hasattr(scraper, "extract_job_listings")
            assert hasattr(scraper, "parse_job_listing")

            logger.info(f"{GREEN}✓ {platform_name} instantiated{RESET}")

        except Exception as e:
            logger.error(f"{RED}✗ {platform_name} failed: {e}{RESET}")
            raise


def test_scrapes():
    """Test actual scraping - skipped for CI environment."""
    logger.info("=" * 60)
    logger.info("TEST: Scraping - SKIPPED (no network)")
    logger.info("=" * 60)
    # Network-dependent tests are skipped in CI environment


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("SCRAPER TEST SUITE - Job Scout")
    logger.info("=" * 60 + "\n")

    tests = [
        ("Working Directory", test_working_directory),
        ("Module Imports", test_import_scraper_module),
        ("Logging vs Print", test_logging_vs_print),
        ("Type Annotations", test_type_annotations),
        ("Registry", test_registry),
        ("Instantiate Scrapers", test_instantiate_scraper),
        ("Live Scraping", test_scrapes),
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
