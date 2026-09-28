#!/usr/bin/env python3
"""Refresh the TFT catalog from live CommunityDragon or a saved JSON snapshot."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tft.config import DB_PATH, DEFAULT_SET_NUMBER
from tft.etl.static_data import refresh_static_data
from tft.utils.logging import setup_logging


def main() -> None:
    """Parse refresh options and invoke the atomic static data pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", type=int, default=DEFAULT_SET_NUMBER, dest="set_number")
    parser.add_argument("--source", type=Path, help="Use a saved CommunityDragon JSON snapshot")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite destination")
    parser.add_argument("--patch", help="Verified TFT patch label (not the CDragon build version)")
    parser.add_argument(
        "--with-abilities", action="store_true", help="Include reviewed MetaTFT ability values"
    )
    parser.add_argument("--abilities-source", type=Path, help="Use a saved MetaTFT ability export")
    args = parser.parse_args()
    setup_logging()
    refresh_static_data(
        args.db,
        args.set_number,
        args.source,
        args.patch,
        with_abilities=args.with_abilities,
        ability_source_path=args.abilities_source,
    )


if __name__ == "__main__":
    main()
