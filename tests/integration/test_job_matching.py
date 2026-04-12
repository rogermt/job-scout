#!/usr/bin/env python3
"""
Standalone test for the job matching algorithm using sample UK job data.

This test verifies:
1. UK location detection
2. Salary scoring with GBP focus
3. Remote job bonuses
4. Exclusion filters (recruiters, sales, etc.)
5. Reasonable match scores
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Monkey patch get_settings to avoid importing issues
from unittest.mock import Mock

mock_settings = Mock()
mock_settings.job_preferences.titles = ["software engineer", "python developer", "backend developer"]
mock_settings.job_preferences.keywords = ["python", "django", "aws", "microservices"]
mock_settings.job_preferences.exclude_keywords = ["recruiter", "commission", "sales", "b2b"]
mock_settings.job_preferences.contract_types = ["permanent", "contract", "full-time"]
mock_settings.job_preferences.locations = ["london", "remote", "uk"]
mock_settings.job_preferences.salary.min_gbp = 50000
mock_settings.job_preferences.salary.max_gbp = None
mock_settings.job_preferences.remote_only = False
mock_settings.job_preferences.get.return_value = 40.0  # min_score_threshold

# Mock the imports that might cause issues
sys.modules['src.config_manager'] = Mock()
sys.modules['src.config_manager'].get_settings = lambda: mock_settings
sys.modules['src.config_manager'].JobPreferences = Mock
sys.modules['src.config_manager'].Settings = Mock
sys.modules['src.logging_config'] = Mock()
sys.modules['src.logging_config'].get_logger = lambda name: Mock()

# Now import the job matcher
from src.job_discovery.job_matching import JobMatcher


@dataclass
class TestResult:
    test_name: str
    passed: bool
    details: str
    score: float = 0.0


class JobMatchingTester:
    """Test suite for the job matching algorithm."""
    
    def __init__(self):
        self.matcher = JobMatcher(mock_settings.job_preferences)
        self.results: List[TestResult] = []
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all test cases."""
        print("🧪 Starting Job Matching Algorithm Tests")
        print("=" * 50)
        
        self.test_uk_location_detection()
        self.test_salary_scoring_gbp()
        self.test_remote_bonuses()
        self.test_exclusion_filters()
        self.test_match_scores()
        self.test_various_job_platforms()
        
        print("\n" + "=" * 50)
        self.print_summary()
        
        return self.results
    
    def test_uk_location_detection(self):
        """Test UK location detection and scoring."""
        print("\n📍 Testing UK Location Detection")
        print("-" * 40)
        
        test_jobs = [
            {
                "id": "uk-london",
                "title": "Senior Software Engineer",
                "company": "Tech UK Ltd",
                "location": {"original": "London, England", "city": "London", "country": "UK"},
                "salary": {"min": 70000, "max": 90000, "currency": "GBP", "period": "yearly", "original": "£70k-£90k"},
                "contract_type": "permanent",
                "remote_policy": "hybrid",
                "remote_types": ["hybrid"],
                "description": "Python development role with Django and AWS",
                "skills": ["python", "django", "aws"]
            },
            {
                "id": "uk-remote",
                "title": "Python Developer",
                "company": "Remote First",
                "location": {"original": "Remote, United Kingdom", "city": "Remote", "country": "UK"},
                "salary": {"min": 55000, "max": 75000, "currency": "GBP", "period": "yearly", "original": "£55k-£75k"},
                "contract_type": "permanent",
                "remote_policy": "remote",
                "remote_types": ["fully_remote"],
                "description": "Remote Python developer needed for microservices",
                "skills": ["python", "microservices"]
            },
            {
                "id": "us-location",
                "title": "Software Engineer",
                "company": "US Tech Corp",
                "location": {"original": "San Francisco, CA, USA", "city": "San Francisco", "country": "USA"},
                "salary": {"min": 150000, "max": 200000, "currency": "USD", "period": "yearly", "original": "$150k-$200k"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "remote_types": [],
                "description": "Position based in SF",
                "skills": ["python"]
            },
            {
                "id": "scotland",
                "title": "Backend Developer",
                "company": "Scotland Tech",
                "location": {"original": "Edinburgh, Scotland", "city": "Edinburgh", "country": "UK"},
                "salary": {"min": 50000, "max": 65000, "currency": "GBP", "period": "yearly", "original": "£50k-£65k"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "remote_types": [],
                "description": "Backend development in Edinburgh",
                "skills": ["django"]
            }
        ]
        
        for job in test_jobs:
            matches, score, reasons = self.matcher.match_job(job)
            location_text = job['location']['original']
            is_uk = any(indicator in location_text.lower() for indicator in 
                       ["uk", "united kingdom", "britain", "england", "scotland", "wales", "northern ireland", "london"])
            
            expected_match = is_uk or job['remote_policy'] in ['remote', 'hybrid']
            passed = matches == expected_match
            
            self.results.append(TestResult(
                test_name=f"UK Location: {job['id']}",
                passed=passed,
                details=f"Location: {location_text} | UK: {is_uk} | Remote: {job['remote_policy']} | Score: {score:.1f}",
                score=score
            ))
            
            print(f"  {'✅' if passed else '❌'} {job['id']}: {location_text}")
            print(f"     Score: {score:.1f}/100 | UK: {is_uk} | Remote: {job['remote_policy']}")
    
    def test_salary_scoring_gbp(self):
        """Test salary scoring with GBP focus and currency conversion."""
        print("\n💷 Testing Salary Scoring (GBP Focus)")
        print("-" * 40)
        
        # Target is 50k GBP
        test_jobs = [
            {
                "id": "gbp-70k",
                "title": "Senior Python Developer",
                "company": "UK Co",
                "location": {"original": "London, UK"},
                "salary": {"min": 70000, "max": 85000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "description": "Python role",
                "skills": ["python"]
            },
            {
                "id": "gbp-45k",
                "title": "Python Developer",
                "company": "UK Co",
                "location": {"original": "London, UK"},
                "salary": {"min": 45000, "max": 50000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "description": "Python role",
                "skills": ["python"]
            },
            {
                "id": "gbp-35k",
                "title": "Junior Developer",
                "company": "UK Co",
                "location": {"original": "London, UK"},
                "salary": {"min": 35000, "max": 40000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "description": "Python role",
                "skills": ["python"]
            },
            {
                "id": "usd-100k",
                "title": "Software Engineer",
                "company": "US Co",
                "location": {"original": "Remote, US"},
                "salary": {"min": 100000, "max": 120000, "currency": "USD", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "remote",
                "description": "Python role",
                "skills": ["python"]
            }
        ]
        
        expected_scores = {
            "gbp-70k": 1.0,  # Above threshold
            "gbp-45k": 0.9,  # Meets threshold
            "gbp-35k": 0.6,  # Close
            "usd-100k": 1.0  # Should convert to ~80k GBP
        }
        
        for job in test_jobs:
            matches, score, reasons = self.matcher.match_job(job)
            salary = job['salary']
            
            # Extract salary info
            if salary['currency'] == 'GBP':
                salary_gbp = salary['min']
            elif salary['currency'] == 'USD':
                salary_gbp = salary['min'] * 0.8
            else:
                salary_gbp = salary['min']
            
            # Expected score based on conversion
            if salary_gbp >= 60000:
                exp_score = 1.0
            elif salary_gbp >= 50000:
                exp_score = 0.9
            elif salary_gbp >= 40000:
                exp_score = 0.6
            else:
                exp_score = 0.3
            
            actual_score = reasons['salary_match']
            passed = abs(actual_score - exp_score) < 0.1
            
            self.results.append(TestResult(
                test_name=f"Salary: {job['id']}",
                passed=passed,
                details=f"Salary: {salary['min']} {salary['currency']} ({salary_gbp:.0f} GBP) | Score: {reasons['salary_match']:.1f}",
                score=score
            ))
            
            print(f"  {'✅' if passed else '❌'} {job['id']}: {salary['min']:,} {salary['currency']} = {salary_gbp:,.0f} GBP")
            print(f"     Salary Score: {reasons['salary_match']:.1f}/1.0")
    
    def test_remote_bonuses(self):
        """Test remote policy detection and scoring."""
        print("\n🏠 Testing Remote Job Bonuses")
        print("-" * 40)
        
        test_jobs = [
            {
                "id": "remote-full",
                "title": "Senior Python Developer",
                "company": "Remote Co",
                "location": {"original": "Remote (UK)"},
                "salary": {"min": 65000, "max": 80000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "remote",
                "remote_types": ["fully_remote"],
                "description": "Fully remote role",
                "skills": ["python", "django"]
            },
            {
                "id": "hybrid-london",
                "title": "Python Developer",
                "company": "Hybrid Co",
                "location": {"original": "London, UK"},
                "salary": {"min": 60000, "max": 75000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "hybrid",
                "remote_types": ["hybrid"],
                "description": "2 days in office",
                "skills": ["python"]
            },
            {
                "id": "office-only",
                "title": "Backend Developer",
                "company": "Office Co",
                "location": {"original": "Manchester, UK"},
                "salary": {"min": 55000, "max": 70000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "remote_types": [],
                "description": "Office based only",
                "skills": ["python"]
            }
        ]
        
        for job in test_jobs:
            matches, score, reasons = self.matcher.match_job(job)
            
            remote_policy = job['remote_policy']
            remote_score = reasons['remote_match']
            
            # Expected remote score
            if remote_policy == "remote":
                exp_remote = 1.0
            elif remote_policy == "hybrid":
                exp_remote = 0.7
            else:
                exp_remote = 0.0
            
            passed = abs(remote_score - exp_remote) < 0.01
            
            self.results.append(TestResult(
                test_name=f"Remote: {job['id']}",
                passed=passed,
                details=f"Policy: {remote_policy} | Remote Score: {remote_score:.1f}",
                score=score
            ))
            
            print(f"  {'✅' if passed else '❌'} {job['id']}: {remote_policy} (score: {remote_score:.1f})")
    
    def test_exclusion_filters(self):
        """Test that exclusion filters work properly."""
        print("\n🚫 Testing Exclusion Filters")
        print("-" * 40)
        
        test_jobs = [
            {
                "id": "recruiter-job",
                "title": "Software Engineer - Recruiter Posting",
                "company": "Tech Recruiters Ltd",
                "location": {"original": "London, UK"},
                "salary": {"min": 60000, "max": 80000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "hybrid",
                "description": "Looking for software engineer. Contact our recruitment team.",
                "skills": ["python"]
            },
            {
                "id": "sales-role",
                "title": "Sales Engineer",
                "company": "B2B Solutions",
                "location": {"original": "London, UK"},
                "salary": {"min": 55000, "max": 70000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "description": "Commission-based sales role with B2B focus",
                "skills": ["sales"]
            },
            {
                "id": "commission-role",
                "title": "Software Developer",
                "company": "Commission Only Ltd",
                "location": {"original": "London, UK"},
                "salary": {"min": 30000, "max": 100000, "currency": "GBP", "period": "yearly"},
                "contract_type": "contract",
                "remote_policy": "remote",
                "description": "High earning potential with commission structure",
                "skills": ["python"]
            },
            {
                "id": "good-job",
                "title": "Senior Python Developer",
                "company": "Tech Company",
                "location": {"original": "London, UK"},
                "salary": {"min": 65000, "max": 85000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "hybrid",
                "description": "Looking for Python developer with Django and AWS",
                "skills": ["python", "django", "aws"]
            }
        ]
        
        for job in test_jobs:
            matches, score, reasons = self.matcher.match_job(job)
            
            # Check if any exclusion keywords appear
            text_to_check = " ".join([
                job.get("title", ""),
                job.get("company", ""),
                job.get("description", "")
            ]).lower()
            
            excluded_keywords = ["recruiter", "commission", "sales", "b2b"]
            has_exclusion = any(kw in text_to_check for kw in excluded_keywords)
            
            passed = (not matches) == has_exclusion
            
            self.results.append(TestResult(
                test_name=f"Exclusion: {job['id']}",
                passed=passed,
                details=f"Excluded: {has_exclusion} | Matched: {matches} | Score: {score:.1f}",
                score=score
            ))
            
            print(f"  {'✅' if passed else '❌'} {job['id']}: {'EXCLUDED' if not matches else 'MATCHED'} (has_exclusion: {has_exclusion})")
    
    def test_match_scores(self):
        """Test that match scores are reasonable and calculated correctly."""
        print("\n📊 Testing Match Score Calculations")
        print("-" * 40)
        
        # Perfect match job
        perfect_job = {
            "id": "perfect-match",
            "title": "Senior Python Developer",
            "company": "Python Tech Ltd",
            "location": {"original": "London, UK"},
            "salary": {"min": 70000, "max": 90000, "currency": "GBP", "period": "yearly"},
            "contract_type": "permanent",
            "remote_policy": "remote",
            "remote_types": ["fully_remote"],
            "description": "Looking for experienced software engineer with python, django, aws, microservices",
            "skills": ["python", "django", "aws", "microservices", "software engineering"]
        }
        
        # Mediocre match
        mediocre_job = {
            "id": "mediocre-match",
            "title": "Java Developer",
            "company": "Old School Corp",
            "location": {"original": "Birmingham, UK"},
            "salary": {"min": 45000, "max": 55000, "currency": "GBP", "period": "yearly"},
            "contract_type": "contract",
            "remote_policy": "none",
            "remote_types": [],
            "description": "Java enterprise development, some python experience helpful",
            "skills": ["java", "spring"]
        }
        
        # Poor match
        poor_job = {
            "id": "poor-match",
            "title": "Sales Representative",
            "company": "B2B Sales Ltd",
            "location": {"original": "New York, USA"},
            "salary": {"min": 40000, "max": 60000, "currency": "USD", "period": "yearly"},
            "contract_type": "permanent",
            "remote_policy": "none",
            "remote_types": [],
            "description": "Sales focused role with commission structure",
            "skills": ["sales", "b2b", "communication"]
        }
        
        perfect_matches, perfect_score, perfect_reasons = self.matcher.match_job(perfect_job)
        mediocre_matches, mediocre_score, mediocre_reasons = self.matcher.match_job(mediocre_job)
        poor_matches, poor_score, poor_reasons = self.matcher.match_job(poor_job)
        
        # Validate score ranges
        perfect_ok = perfect_score > 80 and perfect_matches
        mediocre_ok = 40 <= mediocre_score <= 80 and mediocre_matches
        poor_ok = poor_score < 40 and not poor_matches
        
        self.results.append(TestResult(
            test_name="Score: Perfect Match",
            passed=perfect_ok,
            details=f"Score: {perfect_score:.1f} | Matched: {perfect_matches} | Expected: >80",
            score=perfect_score
        ))
        
        self.results.append(TestResult(
            test_name="Score: Mediocre Match",
            passed=mediocre_ok,
            details=f"Score: {mediocre_score:.1f} | Matched: {mediocre_matches} | Expected: 40-80",
            score=mediocre_score
        ))
        
        self.results.append(TestResult(
            test_name="Score: Poor Match",
            passed=poor_ok,
            details=f"Score: {poor_score:.1f} | Matched: {poor_matches} | Expected: <40",
            score=poor_score
        ))
        
        print(f"  {'✅' if perfect_ok else '❌'} Perfect match: {perfect_score:.1f}/100")
        print(f"     Reasons: Title:{perfect_reasons['title_match']} Keywords:{perfect_reasons['keyword_matches']} "
              f"Location:{perfect_reasons['location_match']} Salary:{perfect_reasons['salary_match']} "
              f"Remote:{perfect_reasons['remote_match']}")
        
        print(f"  {'✅' if mediocre_ok else '❌'} Mediocre match: {mediocre_score:.1f}/100")
        print(f"  {'✅' if poor_ok else '❌'} Poor match: {poor_score:.1f}/100")
    
    def test_various_job_platforms(self):
        """Test with samples simulating different job platforms."""
        print("\n🌐 Testing Different Job Platforms")
        print("-" * 40)
        
        platform_jobs = [
            {
                "id": "reed-uk",
                "title": "Software Engineer | Python | Django | AWS | Remote",
                "company": "Reed.co.uk Tech",
                "location": {"original": "Bristol, UK (Remote)", "city": "Bristol", "country": "UK"},
                "salary": {"min": 55000, "max": 75000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "remote",
                "remote_types": ["fully_remote"],
                "description": "Exciting opportunity for a Python Developer to join our team. You will be working with Django, AWS, microservices architecture.",
                "skills": ["python", "django", "aws", "microservices"]
            },
            {
                "id": "indeed-contract",
                "title": "Python Developer - Contract - Immediate Start",
                "company": "Indeed Tech Ltd",
                "location": {"original": "London, England", "city": "London", "country": "UK"},
                "salary": {"min": 450, "max": 550, "currency": "GBP", "period": "daily"},
                "contract_type": "contract",
                "remote_policy": "hybrid",
                "remote_types": ["hybrid"],
                "description": "6 month contract for Python developer. Hybrid working 3 days in office.",
                "skills": ["python", "django"]
            },
            {
                "id": "stackoverflow-glasgow",
                "title": "Senior Backend Engineer",
                "company": "Stack Overflow Glasgow",
                "location": {"original": "Glasgow, Scotland", "city": "Glasgow", "country": "UK"},
                "salary": {"min": 65000, "max": 80000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "none",
                "remote_types": [],
                "description": "Senior backend role with Python, microservices, cloud architecture",
                "skills": ["python", "microservices"]
            },
            {
                "id": "totaljobs-recruiter",
                "title": "Python Developer - Via Recruitment Agency",
                "company": "Top Talent Recruiters",
                "location": {"original": "Remote, UK", "city": "Remote", "country": "UK"},
                "salary": {"min": 50000, "max": 65000, "currency": "GBP", "period": "yearly"},
                "contract_type": "permanent",
                "remote_policy": "remote",
                "remote_types": ["fully_remote"],
                "description": "Our client is looking for a Python developer",
                "skills": ["python"]
            }
        ]
        
        for job in platform_jobs:
            matches, score, reasons = self.matcher.match_job(job)
            
            # Special check for recruiter jobs
            is_recruiter = "recruit" in job['company'].lower() or "recruit" in job['title'].lower()
            expected_match = matches == (not is_recruiter)
            
            self.results.append(TestResult(
                test_name=f"Platform: {job['id']}",
                passed=expected_match,
                details=f"Platform: {job['id']} | Matched: {matches} | Score: {score:.1f}",
                score=score
            ))
            
            status = "✅" if expected_match else "❌"
            if is_recruiter:
                status = "🚫"  # Special symbol for recruiter exclusion
            
            print(f"  {status} {job['id']}: {job['company']}")
            print(f"     Match: {matches} | Score: {score:.1f}/100")
    
    def print_summary(self):
        """Print test summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"📊 Test Summary: {passed}/{total} passed")
        print()
        
        if failed > 0:
            print("❌ Failed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"   - {result.test_name}: {result.details}")
        else:
            print("✅ All tests passed!")
        
        # Print score statistics
        avg_score = sum(r.score for r in self.results) / total if total > 0 else 0
        max_score = max((r.score for r in self.results), default=0)
        min_score = min((r.score for r in self.results), default=0)
        
        print(f"\n📈 Score Statistics:")
        print(f"   Average: {avg_score:.1f}")
        print(f"   Maximum: {max_score:.1f}")
        print(f"   Minimum: {min_score:.1f}")


def main():
    """Run the test suite."""
    tester = JobMatchingTester()
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r.passed)
    if failed > 0:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
