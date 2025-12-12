"""
Logging utilities for consistent structured logging.
"""

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with consistent configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs: Any):
    """
    Log with structured context.

    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        **kwargs: Additional structured fields
    """
    log_func = getattr(logger, level.lower())

    # Add structured fields as extra
    if kwargs:
        log_func(message, extra=kwargs)
    else:
        log_func(message)
