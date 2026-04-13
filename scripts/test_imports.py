#!/usr/bin/env python3
"""Test script to verify circular import fixes.

Usage:
    source .venv/bin/activate
    python scripts/test_imports.py

Or with uv:
    uv run python scripts/test_imports.py

Note: This script adds project root to sys.path so 'src.' imports work
      (simulating pytest's pythonpath config).
"""

import sys
import os

# Get project root (parent of scripts directory)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Go up from scripts/ to project root

# Add project root to path if not already present
# This allows 'src.' imports to work (as configured in pyproject.toml)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Check if we're in a virtual environment
venv_path = os.path.join(project_root, ".venv", "bin", "python")
in_venv = sys.prefix != sys.base_prefix or os.path.exists(venv_path)

if not in_venv:
    print("Warning: This script works best inside the project venv.")
    print("Run: source .venv/bin/activate && python scripts/test_imports.py")
    print()

try:
    print("Testing imports...")

    # Test that we can import job_discovery modules without errors
    # Note: uses 'src.' prefix as configured in pyproject.toml pythonpath = ["src"]
    from src.discovery.platforms.base_scraper import BaseScraper  # noqa: F401

    print("✓ Successfully imported from src.discovery.platforms.base_scraper")

    from src.discovery.platforms.indeed_scraper import IndeedScraper  # noqa: F401

    print("✓ Successfully imported from src.discovery.platforms.indeed_scraper")

    from src.discovery.platforms.reed_scraper import ReedScraper  # noqa: F401

    print("✓ Successfully imported from src.discovery.platforms.reed_scraper")

    from src.discovery.platforms.totaljobs_scraper import TotaljobsScraper  # noqa: F401

    print("✓ Successfully imported from src.discovery.platforms.totaljobs_scraper")

    print("✓ Successfully imported from src.discovery.platforms.stackoverflow_scraper")

    # Test config manager
    from src.config_manager import get_settings  # noqa: F401

    print("✓ Successfully imported from src.config_manager")

    print("\n✅ All imports successful! Circular import issue resolved.")

except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
