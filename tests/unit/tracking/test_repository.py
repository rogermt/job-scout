"""Tests for JobRepository."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from src.tracking.repository import JobRepository, _to_decimal


class TestToDecimal:
    """Test _to_decimal helper."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert _to_decimal(None) is None

    def test_decimal_passthrough(self) -> None:
        """Decimal input returns same."""
        assert _to_decimal(Decimal("50000")) == Decimal("50000")

    def test_valid_number_string(self) -> None:
        """Valid number string converts."""
        assert _to_decimal("50000") == Decimal("50000")

    def test_with_comma(self) -> None:
        """Number with commas converts."""
        assert _to_decimal("50,000") == Decimal("50000")

    def test_with_currency_symbols(self) -> None:
        """Currency symbols are stripped."""
        assert _to_decimal("£50,000") == Decimal("50000")
        assert _to_decimal("$50000") == Decimal("50000")
        assert _to_decimal("€50000") == Decimal("50000")

    def test_invalid_returns_none(self) -> None:
        """Invalid input returns None."""
        assert _to_decimal("not a number") is None


class TestJobRepository:
    """Test JobRepository."""

    def test_upsert_job_new(self) -> None:
        """Test inserting new job."""
        repo = JobRepository()
        session = MagicMock()
        session.scalar.return_value = None

        job_data = {
            "platform": "reed",
            "platform_id": "12345",
            "title": "Software Engineer",
            "company": "Tech Corp",
            "url": "https://example.com/job",
            "location": {"original": "London"},
            "salary": {
                "min": "50000",
                "max": "70000",
                "currency": "GBP",
                "period": "year",
            },
        }

        result = repo.upsert_job(session, job_data)

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.platform == "reed"
        assert result.platform_id == "12345"
        assert result.title == "Software Engineer"

    def test_upsert_job_update(self) -> None:
        """Test updating existing job."""
        repo = JobRepository()
        session = MagicMock()

        existing_job = MagicMock()
        session.scalar.return_value = existing_job

        job_data = {
            "platform": "reed",
            "platform_id": "12345",
            "title": "Senior Engineer",
            "company": "Tech Corp",
            "url": "https://example.com/job/updated",
            "location": {"original": "Manchester"},
            "salary": {},
        }

        result = repo.upsert_job(session, job_data)

        session.add.assert_not_called()
        assert result == existing_job
        assert result.title == "Senior Engineer"

    def test_upsert_job_validates_required_fields(self) -> None:
        """Test validation of platform and platform_id."""
        repo = JobRepository()
        session = MagicMock()

        with pytest.raises(ValueError, match="requires non-empty"):
            repo.upsert_job(session, {"platform": "", "platform_id": "12345"})

        with pytest.raises(ValueError, match="requires non-empty"):
            repo.upsert_job(session, {"platform": "reed", "platform_id": ""})

    def test_upsert_job_handles_integrity_error(self) -> None:
        """Test race condition handling."""
        repo = JobRepository()
        session = MagicMock()
        session.scalar.side_effect = [None, MagicMock()]

        from sqlalchemy.exc import IntegrityError

        session.flush.side_effect = IntegrityError(
            "duplicate", "duplicate", "duplicate"
        )

        job_data = {
            "platform": "reed",
            "platform_id": "12345",
            "title": "Engineer",
            "company": "Corp",
            "url": "https://example.com",
            "location": {},
            "salary": {},
        }

        result = repo.upsert_job(session, job_data)

        session.rollback.assert_called()
        assert result is not None
