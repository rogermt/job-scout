#!/usr/bin/env python3
"""
Fix indentation error in base_scraper.py
The issue is at line 349 where def parse_salary is indented one level too deep.
"""

# Read the file
with open("src/job_discovery/base_scraper.py", "r") as f:
    lines = f.readlines()

# Fix the indentation on line 349 (index 348)
if len(lines) > 348:
    # Check if line 349 has a def statement
    line_349 = lines[348]
    if "def parse_salary" in line_349 and line_349.startswith(" "):
        print(f"Line 349 before: {repr(line_349)}")
        lines[348] = line_349.lstrip()
        print(f"Line 349 after: {repr(lines[348])}")

# Write back
with open("src/job_discovery/base_scraper.py", "w") as f:
    f.writelines(lines)

print("Fixed indentation error in base_scraper.py")
