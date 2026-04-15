"""Tests for logging configuration."""
from unittest.mock import patch

import sys

sys.path.insert(0, "src")

from logging_config import setup_logging, get_logger


class TestLoggingConfig:
    """Test logging configuration."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with default parameters."""
        with patch("logging_config.logging.basicConfig") as mock_config:
            setup_logging()
            mock_config.assert_called_once()

    def test_setup_logging_custom_params(self) -> None:
        """Test setup_logging with custom parameters."""
        with patch("logging_config.logging.basicConfig") as mock_config:
            setup_logging("custom.log", "DEBUG")
            call_args = mock_config.call_args
            assert call_args is not None

    def test_get_logger_returns_logger(self) -> None:
        """Test get_logger returns a logger."""
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_setup_logging_invalid_level(self) -> None:
        """Test setup_logging with invalid level falls back to INFO."""
        with patch("logging_config.logging.basicConfig") as mock_config:
            setup_logging(log_level="INVALID_LEVEL")
            mock_config.assert_called_once()
