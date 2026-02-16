"""Structured logging configuration for GreySignal."""

import logging
import os
import sys
from datetime import datetime, timezone

from rich.console import Console
from rich.logging import RichHandler


_console = Console(stderr=True)
_initialized = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Uses Rich for console output and supports LOG_LEVEL env var.
    All loggers share a common 'greysignal' namespace.
    """
    global _initialized

    logger = logging.getLogger(f"greysignal.{name}")

    if not _initialized:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        root_logger = logging.getLogger("greysignal")
        root_logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Rich handler for human-readable console output
        rich_handler = RichHandler(
            console=_console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(rich_handler)

        _initialized = True

    return logger


def get_console() -> Console:
    """Get the shared Rich console for direct output (e.g., progress bars)."""
    return _console
