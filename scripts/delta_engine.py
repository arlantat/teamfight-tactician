#!/usr/bin/env python3
"""Run the TFT Delta Engine — Challenger vs Grandmaster knowledge gap analysis.

Reads ``tft_data.db`` (must exist with harvested match data) and prints
formatted markdown tables showing placement deltas, economy deltas, and
Challenger-favoured item builds.

Usage::

    .venv/bin/python scripts/delta_engine.py
"""

import sys
from pathlib import Path

# Ensure src/ is on sys.path for src-layout imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tft.analysis.delta_engine import run  # noqa: E402
from tft.utils.logging import setup_logging  # noqa: E402


def main() -> None:
    """Entry point — run the delta engine analysis."""
    setup_logging()
    run()


if __name__ == "__main__":
    main()
