"""Central logging configuration for the application."""

from __future__ import annotations

import logging


def setup_logging() -> logging.Logger:
    """Configure and return application logger (English terminal output only)."""
    logger = logging.getLogger("documind")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger
