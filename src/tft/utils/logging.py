"""Centralised logging configuration."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a human-readable console format.

    Call this **once** at the top of every CLI entry point.

    Args:
        level: Logging threshold (default ``INFO``).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)-30s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
