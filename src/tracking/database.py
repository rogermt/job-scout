"""Database models and operations for Job Scout using SQLAlchemy 2.0.

This module provides database persistence for jobs, applications, and analytics
following ForgeSyte standards with type safety and proper error handling.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional, Type, TypeVar

from sqlalchemy import (
 Boolean,
 Column,
 DateTime,
 Float,
 ForeignKey,
 Integer,
 String,
 Table,
 Text,
 UniqueConstraint,
 create_engine,
 func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from ..config_manager import DatabaseConfig

logger = logging.getLogger(__name__)

Base = declarative_base()
T = TypeVar("T", bound="BaseModel")


class Job(Base):
    """Job listing scraped from a platform."""
    
    __tablename__ = "jobs"
    
    # Primary key: composite of platform and platform-specific ID
    id: str = Column(String, primary_key=True)  # Format: "platform:platform_id"
    platform: str = Column(String, nullable=False, index=True)
    title: str = Column(String, nullable=False)
    company: str = Column(String, nullable=False, index=True)
    
    # Location and remote information
    location: Optional[str] = Column(String, nullable=True)
    remote_policy: Optional[str] = Column(String, nullable=True)
    
    # Salary information (always stored as GBP equivalent for comparison)
    salary_min_gbp: Optional[float] = Column(Float, nullable=True)
    salary_max_gbp: Optional[float] = Column(Float, nullable=True)
    original_currency: Optional[str] = Column(String, nullable=True)
    
    # Job details
    description: Optional[str] = Column(Text, nullable=True)
    url: Optional[str] = Column(String, nullable=True)
    company_size: Optional[str] = Column(String, nullable=True)
    
    # Metadata
    posted_date: Optional[datetime] = Column(DateTime, nullable=True)
    scraped_date: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    match_score: Optional[float] = Column(Float, nullable=True)
    
    # Status
    hidden: bool = Column(Boolean, nullable=False, default=False)  # User has hidden this job
    applied: bool = Column(Boolean, nullable=False, default=False)  # Application submitted
    
    # Relationships
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation of Job."""
        return f"<Job(id='{self.id}', title='{self.title}', company='{self.company}')>"
    
    def format_salary(self) -> str:
        """Format salary as human-readable string with currency."""
        if not self.salary_min_gbp:
            return "Not specified"
        
        # Convert to appropriate currency for display
        if self.original_currency == "GBP":
            min_str = f"£{self.salary_min_gbp:,.0f}"
            max_str = f"£{self.salary_max_gbp:,.0f}" if self.salary_max_gbp else ""
        elif self.original_currency == "USD":
            # Approximate conversion for display
            min_usd = self.salary_min_gbp / 0.79  # Approximate GBP to USD
            max_usd = self.salary_max_gbp / 0.79 if self.salary_max_gbp else None
            min_str = f"${int(min_usd):,}"
            max_str = f"${int(max_usd):,}" if max_usd else ""
        else:
            min_str = f"{self.salary_min_gbp:,.0f}"
            max_str = f"{self.salary_max_gbp:,.0f}" if self.salary_max_gbp else ""
        
        if self.salary_max_gbp and self.salary_min_gbp != self.salary_max_gbp:
            return f"{min_str} - {max_str} {self.original_currency or 'GBP'}"
        return f"{min_str} {self.original_currency or 'GBP'}"


class Application(Base):
    """Application submitted for a job."""

    __tablename__ = "applications"
    __allow_unmapped__ = True  # Allow legacy annotations during migration
    
    id: int = Column(Integer, primary_key=True)
    job_id: str = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Application details
    status: str = Column(String, nullable=False, default="saved")  # saved, ready, applied, interview, rejected, offer, ghosted
    applied_date: Optional[datetime] = Column(DateTime, nullable=True)
    
    # Generated documents
    cv_path: Optional[str] = Column(String, nullable=True)
    cover_letter_path: Optional[str] = Column(String, nullable=True)
    
    # Tracking
    follow_up_date: Optional[datetime] = Column(DateTime, nullable=True)
    notes: Optional[str] = Column(Text, nullable=True)
    
    # Application metrics
    application_method: Optional[str] = Column(String, nullable=True)  # email, portal, etc.
    response_time_days: Optional[int] = Column(Integer, nullable=True)
    
    # Timestamps
    created_date: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_date: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job: Job = relationship("Job", back_populates="applications")
    
    def __repr__(self) -> str:
        """String representation of Application."""
        return f"<Application(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"


class PlatformStats(Base):
    """Statistics per platform for analytics."""
    
    __tablename__ = "platform_stats"
    
    id: int = Column(Integer, primary_key=True)
    platform: str = Column(String, nullable=False, index=True)
    
    # Daily statistics
    search_date: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    jobs_found: int = Column(Integer, nullable=False, default=0)
    jobs_applied: int = Column(Integer, nullable=False, default=0)
    
    # Cumulative statistics
    total_jobs_found: int = Column(Integer, nullable=False, default=0)
    total_applications: int = Column(Integer, nullable=False, default=0)
    
    # Unique constraint for platform + date
    __table_args__ = (
        # Assuming we want one record per platform per day
        UniqueConstraint('platform', 'search_date', name='uq_platform_date'),
    )
    
    def __repr__(self) -> str:
        """String representation of PlatformStats."""
        return f"<PlatformStats(platform='{self.platform}', date='{self.search_date.date()}')>"


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize database manager.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.engine = create_engine(
            f"sqlite:///{config.path}",
            echo=config.echo,
            connect_args={"check_same_thread": False},  # Allow multi-threading
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        logger.info("Database manager initialized", extra={"database_path": str(config.path)})
    
    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error("Failed to create database tables", extra={"error": str(e)})
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session (context manager).
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error("Database session error", extra={"error": str(e)})
            raise
        finally:
            session.close()
    
    @staticmethod
    def get_or_create(
        session: Session,
        model: Type[T],
        defaults: Optional[dict[str, Any]] = None,
        **kwargs: Any
    ) -> tuple[T, bool]:
        """Get an existing record or create a new one.
        
        Args:
            session: Database session
            model: Model class
            defaults: Default values for creation
            **kwargs: Lookup parameters
            
        Returns:
            Tuple of (instance, created)
        """
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        
        params = {k: v for k, v in kwargs.items()}
        if defaults:
            params.update(defaults)
        
        instance = model(**params)
        session.add(instance)
        session.flush()
        return instance, True
    
    def get_job(self, session: Session, job_id: str) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            session: Database session
            job_id: Job ID (format: "platform:platform_id")
            
        Returns:
            Job instance or None
        """
        return session.query(Job).filter(Job.id == job_id).first()
    
    def add_job(self, session: Session, **kwargs: Any) -> Job:
        """Add a new job to the database.
        
        Args:
            session: Database session
            **kwargs: Job attributes
            
        Returns:
            Created Job instance
        """
        job = Job(**kwargs)
        session.add(job)
        session.flush()
        logger.info("Job added to database", extra={"job_id": job.id, "title": job.title})
        return job
    
    def update_job(self, session: Session, job_id: str, **kwargs: Any) -> Optional[Job]:
        """Update an existing job.
        
        Args:
            session: Database session
            job_id: Job ID
            **kwargs: Attributes to update
            
        Returns:
            Updated Job instance or None if not found
        """
        job = self.get_job(session, job_id)
        if job:
            for key, value in kwargs.items():
                setattr(job, key, value)
            session.flush()
            logger.info("Job updated", extra={"job_id": job_id})
        return job
    
    def add_application(self, session: Session, job_id: str, **kwargs: Any) -> Application:
        """Add a new application.
        
        Args:
            session: Database session
            job_id: Job ID
            **kwargs: Application attributes
            
        Returns:
            Created Application instance
        """
        application = Application(job_id=job_id, **kwargs)
        session.add(application)
        session.flush()
        logger.info("Application created", extra={"job_id": job_id, "status": application.status})
        return application
    
    def get_application_stats(self, session: Session) -> dict[str, int]:
        """Get application statistics by status.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary of status -> count
        """
        from sqlalchemy import func
        
        results = (
            session.query(Application.status, func.count(Application.id))
            .group_by(Application.status)
            .all()
        )
        return dict(results)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_database(config: DatabaseConfig) -> DatabaseManager:
    """Initialize the global database manager.
    
    Args:
        config: Database configuration
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(config)
    _db_manager.create_tables()
    return _db_manager


def get_database() -> DatabaseManager:
    """Get the global database manager.
    
    Returns:
        DatabaseManager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


__all__ = [
    "Base",
    "Job",
    "Application",
    "PlatformStats",
    "DatabaseManager",
    "init_database",
    "get_database",
]