# 1. OBJECTIVE

Fix `pyproject.toml` so that `pip install -e .` works locally without missing library errors.

# 2. CONTEXT SUMMARY

The project has runtime dependencies listed in `[project.optional-dependencies].test` instead of main `[project]` dependencies. When running `pip install -e .` locally, required packages are missing. CI/CD works because it installs `.[test]` which includes all deps.

Files involved:
- `/workspace/project/job-scout/pyproject.toml` - needs updating with all required runtime deps

# 3. APPROACH OVERVIEW

Move all missing runtime dependencies from `[project.optional-dependencies].test` into the main `[project].dependencies` array in `pyproject.toml`. This ensures `pip install -e .` works correctly without manual `pip install` commands.

# 4. IMPLEMENTATION STEPS

## Step 1: Update pyproject.toml with all runtime dependencies
**Goal:** Add all missing packages to main dependencies

**Method:** Edit `pyproject.toml` - append these packages to the `dependencies` array:
- `pydantic>=2.0.0`
- `pydantic-settings>=2.0.0`
- `email-validator>=2.0.0`
- `beautifulsoup4>=4.0.0`
- `requests>=2.0.0`
- `python-dateutil>=2.0.0`
- `click>=8.0.0`
- `rich>=13.0.0`

**Reference:** `/workspace/project/job-scout/pyproject.toml` lines 15-18

## Step 2: Verify installation works
**Goal:** Confirm `pip install -e .` works without missing deps

**Method:** Run `pip install -e .` and verify no ImportError

**Reference:** Terminal

# 5. TESTING AND VALIDATION

Run `pip install -e .` then `python -m src.main search -q "test" -l "London" --max-pages 1` - should run without ModuleNotFoundError.
