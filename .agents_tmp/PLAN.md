# 1. OBJECTIVE

Increase test coverage from current levels to **80%** on these specific platform files:
- `src/discovery/platforms/base_scraper.py`: 34% → 80%
- `src/discovery/platforms/indeed_scraper.py`: 68% → 80%
- `src/discovery/platforms/job_matching.py`: 0% → 80%
- `src/discovery/platforms/reed_scraper.py`: 77% → 80%
- `src/discovery/platforms/stackoverflow_scraper.py`: 47% → 80%

Focus on **high-value edge cases and major functionality**, NOT minor tests or 100% coverage.

# 2. CONTEXT SUMMARY

The job-scout project has platform scrapers for Indeed, Reed, StackOverflow, and a base class. Current coverage is low on most files except reed_scraper.py (77%). The job_matching.py has 0% coverage and is a critical component for job filtering.

**Key files to test:**
- `base_scraper.py`: Rate limiting, salary parsing, date parsing, retry logic
- `indeed_scraper.py`: Salary parsing with multiple currencies/periods, remote detection, contract type parsing
- `job_matching.py`: The entire matching/filtering engine (all scoring methods)
- `reed_scraper.py`: Contract type parsing, remote detection, posted date parsing
- `stackoverflow_scraper.py`: Basic scraping functionality

# 3. APPROACH OVERVIEW

Prioritize high-value tests that cover:
1. **Edge cases** in parsing (empty inputs, unusual formats)
2. **Core business logic** in job_matching.py (the 0% coverage file)
3. **Multi-currency/period** salary parsing in scrapers
4. **Remote/policy detection** logic
5. **Contract type** parsing variations

Skip testing:
- Abstract method signatures (tested via concrete implementations)
- HTTP request retry logic (tested indirectly via mocked responses)
- Minor utility helpers

# 4. IMPLEMENTATION STEPS

## Step 1: Test job_matching.py (0% → 80%)
**Goal:** Add comprehensive tests for the JobMatcher class - the core filtering engine

- Create `tests/unit/test_job_matching.py` with tests for:
  - `match_job()`: matching jobs that pass/fail threshold
  - `_has_excluded_keywords()`: exclusion filtering
  - `_score_title()`: title pattern matching
  - `_score_keywords()`: keyword matching
  - `_score_location()`: UK/remote location scoring
  - `_score_salary()`: salary threshold matching
  - `_score_contract_type()`: contract type filtering
  - `_score_remote()`: remote policy scoring
  - `filter_jobs()`: batch filtering
  - Edge cases: empty preferences, no salary data, remote_only mode

## Step 2: Test base_scraper.py (34% → 80%)
**Goal:** Cover utility methods and rate limiting logic

- Add tests to existing `tests/unit/test_scrapers.py`:
  - `parse_salary()`: empty text, single number, range, GBP/USD/EUR, yearly/monthly/daily/hourly
  - `parse_posted_date()`: days, weeks, months, hours ago
  - `is_enabled()` / `can_scrape()`: enabled/disabled states
  - `has_next_page()`: pagination detection
  - `register_scraper()` / `get_scraper()` / `list_scrapers()`: registration functions
  - Edge cases: malformed salary text, invalid date formats

## Step 3: Test indeed_scraper.py (68% → 80%)
**Goal:** Cover missing high-value parsing methods

- Add tests to `tests/unit/test_indeed_scraper.py`:
  - `_parse_salary()`: all currency/period combinations
  - `_is_remote_job()`: remote in title, "anywhere" in location
  - `_parse_contract_type()`: permanent/contract/temporary variations
  - `get_platform_name()`: returns correct name
  - Edge cases: mixed currencies, unusual contract type strings

## Step 4: Test reed_scraper.py (77% → 80%)
**Goal:** Cover remaining edge cases

- Add tests to `tests/unit/test_reed_scraper.py`:
  - `_parse_contract_type()`: fixed term, part-time, freelance variations
  - `_parse_posted_date()`: date string output
  - `is_remote_job()`: remote detection edge cases
  - Edge cases: complex location strings with remote+hybrid

## Step 5: Test stackoverflow_scraper.py (47% → 80%)
**Goal:** Cover basic scraping functionality

- Add tests to `tests/unit/test_stackoverflow_scraper.py`:
  - `build_search_url()`: query, location, pagination
  - `extract_job_listings()`: CSS selector matching
  - `parse_job_listing()`: job ID extraction
  - `get_job_details()`: fetch and return
  - Edge cases: missing job ID, empty results

# 5. TESTING AND VALIDATION

**Success criteria:**
- All 5 files achieve ≥80% line coverage
- New tests focus on edge cases and high-value business logic
- No minor/micro tests added
- All existing tests still pass

**Validation command:**
```bash
pytest --cov=src.discovery.platforms --cov-report=term-missing
```

Expected result after implementation:
- `base_scraper.py`: ≥80%
- `indeed_scraper.py`: ≥80%
- `job_matching.py`: ≥80%
- `reed_scraper.py`: ≥80%
- `stackoverflow_scraper.py`: ≥80%
