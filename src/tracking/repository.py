"""Job repository for database operations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.tracking.models import Job


def _to_decimal(value: Any) -> Optional[Decimal]:
    """Convert value to Decimal safely."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        # Normalize: strip whitespace, remove commas and currency symbols
        normalized = (
            str(value)
            .strip()
            .replace(",", "")
            .replace("£", "")
            .replace("$", "")
            .replace("€", "")
        )
        return Decimal(normalized)
    except (InvalidOperation, ValueError, TypeError):
        return None


class JobRepository:
    """Repository for Job persistence."""

    def upsert_job(self, session: Session, job_data: dict[str, Any]) -> Job:
        """Insert or update job in database.

        Args:
            session: SQLAlchemy session
            job_data: Job data dictionary from scraper

        Returns:
            Job instance (persisted)
        """
        platform = str(job_data.get("platform") or "")
        platform_id = str(job_data.get("platform_id") or "")
        # Validate required fields
        if not platform or not platform_id:
            raise ValueError("job_data requires non-empty 'platform' and 'platform_id'")
        title = str(job_data.get("title") or "")
        company = str(job_data.get("company") or "")
        url = str(job_data.get("url") or "")
        location_original = str(job_data.get("location", {}).get("original", "") or "")

        salary = job_data.get("salary") or {}
        salary_min = _to_decimal(salary.get("min"))
        salary_max = _to_decimal(salary.get("max"))
        salary_currency = salary.get("currency")
        salary_period = salary.get("period")

        # Check if job already exists
        existing = session.scalar(
            select(Job).where(Job.platform == platform, Job.platform_id == platform_id)
        )

        if existing:
            # Update existing
            existing.title = title
            existing.company = company
            existing.url = url
            existing.location_original = location_original
            existing.salary_min = salary_min
            existing.salary_max = salary_max
            existing.salary_currency = salary_currency
            existing.salary_period = salary_period
            return existing

        # Create new
        job = Job(
            platform=platform,
            platform_id=platform_id,
            title=title,
            company=company,
            url=url,
            location_original=location_original,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_period=salary_period,
        )
        session.add(job)
        try:
            session.flush()
        except IntegrityError:
            # Another writer created the job first - rollback and fetch existing
            session.rollback()
            existing = session.scalar(
                select(Job).where(
                    Job.platform == platform, Job.platform_id == platform_id
                )
            )
            if existing:
                # Update the existing record that won the race
                existing.title = title
                existing.company = company
                existing.url = url
                existing.location_original = location_original
                existing.salary_min = salary_min
                existing.salary_max = salary_max
                existing.salary_currency = salary_currency
                existing.salary_period = salary_period
                return existing
            raise
        return job


__all__ = ["JobRepository"]
