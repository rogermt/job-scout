"""Tests for logging configuration (structured JSON logging)."""

import json
import logging
import sys
import tempfile
from pathlib import Path
from logging.handlers import RotatingFileHandler

sys.path.insert(0, "src")

from logging_config import JsonFormatter, setup_logging, get_logger


class TestJsonFormatter:
    """Test JSON formatter."""

    def test_format_returns_json_string(self) -> None:
        """Test formatter outputs valid JSON (or gracefully handles edge cases)."""
        from logging import makeLogRecord

        # Create minimal log record
        rec = makeLogRecord({"msg": "test", "name": "test", "levelname": "INFO"})
        formatter = JsonFormatter()

        # Should not raise and should return string
        result = formatter.format(rec)
        assert isinstance(result, str)
        # Validate it's valid JSON with expected structure
        payload = json.loads(result)
        assert payload["message"] == "test"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test"


class TestSetupLogging:
    """Test setup_logging with new structured handlers."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging creates console + file handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            setup_logging(log_path, "DEBUG")

            root = logging.getLogger()
            # Check handlers exist
            assert len(root.handlers) >= 2
            # RotatingFileHandler present
            has_file_handler = any(
                isinstance(h, RotatingFileHandler) for h in root.handlers
            )
            assert has_file_handler

    def test_setup_logging_custom_path(self) -> None:
        """Test setup_logging with custom log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "custom.log"
            setup_logging(log_path, "DEBUG")

            root = logging.getLogger()
            has_file = any(isinstance(h, RotatingFileHandler) for h in root.handlers)
            assert has_file


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self) -> None:
        """Test get_logger returns a logger."""
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"
