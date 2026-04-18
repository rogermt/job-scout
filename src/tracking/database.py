"""Database management (SQLAlchemy SQLite)."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config_manager import DatabaseConfig
from src.tracking.models import Base


class DatabaseManager:
    """SQLAlchemy SQLite database manager."""

    def __init__(self, config: DatabaseConfig) -> None:
        db_path = Path(config.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine: Engine = create_engine(
            f"sqlite:///{db_path}", echo=bool(config.echo)
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False
        )

    def init_schema(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def init_database(db_config: DatabaseConfig) -> DatabaseManager:
    """Initialize database and create schema.

    Args:
        db_config: Database configuration

    Returns:
        DatabaseManager instance
    """
    manager = DatabaseManager(db_config)
    manager.init_schema()
    return manager


def get_session():
    """Get current database session (deprecated - use manager.session())."""
    return None


__all__ = ["DatabaseManager", "init_database", "get_session"]
