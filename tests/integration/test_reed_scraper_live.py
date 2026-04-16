"""Live Reed.co.uk integration test.

Tests against REAL Reed.co.uk to catch selector changes.
"""

import pytest
import requests
from bs4 import BeautifulSoup


@pytest.mark.integration
def test_reed_live_scraping() -> None:
    """Test scraping real Reed.co.uk to verify selectors work."""
    url = "https://www.reed.co.uk/jobs?keywords=python&location=london"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Current selectors in reed_scraper.py
    job_elements = soup.select("article.job-result, article.job-card")

    print("\n=== DEBUG ===")
    print(f"Status: {resp.status_code}")
    print(f"Content length: {len(resp.text)}")
    print(
        f"Selectors 'article.job-result, article.job-card' found: {len(job_elements)}"
    )

    if not job_elements:
        # Try alternative selectors
        alt_selectors = [
            ".job-card",
            ".job-result",
            "[data-job-id]",
            ".results-item",
            ".job-item",
        ]
        for sel in alt_selectors:
            found = soup.select(sel)
            print(f"  Alternative '{sel}': {len(found)}")

    # Print snippet of HTML structure
    if job_elements:
        print("\nFirst job element:")
        print(job_elements[0].prettify()[:500])
    else:
        print("\nNo job elements found. HTML snippet:")
        print(resp.text[3000:6000])

    # Assert jobs found
    assert len(job_elements) > 0, "No job elements found - selectors may have changed"


if __name__ == "__main__":
    test_reed_live_scraping()
