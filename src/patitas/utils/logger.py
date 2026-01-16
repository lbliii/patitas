"""Minimal logging utilities for Patitas.

Provides a simple get_logger function that wraps the standard library logging.

Example:
    >>> from patitas.utils.logger import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Parsing document")
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name.

    Returns a standard library logger with the "patitas." prefix.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger instance

    Example:
        >>> logger = get_logger("mymodule")
        >>> logger.name
        'patitas.mymodule'
    """
    # Ensure patitas prefix for consistent namespacing
    if not (name == "patitas" or name.startswith("patitas.")):
        name = f"patitas.{name}"
    return logging.getLogger(name)
