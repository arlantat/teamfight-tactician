#!/usr/bin/env python3
"""Harvest a bounded ranked TFT sample into the local database."""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tft.config import (
    DB_PATH,
    DEFAULT_SET_NUMBER,
    HARVESTER_MATCH_COUNT,
    HARVESTER_TOP_CHALLENGERS,
    HARVESTER_TOP_GRANDMASTERS,
    TFT_SERVERS,
)
from tft.exceptions import RiotApiError
from tft.riot.harvest import harvest_matches
from tft.riot.models import HarvestOptions
from tft.utils.logging import setup_logging


def main() -> int:
    """Parse an explicit sample scope and invoke the harvest service."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servers", nargs="+", type=str.upper, choices=TFT_SERVERS, default=["NA"])
    parser.add_argument("--challengers", type=int, default=HARVESTER_TOP_CHALLENGERS)
    parser.add_argument("--grandmasters", type=int, default=HARVESTER_TOP_GRANDMASTERS)
    parser.add_argument("--matches", type=int, default=HARVESTER_MATCH_COUNT, help="Matches per player")
    parser.add_argument("--set", dest="set_number", type=int, default=DEFAULT_SET_NUMBER)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    setup_logging()
    try:
        result = harvest_matches(HarvestOptions(
            servers=tuple(args.servers),
            challengers=args.challengers,
            grandmasters=args.grandmasters,
            matches_per_player=args.matches,
            set_number=args.set_number,
        ), args.db)
    except (RiotApiError, ValueError, sqlite3.Error, OSError) as exc:
        logging.getLogger(__name__).error("Harvest failed: %s", exc)
        return 1
    return 1 if result.request_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
