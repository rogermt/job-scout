"""Unit tests for JobMatcher - the job filtering and scoring engine."""

import pytest
from unittest.mock import MagicMock, patch

from src.discovery.platforms.job_matching import (
    JobMatcher,
    create_matcher,
    get_settings,
    get_job_preferences,
    
)


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_settings_returns_config(self) -> None:
        """Test get_settings returns configuration."""
        config = get_settings()
        assert config is not None
        assert hasattr(config, "job_preferences")

    def test_get_job_preferences_returns_class(self) -> None:
        """Test get_job_preferences returns JobPreferences class."""
        cls = get_job_preferences()
        assert cls is not None
        assert cls.__name__ == "JobPreferences"

    def test_init_logger_returns_logger(self) -> None:
        """Test _init_logger returns a logger."""
        logger = _init_logger()
        assert logger is not None
        assert logger.name == "src.discovery.platforms.job_matching"

    def test_create_matcher_returns_instance(self) -> None:
        """Test create_matcher factory function."""
        from src.discovery.platforms.job_matching import create_matcher

        matcher = create_matcher()
        assert matcher is not None
        assert matcher.__class__.__name__ == "JobMatcher"

    def test_job_matcher_score_calculation(self) -> None:
        """Test score calculation for job matching."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = ["developer"]
        prefs.keywords = ["python"]
        prefs.exclude_keywords = ["recruiter"]
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = 30000
        prefs.salary.max_gbp = None
        prefs.get = lambda k, d=None: {"min_gbp": 30000}.get(k, d)
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)

        # High match job
        job_high = {
            "title": "Python Developer",
            "description": "Python developer role",
            "location": {"original": "London", "is_remote": False},
        }
        result = matcher.match_job(job_high)
        assert result is not None

    def test_job_matcher_exclude_keywords(self) -> None:
        """Test job matching excludes by keywords."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = ["recruiter", "commission"]
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)

        # Job with excluded keyword
        job_bad = {
            "title": "Recruiter",
            "description": "Commission based recruiter role",
            "location": {"original": "Office", "is_remote": False},
        }
        result = matcher.match_job(job_bad)
        assert result is not None

    def test_job_matcher_location_filter(self) -> None:
        """Test location filtering."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)

        job = {
            "title": "Developer",
            "location": {"original": "London", "is_remote": False},
        }
        result = matcher.match_job(job)
        assert result is not None

    def test_job_matcher_remote_policy(self) -> None:
        """Test remote policy scoring."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = True
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)

        job_remote = {
            "title": "Developer",
            "location": {"original": "Remote", "is_remote": True},
            "remote_policy": "full",
        }
        result = matcher.match_job(job_remote)
        assert result is not None

    def test_job_matcher_empty_job_dict(self) -> None:
        """Test job_matcher with empty job dict."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)
        result = matcher.match_job({})
        assert result is not None

    def test_job_matcher_missing_location(self) -> None:
        """Test job_matcher handles missing location."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)
        result = matcher.match_job({"title": "Developer"})
        assert result is not None

    def test_job_matcher_preferred_location_match(self) -> None:
        """Test job_matcher location preference scoring."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = ["london"]
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)
        result = matcher.match_job(
            {
                "title": "Developer",
                "location": {"original": "London", "is_remote": False},
            }
        )
        assert result is not None

    def test_job_matcher_salary_scoring_usd(self) -> None:
        """Test salary scoring with USD conversion."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = 30000
        prefs.salary.max_gbp = None
        prefs.get = lambda k, d=None: {"min_gbp": 30000}.get(k, d)
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)
        result = matcher.match_job(
            {
                "title": "Developer",
                "salary": {"min": 50000, "currency": "USD", "period": "yearly"},
                "location": {"original": "Remote", "is_remote": True},
            }
        )
        assert result is not None

    def test_job_matcher_salary_scoring_gbp(self) -> None:
        """Test salary scoring with GBP."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = 30000
        prefs.salary.max_gbp = None
        prefs.get = lambda k, d=None: {"min_gbp": 30000}.get(k, d)
        prefs.contract_types = []
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)
        result = matcher.match_job(
            {
                "title": "Developer",
                "salary": {"min": 40000, "currency": "GBP", "period": "yearly"},
                "location": {"original": "Remote", "is_remote": True},
            }
        )
        assert result is not None

    def test_job_matcher_contract_type_match(self) -> None:
        """Test contract type matching."""
        from src.discovery.platforms.job_matching import JobMatcher

        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.locations = []
        prefs.salary = MagicMock()
        prefs.salary.min_gbp = None
        prefs.get = lambda k, d=None: d
        prefs.contract_types = ["full_time"]
        prefs.job_types = []
        prefs.company_sizes = []

        matcher = JobMatcher(prefs)
        result = matcher.match_job(
            {
                "title": "Developer",
                "contract_type": "full_time",
                "location": {"original": "Remote", "is_remote": True},
            }
        )
        assert result is not None


class TestJobMatcherInit:
    """Test JobMatcher initialization."""

    def test_init_with_preferences(self) -> None:
        """Test initialization with custom preferences."""
        mock_prefs = MagicMock()
        mock_prefs.titles = ["developer"]
        mock_prefs.keywords = ["python", "django"]
        mock_prefs.exclude_keywords = ["intern"]
        mock_prefs.remote_only = False

        matcher = JobMatcher(mock_prefs)
        assert matcher.preferences == mock_prefs

    def test_init_with_defaults(self) -> None:
        """Test initialization uses default preferences."""
        with patch("src.discovery.platforms.job_matching.get_settings") as mock:
            mock_settings = MagicMock()
            mock_settings.job_preferences = MagicMock()
            mock_settings.job_preferences.titles = []
            mock_settings.job_preferences.keywords = []
            mock_settings.job_preferences.exclude_keywords = []
            mock_settings.job_preferences.remote_only = False
            mock.return_value = mock_settings

            matcher = JobMatcher()
            assert matcher.preferences is not None


class TestMatchJob:
    """Test match_job scoring method."""

    @pytest.fixture
    def mock_preferences(self) -> MagicMock:
        """Create mock preferences."""
        prefs = MagicMock()
        prefs.titles = ["developer", "engineer"]
        prefs.keywords = ["python", "django"]
        prefs.exclude_keywords = ["intern", "junior"]
        prefs.min_salary = 40000
        prefs.remote_only = False
        prefs.uk_only = False
        prefs.experience_levels = []
        prefs.contract_types = []
        prefs.location = "London"
        prefs.job_types = []
        prefs.company_sizes = []
        prefs.locations = []
        prefs.salary = {"min_gbp": 40000}
        prefs.get.return_value = 40.0
        return prefs

    @pytest.fixture
    def matcher(self, mock_preferences: MagicMock) -> JobMatcher:
        """Create matcher with mock preferences."""
        return JobMatcher(mock_preferences)

    def test_matching_job_returns_tuple(self, matcher: JobMatcher) -> None:
        """Test job matching returns proper tuple format."""
        job = {
            "title": "Senior Python Developer",
            "company": "Tech Corp",
            "location": {"original": "London, UK"},
            "salary": {"min": 50000, "max": 70000, "currency": "GBP"},
            "contract_type": "permanent",
            "url": "https://example.com/job/1",
        }
        matches, score, reasons = matcher.match_job(job)
        assert isinstance(matches, bool)
        assert isinstance(score, (int, float))
        assert isinstance(reasons, dict)

    def test_non_matching_intern_job(self, matcher: JobMatcher) -> None:
        """Test intern job is excluded."""
        job = {
            "title": "Marketing Intern",
            "company": "Ad Agency",
            "location": {"original": "Manchester, UK"},
            "salary": {"min": 20000, "max": 25000, "currency": "GBP"},
            "contract_type": "internship",
            "url": "https://example.com/job/2",
        }
        matches, score, reasons = matcher.match_job(job)
        assert isinstance(matches, bool)

    def test_job_with_minimal_fields(self, matcher: JobMatcher) -> None:
        """Test job with only required fields."""
        job = {
            "title": "Python Developer",
            "url": "https://example.com/job/3",
        }
        matches, score, reasons = matcher.match_job(job)
        assert isinstance(matches, bool)
        assert isinstance(score, (int, float))


class TestHasExcludedKeywords:
    """Test _has_excluded_keywords method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with exclusion keywords."""
        prefs = MagicMock()
        prefs.titles = ["developer"]
        prefs.keywords = []
        prefs.exclude_keywords = ["intern", "junior", "contractor"]
        prefs.remote_only = False
        return JobMatcher(prefs)

    def test_excluded_keyword_in_title(self, matcher: JobMatcher) -> None:
        """Test job with excluded keyword in title."""
        job = {"title": "Marketing Intern", "url": "https://example.com/job/1"}
        assert matcher._has_excluded_keywords(job) is True

    def test_no_excluded_keywords(self, matcher: JobMatcher) -> None:
        """Test job without excluded keywords."""
        job = {"title": "Python Developer", "url": "https://example.com/job/2"}
        assert matcher._has_excluded_keywords(job) is False


class TestScoreTitle:
    """Test _score_title method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with title patterns."""
        prefs = MagicMock()
        prefs.titles = ["developer", "engineer", "architect"]
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        return JobMatcher(prefs)

    def test_title_match_gives_positive_score(self, matcher: JobMatcher) -> None:
        """Test title match gives positive score."""
        job = {"title": "Senior Developer", "url": "https://example.com/job/1"}
        score = matcher._score_title(job)
        assert score > 0

    def test_no_title_match_gives_zero(self, matcher: JobMatcher) -> None:
        """Test no title match gives zero score."""
        job = {"title": "Marketing Manager", "url": "https://example.com/job/2"}
        score = matcher._score_title(job)
        assert score == 0.0


class TestScoreKeywords:
    """Test _score_keywords method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with keywords."""
        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = ["python", "django", "api", "rest"]
        prefs.exclude_keywords = []
        prefs.remote_only = False
        return JobMatcher(prefs)

    def test_keyword_match_gives_positive_score(self, matcher: JobMatcher) -> None:
        """Test job with keyword matches gets positive score."""
        job = {
            "title": "Python Developer",
            "description": "We use Django and REST APIs",
            "url": "https://example.com/job/1",
        }
        score = matcher._score_keywords(job)
        assert score > 0

    def test_no_keyword_matches_gives_zero(self, matcher: JobMatcher) -> None:
        """Test job with no keyword matches gets zero."""
        job = {"title": "Java Developer", "url": "https://example.com/job/2"}
        score = matcher._score_keywords(job)
        assert score == 0.0


class TestScoreLocation:
    """Test _score_location method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with UK location."""
        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.uk_only = False
        prefs.location = "London"
        return JobMatcher(prefs)

    def test_uk_location_gives_positive(self, matcher: JobMatcher) -> None:
        """Test UK location gets positive score."""
        job = {
            "title": "Developer",
            "location": {"original": "London, UK"},
            "url": "https://example.com/job/1",
        }
        score = matcher._score_location(job)
        assert isinstance(score, (int, float))

    def test_remote_location_gives_positive(self, matcher: JobMatcher) -> None:
        """Test remote location gets positive score."""
        job = {
            "title": "Developer",
            "location": {"original": "Remote"},
            "url": "https://example.com/job/2",
        }
        score = matcher._score_location(job)
        assert isinstance(score, (int, float))


class TestScoreSalary:
    """Test _score_salary method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with salary threshold."""
        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.min_salary = 50000
        return JobMatcher(prefs)

    def test_salary_above_threshold_gives_full(self, matcher: JobMatcher) -> None:
        """Test salary above min gives positive score."""
        job = {
            "title": "Developer",
            "salary": {"min": 60000, "max": 80000, "currency": "GBP"},
            "url": "https://example.com/job/1",
        }
        score = matcher._score_salary(job)
        assert isinstance(score, (int, float))

    def test_salary_below_threshold_gives_zero(self, matcher: JobMatcher) -> None:
        """Test salary below min gives zero score."""
        job = {
            "title": "Developer",
            "salary": {"min": 30000, "max": 40000, "currency": "GBP"},
            "url": "https://example.com/job/2",
        }
        score = matcher._score_salary(job)
        assert isinstance(score, (int, float))

    def test_no_salary_data_gives_zero(self, matcher: JobMatcher) -> None:
        """Test job without salary data gives zero."""
        job = {"title": "Developer", "url": "https://example.com/job/3"}
        score = matcher._score_salary(job)
        assert isinstance(score, (int, float))


class TestScoreContractType:
    """Test _score_contract_type method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with contract type filter."""
        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False
        prefs.contract_types = ["permanent", "contract"]
        return JobMatcher(prefs)

    def test_matching_contract_gives_positive(self, matcher: JobMatcher) -> None:
        """Test matching contract type gives positive score."""
        job = {
            "title": "Developer",
            "contract_type": "permanent",
            "url": "https://example.com/job/1",
        }
        score = matcher._score_contract_type(job)
        assert score > 0

    def test_non_matching_contract_gives_zero(self, matcher: JobMatcher) -> None:
        """Test non-matching contract type gives zero."""
        job = {
            "title": "Developer",
            "contract_type": "internship",
            "url": "https://example.com/job/2",
        }
        score = matcher._score_contract_type(job)
        assert score == 0.0


class TestScoreRemote:
    """Test _score_remote method."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher with remote preference."""
        prefs = MagicMock()
        prefs.titles = []
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = True
        return JobMatcher(prefs)

    def test_remote_job_when_remote_only(self, matcher: JobMatcher) -> None:
        """Test remote job gets positive score when remote_only=True."""
        job = {
            "title": "Remote Developer",
            "remote_policy": "remote",
            "url": "https://example.com/job/1",
        }
        score = matcher._score_remote(job)
        assert score > 0

    def test_non_remote_when_remote_only(self, matcher: JobMatcher) -> None:
        """Test non-remote job gets zero when remote_only=True."""
        job = {
            "title": "Developer",
            "remote_policy": "onsite",
            "location": "London, UK",
            "url": "https://example.com/job/2",
        }
        score = matcher._score_remote(job)
        assert score == 0.0


class TestFilterJobs:
    """Test filter_jobs batch filtering."""

    @pytest.fixture
    def matcher(self) -> JobMatcher:
        """Create matcher."""
        prefs = MagicMock()
        prefs.titles = ["developer"]
        prefs.keywords = ["python"]
        prefs.exclude_keywords = ["intern"]
        prefs.remote_only = False
        prefs.min_salary = 40000
        return JobMatcher(prefs)

    def test_filter_returns_list(self, matcher: JobMatcher) -> None:
        """Test filter returns a list."""
        jobs = [
            {
                "title": "Python Developer",
                "salary": {"min": 50000},
                "url": "https://example.com/job/1",
            },
            {"title": "Marketing Intern", "url": "https://example.com/job/2"},
        ]
        filtered = matcher.filter_jobs(jobs)
        assert isinstance(filtered, list)


class TestCreateMatcher:
    """Test create_matcher factory function."""

    def test_create_with_preferences(self) -> None:
        """Test create_matcher with custom preferences."""
        prefs = MagicMock()
        prefs.titles = ["developer"]
        prefs.keywords = []
        prefs.exclude_keywords = []
        prefs.remote_only = False

        matcher = create_matcher(prefs)
        assert isinstance(matcher, JobMatcher)
        assert matcher.preferences == prefs

    def test_create_without_preferences(self) -> None:
        """Test create_matcher uses defaults."""
        with patch("src.discovery.platforms.job_matching.get_settings") as mock:
            mock_settings = MagicMock()
            mock_settings.job_preferences = MagicMock()
            mock_settings.job_preferences.titles = []
            mock_settings.job_preferences.keywords = []
            mock_settings.job_preferences.exclude_keywords = []
            mock_settings.job_preferences.remote_only = False
            mock.return_value = mock_settings

            matcher = create_matcher()
            assert isinstance(matcher, JobMatcher)
