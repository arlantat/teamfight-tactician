#!/usr/bin/env python3
"""Run the TFT Delta Engine — Challenger vs Grandmaster knowledge gap analysis.

Reads the local database and writes a Markdown report of composition
popularity and observed final-board outcomes across ranked samples.

Usage::

    .venv/bin/python scripts/delta_engine.py
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Ensure src/ is on sys.path for src-layout imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tft.analysis.delta_engine import run  # noqa: E402
from tft.utils.logging import setup_logging  # noqa: E402


def main() -> None:
    """Parse command-line options and run the local analysis pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Existing SQLite database")
    parser.add_argument("--output", type=Path, help="Markdown report destination")
    parser.add_argument("--game-version", help="Exact stored game version to compare")
    args = parser.parse_args()
    setup_logging()
    try:
        run(args.db, args.output, args.game_version)
    except (OSError, sqlite3.Error) as exc:
        parser.exit(status=1, message=f"Analysis failed: {exc}\n")


if __name__ == "__main__":
    main()
