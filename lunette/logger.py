"""Logging configuration for Lunette SDK."""

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def get_lunette_logger(name: str) -> logging.Logger:
    """Get a logger instance configured for Lunette.

    Logs are written to ~/.lunette/lunette.log with rotation.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Create ~/.lunette directory if it doesn't exist
        lunette_dir = Path.home() / ".lunette"
        lunette_dir.mkdir(exist_ok=True)

        # Log file path
        log_file = lunette_dir / "lunette.log"

        # Create rotating file handler (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(file_handler)

        # Prevent propagation to root logger
        logger.propagate = False

    return logger
