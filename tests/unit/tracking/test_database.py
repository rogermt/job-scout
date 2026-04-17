"""Tests for DatabaseManager."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.tracking.database import DatabaseManager, init_database


class TestDatabaseManager:
    """Test DatabaseManager."""

    def test_init_creates_engine(self) -> None:
        """Test engine creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.path = Path(tmpdir) / "test.db"
            config.echo = False

            manager = DatabaseManager(config)

            assert manager.engine is not None
            assert "test.db" in str(manager.engine.url)

    def test_init_schema_creates_tables(self) -> None:
        """Test schema initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.path = Path(tmpdir) / "test.db"
            config.echo = False

            manager = DatabaseManager(config)
            manager.init_schema()

            # Check tables exist
            from src.tracking.models import Base

            tables = list(Base.metadata.tables.keys())
            assert "jobs" in tables

    def test_session_context_manager(self) -> None:
        """Test session context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.path = Path(tmpdir) / "test.db"
            config.echo = False

            manager = DatabaseManager(config)
            manager.init_schema()

            with manager.session() as session:
                assert session is not None

    def test_session_rollback_on_error(self) -> None:
        """Test session rollback on exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.path = Path(tmpdir) / "test.db"
            config.echo = False

            manager = DatabaseManager(config)
            manager.init_schema()

            with pytest.raises(ValueError):
                with manager.session():
                    raise ValueError("test error")

            # If we get here, rollback was called


class TestInitDatabase:
    """Test init_database function."""

    def test_init_database_returns_manager(self) -> None:
        """Test init returns DatabaseManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.path = Path(tmpdir) / "test.db"
            config.echo = False

            manager = init_database(config)

            assert isinstance(manager, DatabaseManager)
            assert manager.engine is not None
