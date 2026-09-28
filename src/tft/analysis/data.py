"""Read static lookups and harvested match samples without changing the DB."""

import json
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from tft.analysis.models import AnalysisLookups, ChampInfo, ChampTraits
from tft.config import (
    ANALYSIS_LEGACY_QUERY_PATH,
    ANALYSIS_QUERY_PATH,
    DB_PATH,
    RIOT_RANKED_QUEUE_ID,
)

log = logging.getLogger(__name__)


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Open an existing database in read-only mode with named row access."""
    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}. Run the data update first.")
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_lookups(db_path: Path) -> AnalysisLookups:
    """Load static data used to interpret the harvested boards.

    Args:
        db_path: Existing SQLite database populated by the static-data update.

    Returns:
        Champion, trait, and item labels and champion trait memberships.
    """
    conn = _connect_readonly(db_path)
    try:
        champions: dict[str, ChampInfo] = {}
        champion_traits: ChampTraits = {}
        for row in conn.execute("SELECT api_name, name, cost, role, traits FROM champions"):
            key = row["api_name"].lower()
            champions[key] = (row["name"].strip(), row["cost"], row["role"])
            champion_traits[key] = set(json.loads(row["traits"]))
        traits = {
            row["api_name"]: row["name"]
            for row in conn.execute("SELECT api_name, name FROM traits")
        }
        items = {
            row["api_name"]: row["name"] for row in conn.execute("SELECT api_name, name FROM items")
        }
        return AnalysisLookups(champions, traits, champion_traits, items)
    finally:
        conn.close()


def _catalog_set_number(conn: sqlite3.Connection, tables: set[str]) -> int | None:
    """Read catalog provenance when present, tolerating older database shapes."""
    if "metadata" not in tables:
        return None
    columns = {row[1] for row in conn.execute("PRAGMA table_info(metadata)")}
    if "set_number" not in columns:
        return None
    row = conn.execute("SELECT set_number FROM metadata LIMIT 1").fetchone()
    return row[0] if row is not None else None


def load_data(
    db_path: Path | None = None,
    game_version: str | None = None,
) -> pd.DataFrame:
    """Read ranked boards compatible with the catalog, with an optional patch.

    Catalog metadata restricts matches to its verified set and ranked queue.
    Legacy databases without catalog provenance retain their prior scope.

    Args:
        db_path: Existing database path; defaults to the configured database.
        game_version: Exact stored Riot version string, or all stored versions.

    Returns:
        Participant rows with any known player rank and game version. An empty
        frame is returned when no compatible matches have been harvested yet.
    """
    path = db_path or DB_PATH
    conn = _connect_readonly(path)
    try:
        existing = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not {"match_participants", "players", "matches"}.issubset(existing):
            log.info("No harvested match tables are available yet.")
            return pd.DataFrame()
        query_path = ANALYSIS_LEGACY_QUERY_PATH
        params: dict[str, str | int | None] = {"game_version": game_version}
        set_number = _catalog_set_number(conn, existing)
        if set_number is not None:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
            if not {"set_number", "queue_id"}.issubset(columns):
                log.info("Historical matches lack verified set or queue provenance.")
                return pd.DataFrame()
            query_path = ANALYSIS_QUERY_PATH
            params.update(set_number=set_number, queue_id=RIOT_RANKED_QUEUE_ID)
        frame = pd.read_sql_query(
            query_path.read_text(encoding="utf-8"),
            conn,
            params=params,
        )
    finally:
        conn.close()
    log.info("Loaded %d participant rows from %s", len(frame), path.name)
    return frame
