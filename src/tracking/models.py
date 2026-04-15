"""SQLAlchemy models for job tracking."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class Job(Base):
    """Job model for tracking discovered jobs."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    platform: Mapped[str] = mapped_column(String(50), index=True)
    platform_id: Mapped[str] = mapped_column(String(100), index=True)

    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(500), default="")
    location_original: Mapped[str] = mapped_column(String(500), default="")
    url: Mapped[str] = mapped_column(Text, default="")

    salary_min: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    salary_max: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    salary_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


__all__ = ["Base", "Job"]
