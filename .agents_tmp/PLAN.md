# 1. OBJECTIVE

Add Reed live integration test to catch selector changes, fix selectors.

# 2. CONTEXT SUMMARY

- Dependencies: already fixed in previous PR (merged)
- Code runs (HTTP 200), but returns 0 jobs - selectors outdated for current Reed.co.uk HTML

# 3. APPROACH OVERVIEW

Create live integration test that fetches real Reed.co.uk HTML, fix selectors, update unit tests.

---

**PR Title:** `fix: reed live integration test + selectors`

**PR Body:**
```markdown
## Changes
- Add `tests/integration/test_reed_scraper_live.py` - live HTTP test to Reed.co.uk
- Update `reed_scraper.py` selectors if current ones outdated
- Update unit test mock HTML if selectors changed

## Rationale
Unit tests use mock HTML - always pass. Need integration test hitting REAL Reed.co.uk to catch selector changes when site updates HTML.
```

---

# 4. IMPLEMENTATION STEPS

## Step 1: Create Reed live integration test
**Goal:** Test against REAL Reed.co.uk HTML

**Method:** Create `tests/integration/test_reed_scraper_live.py`

**Detailed Tasks:**
1.1. Create new file `tests/integration/test_reed_scraper_live.py`
1.2. Add imports: `requests`, `BeautifulSoup`, `pytest`
1.3. Create test function `test_reed_live_scraping()`:
    - Use requests.get() to fetch: `https://www.reed.co.uk/jobs?keywords=python&location=london`
    - Add User-Agent header
    - Assert status 200
    - Parse with BeautifulSoup
    - Test selectors: `soup.select("article.job-result, article.job-card")`
    - Assert len(jobs) > 0, else FAIL
    - Print first 3 job elements found (debug)
1.4. Add markers: `@pytest.mark.integration`

**Reference:** New file `tests/integration/test_reed_scraper_live.py`

## Step 2: Run tests and fix
**Goal:** Fix broken unit tests if selectors updated

**Detailed Tasks:**
2.1. Run integration test: `pytest tests/integration/test_reed_scraper_live.py -v`
2.2. If test FAILS (0 jobs found):
    - Inspect output - what selectors exist in real HTML?
    - Update reed_scraper.py line 51 with new selectors
2.3. Run unit tests: `pytest tests/unit/discovery/platforms/test_reed_scraper.py -v`
2.4. If unit tests FAIL (mock HTML needs update):
    - Update test_reed_scraper.py line ~100-108 with matching mock HTML

**Reference:**
- reed_scraper.py line 51
- tests/unit/discovery/platforms/test_reed_scraper.py (line 100-108)

# 5. TESTING AND VALIDATION

- Live test finds jobs > 0
- All unit tests pass
