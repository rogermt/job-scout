"""Structured logging configuration for Job Scout.

This module configures logging with structured JSON output, rotation, and proper
formatting following ForgeSyte standards (no print statements).
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .config_manager import get_settings


def _json_formatter(record: logging.LogRecord) -> str:
    """Format log record as structured JSON.
    
    Args:
        record: Log record
        
    Returns:
        JSON formatted string
    """
    log_obj = {
        "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
        "module": record.module,
        "function": record.funcName,
        "line": record.lineno,
        "process": record.process,
        "thread": record.thread,
    }
    
    # Add exception info if present
    if record.exc_info:
        log_obj["exception"] = logging.Formatter().formatException(record.exc_info)
    
    # Add extra fields
    if hasattr(record, "extra") and record.extra:
        try:
            # Ensure extra is JSON serializable
            extra_data = {}
            for k, v in record.extra.items():
                if isinstance(v, Path):
                    extra_data[k] = str(v)
                else:
                    extra_data[k] = v
            log_obj["extra"] = extra_data
        except Exception:
            # Fallback if extra contains non-serializable data
            log_obj["extra"] = "<non-serializable data>"
    
    return json.dumps(log_obj)


def _plain_formatter(record: logging.LogRecord) -> str:
    """Format log record as plain text with structured fields.
    
    Args:
        record: Log record
        
    Returns:
        Formatted string
    """
    base_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Add extra fields if present
    extra_str = ""
    if hasattr(record, "extra") and record.extra:
        extra_parts = []
        for k, v in record.extra.items():
            if isinstance(v, Path):
                extra_parts.append(f"{k}={v}")
            else:
                extra_parts.append(f"{k}={str(v)[:50]}")
        extra_str = " - " + " ".join(extra_parts) if extra_parts else ""
    
    return base_format + extra_str


def setup_logging(log_file: Path, log_level: str = "INFO", json_output: bool = False) -> None:
    """Set up structured logging configuration.
    
    Configures:
    - Console handler (stdout)
    - File handler with rotation
    - Structured formatting (JSON or plain)
    
    Args:
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON formatting instead of plain text
    """
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    
    # Set level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (always add)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # File handler with rotation (10MB files, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    
    # Formatter
    if json_output:
        formatter = logging.Formatter()
        formatter.format = lambda record: _json_formatter(record) + "\n"
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    # Set formatters
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set levels for common libraries
    # Reduce noise from HTTP libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_file": log_file,
            "log_level": log_level,
            "json_output": json_output,
            "max_file_size": "10MB",
            "backup_count": 5,
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger
    """
    return logging.getLogger(name)


def log_job_event(
    logger: logging.Logger,
    level: int,
    message: str,
    job_id: str,
    job_title: str,
    platform: str,
    **extra: Any
) -> None:
    """Log a job-related event with structured data.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        job_id: Job identifier
        job_title: Job title
        platform: Platform name
        **extra: Additional context data
    """
    extra_data = {
        "job_id": job_id,
        "job_title": job_title,
        "platform": platform,
        **extra,
    }
    logger.log(level, message, extra={"extra": extra_data})


def log_application_event(
    logger: logging.Logger,
    level: int,
    message: str,
    application_id: int,
    job_id: str,
    status: str,
    **extra: Any
) -> None:
    """Log an application-related event with structured data.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        application_id: Application ID
        job_id: Associated job ID
        status: Application status
        **extra: Additional context data
    """
    extra_data = {
        "application_id": application_id,
        "job_id": job_id,
        "status": status,
        **extra,
    }
    logger.log(level, message, extra={"extra": extra_data})


# Auto-configure logging when module is imported
def _auto_configure() -> None:
    """Auto-configure logging on import."""
    try:
        settings = get_settings()
        log_file = settings.output.log_file
        log_level = settings.log_level
        setup_logging(log_file, log_level)
    except Exception as e:
        # Fallback if config not available
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logger = logging.getLogger(__name__)
        logger.warning(
            "Failed to auto-configure logging",
            extra={"error": str(e), "fallback_level": "INFO"}
        )

# Run auto-configuration on import
_auto_configure()

__all__ = [
    "setup_logging",
    "get_logger",
    "log_job_event",
    "log_application_event",
]