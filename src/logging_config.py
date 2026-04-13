import logging


def setup_logging(log_file: str = "app.log", log_level: str = "INFO"):
    """Configure logging with file and console handlers.

    Args:
        log_file: Path to log file (default: app.log)
        log_level: Log level (default: INFO)
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
