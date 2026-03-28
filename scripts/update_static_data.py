#!/usr/bin/env python3
"""Fetch the latest TFT set data from CommunityDragon and populate tft_data.db.

Usage:
    .venv/bin/python scripts/update_static_data.py
"""

import logging
from pathlib import Path

from tft.config import DB_PATH
from tft.db.connection import get_connection, insert_rows, run_schema
from tft.etl.cdragon import (
    derive_set_prefix,
    fetch_cdragon_data,
    find_active_set,
    parse_champions,
    parse_items,
    parse_traits,
)
from tft.utils.logging import setup_logging

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "tft" / "db" / "schema.sql"


def main() -> None:
    """Entry point — fetch, parse, store."""
    setup_logging()

    # ── Fetch ────────────────────────────────────────────────────────────
    data = fetch_cdragon_data()

    # ── Detect active set ────────────────────────────────────────────────
    active_set = find_active_set(data["setData"])
    set_number: int = active_set.get("number", 0)
    set_name: str = active_set.get("name", "Unknown")
    set_mutator: str = active_set.get("mutator", "Unknown")
    log.info(
        "Active set → Set %s (%s)  [mutator=%s]",
        set_number, set_name, set_mutator,
    )

    set_prefix = derive_set_prefix(set_mutator, set_number)

    # ── Parse ────────────────────────────────────────────────────────────
    champ_rows = parse_champions(active_set.get("champions", []))
    trait_rows = parse_traits(active_set.get("traits", []))
    item_rows = parse_items(data.get("items", []), set_prefix)

    # ── Store ────────────────────────────────────────────────────────────
    log.info("Writing to %s …", DB_PATH)
    conn = get_connection(DB_PATH)
    try:
        run_schema(conn, SCHEMA_PATH)
        n_champs = insert_rows(conn, "champions", champ_rows)
        n_traits = insert_rows(conn, "traits", trait_rows)
        n_items = insert_rows(conn, "items", item_rows)
    finally:
        conn.close()

    log.info("Inserted %d champions.", n_champs)
    log.info("Inserted %d traits.", n_traits)
    log.info("Inserted %d items.", n_items)
    log.info("Done ✓")


if __name__ == "__main__":
    main()
