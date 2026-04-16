"""Logging configuration (structured JSON logs).

ForgeSyte standard: no print, structured logging, production-friendly handlers.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include `extra={...}` fields (best-effort)
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }
        for k, v in record.__dict__.items():
            if k not in reserved and k not in payload:
                payload[k] = v

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging(
    log_file: str | Path = Path("logs/job_scout.log"), log_level: str = "INFO"
) -> None:
    """Configure root logging with console + rotating file handlers.

    Args:
        log_file: Path to log file (pathlib.Path or string)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    # Close and remove handlers properly to flush buffers and release file handles
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


__all__ = ["get_logger", "setup_logging"]
