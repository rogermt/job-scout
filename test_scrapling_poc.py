"""POC: Test 3 job sites with Scrapling using best practices.

Best practices from docs:
- Use StealthySession for persistent browser
- Use sync code (no async needed)
- Use Scrapling's built-in CSS parser (no BeautifulSoup)
- Use session context manager
"""

from scrapling.fetchers import StealthySession


def test_site(session, name, url):
    """Test a job site with StealthySession."""
    print(f"\n=== {name} ===")
    print(f"Loading: {url}")

    page = session.fetch(url, timeout=30000, network_idle=True)
    print(f"Status: {page.status}")
    print(f"Content: {len(page.body)} chars")

    # Use Scrapling's built-in CSS parser (no BeautifulSoup needed)
    articles = page.css("article")
    print(f"Found {len(articles)} articles")

    # Print first 3 job titles (selector: a inside article)
    for i, article in enumerate(articles[:3]):
        title = article.css("a::text").get()
        print(f"  {i+1}. {title}")

    return len(articles) > 0


def main():
    sites = [
        ("Reed.co.uk", "https://www.reed.co.uk/jobs?keywords=python&location=london"),
        ("Totaljobs", "https://www.totaljobs.com/jobs/python-jobs/in-london"),
        (
            "CVLibrary",
            "https://www.cvlibrary.co.uk/jobs?keywords=python&location=london",
        ),
    ]

    print("=== Scrapling StealthySession POC (Best Practices) ===\n")

    results = []

    # Use session context manager - browser stays open across requests
    with StealthySession(headless=True) as session:
        for name, url in sites:
            success = test_site(session, name, url)
            results.append((name, "✅" if success else "❌"))

    print("\n=== SUMMARY ===")
    for name, status in results:
        print(f"{name}: {status}")


if __name__ == "__main__":
    main()
