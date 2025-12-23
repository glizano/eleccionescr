"""
Logging utilities for consistent structured logging with security safeguards.
"""

import logging
import re
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


def sanitize_for_log(value: str | None) -> str:
    """
    Sanitize a string value for safe logging by removing/escaping control characters.

    This prevents log injection attacks where malicious input could:
    - Inject fake log entries
    - Break log parsing
    - Exploit log processing tools

    Args:
        value: The string value to sanitize (can be None)

    Returns:
        Sanitized string safe for logging

    Example:
        >>> sanitize_for_log("normal text")
        'normal text'
        >>> sanitize_for_log("text\\nwith\\nnewlines")
        'text with newlines'
    """
    if value is None:
        return ""

    # Convert to string if not already
    value = str(value)

    # Replace newlines, carriage returns, and other control characters
    # This prevents log injection by removing characters that could break log format
    # Only removes C0 control characters (0x00-0x1F) and DEL (0x7F)
    value = re.sub(r"[\x00-\x1f\x7f]", " ", value)

    # Replace multiple spaces with single space
    value = re.sub(r"\s+", " ", value)

    # Strip leading/trailing whitespace
    return value.strip()


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
