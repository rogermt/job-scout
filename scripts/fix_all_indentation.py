#!/usr/bin/env python3
"""
Fix all indentation errors in base_scraper.py
Some methods have wrong indentation (one level too deep).
"""

import re

# Read the file
with open("src/job_discovery/base_scraper.py", "r") as f:
    content = f.read()

# Fix method definitions that are indented too much
# Pattern: line starting with space followed by def
fixed_content = re.sub(r"^ (def \w+)", r"\1", content, flags=re.MULTILINE)

# Count changes
changes = len(re.findall(r"^ def \w+", content, re.MULTILINE))

# Write back
with open("src/job_discovery/base_scraper.py", "w") as f:
    f.write(fixed_content)

print(f"Fixed {changes} methods with wrong indentation")
print("Fixed all indentation errors in base_scraper.py")
