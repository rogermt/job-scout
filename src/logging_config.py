import logging


def setup_logging(log_file: str = "logs/job_scout.log", log_level: str = "DEBUG"):
    """Configure logging with file and console handlers.

    Following PYTHON_STANDARDS.md recommendations.

    Args:
        log_file: Path to log file (default: logs/job_scout.log)
        log_level: Log level (default: DEBUG for debugging)
    """
    level = getattr(logging, log_level.upper(), logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured: level={log_level}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
