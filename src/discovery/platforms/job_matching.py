"""Job matching algorithm for filtering and scoring job listings.

This module provides intelligent job matching based on user preferences including:
- Job titles and keywords matching
- Location filters (UK + remote focus)
- Salary range validation
- Experience level matching
- Contract type filtering
- Company size preferences
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from src.config_manager import JobPreferences

logger = None  # Will be set by _init_logger()


def _init_logger():
    global logger
    if logger is None:
        from src.logging_config import get_logger

        logger = get_logger(__name__)
    return logger


def get_settings():
    """Get configuration settings (lazy import to avoid circular imports)."""
    from src.config_manager import get_settings

    return get_settings()


def get_job_preferences():
    """Get job preferences (lazy import to avoid circular imports)."""
    from src.config_manager import JobPreferences

    return JobPreferences


class JobMatcher:
    """Intelligent job matching and filtering engine.

    The matcher evaluates jobs against user preferences and assigns relevance scores.
    It prioritizes UK jobs and remote positions as configured.
    """

    def __init__(self, preferences: Optional[JobPreferences] = None):
        """Initialize job matcher with user preferences.

        Args:
            preferences: JobPreferences from configuration
        """
        self.preferences = preferences or get_settings().job_preferences
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        # Title patterns
        self.title_patterns = []
        if self.preferences.titles:
            for title in self.preferences.titles:
                # Create case-insensitive pattern with word boundaries
                pattern = re.compile(r"\b" + re.escape(title.lower()) + r"\b", re.I)
                self.title_patterns.append(pattern)

        # Keyword patterns
        self.keyword_patterns = []
        if self.preferences.keywords:
            for keyword in self.preferences.keywords:
                pattern = re.compile(r"\b" + re.escape(keyword.lower()) + r"\b", re.I)
                self.keyword_patterns.append(pattern)

        # Exclude keyword patterns
        self.exclude_patterns = []
        if self.preferences.exclude_keywords:
            for keyword in self.preferences.exclude_keywords:
                pattern = re.compile(r"\b" + re.escape(keyword.lower()) + r"\b", re.I)
                self.exclude_patterns.append(pattern)

    def match_job(self, job_data: Dict[str, Any]) -> Tuple[bool, float, Dict[str, Any]]:
        """Evaluate if a job matches user preferences and calculate relevance score.

        Args:
            job_data: Job data dictionary from scraper

        Returns:
            Tuple of (matches: bool, score: float, reasons: dict)
        """
        score = 0.0
        reasons = {
            "title_match": False,
            "keyword_matches": 0,
            "location_match": False,
            "salary_match": False,
            "experience_match": False,
            "contract_match": False,
            "remote_match": False,
            "excluded": False,
        }

        # Check exclusions first (fastest)
        if self._has_excluded_keywords(job_data):
            reasons["excluded"] = True
            return False, 0.0, reasons

        # Title matching (high weight: 30 points)
        title_score = self._score_title(job_data)
        if title_score > 0:
            reasons["title_match"] = True
            score += title_score * 30

        # Keyword matching (medium weight: 20 points)
        keyword_score = self._score_keywords(job_data)
        reasons["keyword_matches"] = int(keyword_score * 10)
        score += keyword_score * 20

        # Location matching (high weight: 25 points)
        location_score = self._score_location(job_data)
        if location_score > 0:
            reasons["location_match"] = True
            score += location_score * 25

        # Salary matching (medium weight: 15 points)
        salary_score = self._score_salary(job_data)
        if salary_score > 0:
            reasons["salary_match"] = True
            score += salary_score * 15

        # Contract type matching (low weight: 5 points)
        contract_score = self._score_contract_type(job_data)
        if contract_score > 0:
            reasons["contract_match"] = True
            score += contract_score * 5

        # Remote policy bonus (UK focus)
        remote_score = self._score_remote(job_data)
        if remote_score > 0:
            reasons["remote_match"] = True
            score += remote_score * 5

        # Normalize score to 0-100
        score = min(score, 100.0)

        # Determine if job passes threshold
        matches = score >= (
            self.preferences.get("min_score_threshold", 40.0)
            if self.preferences is not None and hasattr(self.preferences, "get")
            else 40.0
        )

        if matches:
            if logger is not None:
                logger.debug(
                    "Job matched preferences",
                    extra={
                        "job_id": job_data.get("id"),
                        "title": job_data.get("title"),
                        "score": round(score, 2),
                    },
                )

        return matches, score, reasons

    def _has_excluded_keywords(self, job_data: Dict[str, Any]) -> bool:
        """Check if job contains excluded keywords.

        Args:
            job_data: Job data dictionary

        Returns:
            True if job contains excluded keywords
        """
        if not self.exclude_patterns:
            return False

        text_to_check = " ".join(
            [
                job_data.get("title", ""),
                job_data.get("company", ""),
                job_data.get("description", ""),
                job_data.get("location", {}).get("original", ""),
            ]
        ).lower()

        for pattern in self.exclude_patterns:
            if pattern.search(text_to_check):
                if logger is not None:
                    logger.debug(
                        "Job excluded by keyword filter",
                        extra={
                            "job_id": job_data.get("id"),
                            "keyword": pattern.pattern,
                        },
                    )
                return True

        return False

    def _score_title(self, job_data: Dict[str, Any]) -> float:
        """Score job based on title match.

        Args:
            job_data: Job data dictionary

        Returns:
            Score from 0.0 to 1.0
        """
        if not self.title_patterns:
            return 1.0  # No preferences = accept all

        title = job_data.get("title", "").lower()
        max_score = 0.0

        for pattern in self.title_patterns:
            if pattern.search(title):
                # Bonus for exact matches
                exact_match = pattern.pattern.strip(r"\b").strip()
                if exact_match.lower() in title:
                    max_score = max(max_score, 1.0)
                else:
                    max_score = max(max_score, 0.8)

        return max_score

    def _score_keywords(self, job_data: Dict[str, Any]) -> float:
        """Score job based on keyword matches.

        Args:
            job_data: Job data dictionary

        Returns:
            Score from 0.0 to 1.0 based on keyword matches
        """
        if not self.keyword_patterns:
            return 1.0  # No preferences = accept all

        text_to_check = " ".join(
            [
                job_data.get("title", ""),
                job_data.get("description", ""),
                job_data.get("company", ""),
                " ".join(job_data.get("skills", [])),
            ]
        ).lower()

        matches = 0
        for pattern in self.keyword_patterns:
            if pattern.search(text_to_check):
                matches += 1

        return min(matches / len(self.keyword_patterns), 1.0)

    def _score_location(self, job_data: Dict[str, Any]) -> float:
        """Score job based on location preferences (UK focus).

        Args:
            job_data: Job data dictionary

        Returns:
            Score from 0.0 to 1.0
        """
        location = job_data.get("location", {})
        location_text = location.get("original", "").lower()

        # Remote has highest priority if enabled
        if self.preferences.remote_only:
            remote_policy = job_data.get("remote_policy", "none")
            if remote_policy != "none" or len(job_data.get("remote_types", [])) > 0:
                return 1.0
            return 0.0

        # Check if UK location
        uk_indicators = [
            "uk",
            "united kingdom",
            "britain",
            "england",
            "scotland",
            "wales",
            "northern ireland",
            "london",
        ]
        for indicator in uk_indicators:
            if indicator in location_text:
                return 1.0

        # Remote fallback for UK residents
        remote_policy = job_data.get("remote_policy", "none")
        if remote_policy != "none" or len(job_data.get("remote_types", [])) > 0:
            return 0.8  # Remote is good for UK workers

        # If user specified locations, check there
        if self.preferences.locations:
            for pref_location in self.preferences.locations:
                if pref_location.lower() in location_text:
                    return 0.9
        return 0.0

    def _score_salary(self, job_data: Dict[str, Any]) -> float:
        """Score job based on salary expectations (UK focus).

        Args:
            job_data: Job data dictionary

        Returns:
            Score from 0.0 to 1.0
        """
        if self.preferences.salary is None or "min_gbp" not in self.preferences.salary:
            return 1.0  # No salary requirements

        salary = job_data.get("salary", {})
        min_salary = salary.get("min")
        # max_salary = salary.get("max")
        currency = salary.get("currency", "GBP")
        period = salary.get("period", "yearly")

        if not min_salary:
            return 0.5  # Unknown salary = neutral

        # Convert to yearly GBP for comparison
        target_min = (
            self.preferences.salary.get("min_gbp", 0)
            if self.preferences is not None
            and hasattr(self.preferences, "salary")
            and self.preferences.salary is not None
            and hasattr(self.preferences.salary, "get")
            else 0
        )

        # Convert based on currency and period
        if currency == "USD":
            min_salary_gbp = min_salary * 0.8  # Approximate conversion
        elif currency == "EUR":
            min_salary_gbp = min_salary * 0.85  # Approximate conversion
        else:
            min_salary_gbp = min_salary

        if period == "monthly":
            min_salary_gbp *= 12
        elif period == "weekly":
            min_salary_gbp *= 52
        elif period == "daily":
            min_salary_gbp *= 260  # 5 days * 52 weeks
        elif period == "hourly":
            min_salary_gbp *= 2080  # 40 hours * 52 weeks

        # Score based on how much above minimum
        ratio = min_salary_gbp / target_min if target_min > 0 else 1.0

        if ratio >= 1.2:
            return 1.0  # Great salary
        elif ratio >= 1.0:
            return 0.9  # Meets expectations
        elif ratio >= 0.8:
            return 0.6  # Close to expectations
        elif ratio >= 0.6:
            return 0.3  # Below expectations
        else:
            return 0.0  # Too low

    def _score_contract_type(self, job_data: Dict[str, Any]) -> float:
        """Score job based on contract type preferences.

        Args:
            job_data: Job data dictionary

        Returns:
            Score from 0.0 to 1.0
        """
        if not self.preferences.contract_types:
            return 1.0  # No preferences

        job_type = job_data.get("contract_type", "").lower()

        for pref_type in self.preferences.contract_types:
            pref_type_lower = pref_type.lower()
            if pref_type_lower in job_type:
                return 1.0

        return 0.0

    def _score_remote(self, job_data: Dict[str, Any]) -> float:
        """Score job based on remote policy (UK resident benefit).

        Args:
            job_data: Job data dictionary

        Returns:
            Score from 0.0 to 1.0
        """
        remote_policy = job_data.get("remote_policy", "none")
        remote_types = job_data.get("remote_types", [])

        if remote_policy == "remote" or len(remote_types) > 0:
            return 1.0  # Remote jobs are great for UK workers

        if remote_policy == "hybrid":
            return 0.7  # Hybrid is also good

        return 0.0

    def filter_jobs(
        self, jobs: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], float, Dict[str, Any]]]:
        """Filter and score a list of jobs.

        Args:
            jobs: List of job data dictionaries

        Returns:
            List of tuples (job_data, score, reasons) sorted by score descending
        """
        results = []

        for job in jobs:
            try:
                matches, score, reasons = self.match_job(job)
                if matches:
                    results.append((job, score, reasons))
            except Exception as e:
                if logger is not None:
                    logger.error(
                        "Error matching job",
                        extra={"job_id": job.get("id"), "error": str(e)},
                        exc_info=True,
                    )
                continue

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        if logger is not None:
            logger.info(
                "Job matching complete",
                extra={
                    "total_jobs": len(jobs),
                    "matched_jobs": len(results),
                    "match_rate": (
                        round(len(results) / len(jobs) * 100, 2) if jobs else 0
                    ),
                },
            )

        return results

    def get_match_explanation(
        self, job_data: Dict[str, Any], score: float, reasons: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of why job matched.

        Args:
            job_data: Job data dictionary
            score: Relevance score
            reasons: Reasons dictionary from match_job

        Returns:
            Human-readable explanation
        """
        lines = [f"Match Score: {score:.1f}/100"]

        if reasons["title_match"]:
            lines.append("✓ Title matches your preferences")

        if reasons["keyword_matches"] > 0:
            lines.append(f"✓ Matches {reasons['keyword_matches']} keywords")

        if reasons["location_match"]:
            location = job_data.get("location", {}).get("original", "")
            lines.append(f"✓ Location suitable: {location}")

        if reasons["salary_match"]:
            salary = job_data.get("salary", {})
            salary_str = salary.get("original", "")
            lines.append(f"✓ Salary meets expectations: {salary_str}")

        if reasons["contract_match"]:
            contract_type = job_data.get("contract_type", "")
            lines.append(f"✓ Contract type matches: {contract_type}")

        if reasons["remote_match"]:
            lines.append("✓ Remote work available")

        return " | ".join(lines)


def create_matcher(preferences: Optional[JobPreferences] = None) -> JobMatcher:
    """Factory function to create a job matcher.

    Args:
        preferences: JobPreferences or uses settings

    Returns:
        JobMatcher instance
    """
    return JobMatcher(preferences)
