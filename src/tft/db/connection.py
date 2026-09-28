"""SQLite connections and transaction-aware typed row insertion."""

import logging
import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, TypeAlias

from tft.config import SQLITE_BUSY_TIMEOUT_SECONDS
from tft.db.models import (
    AugmentRow,
    ChampionRow,
    ItemRow,
    MatchParticipantRow,
    MatchRow,
    PlayerRow,
    StaticDataMetadata,
    TraitRow,
)

log = logging.getLogger(__name__)

DatabaseRow: TypeAlias = (
    ChampionRow
    | TraitRow
    | ItemRow
    | AugmentRow
    | StaticDataMetadata
    | PlayerRow
    | MatchRow
    | MatchParticipantRow
    | Mapping[str, Any]
)
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite database using WAL and a bounded busy timeout.

    The caller owns the returned connection and must close it in finally.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        conn.close()
        raise
    log.debug("Opened SQLite connection: %s", db_path)
    return conn


def run_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """Apply SQL statements without committing the caller's transaction.

    Unlike sqlite3.executescript, executing complete statements individually
    preserves an open transaction, allowing destructive refreshes to roll back.
    """
    statement = ""
    for line in schema_path.read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""
    if statement.strip():
        conn.execute(statement)
    log.info("Schema applied from %s", schema_path.name)


def insert_rows(
    conn: sqlite3.Connection,
    table: str,
    rows: Sequence[DatabaseRow],
    *,
    commit: bool = True,
) -> int:
    """Insert typed or mapping rows, optionally leaving commit to the caller.

    Args:
        conn: Open SQLite connection.
        table: Valid SQL table identifier.
        rows: Dataclasses or mappings with consistent column names.
        commit: Retain standalone insertion behavior; use False in transactions.

    Returns:
        Number of rows inserted.
    """
    if not _IDENTIFIER.fullmatch(table):
        raise ValueError(f"Invalid table identifier: {table!r}")
    if not rows:
        return 0
    records = [asdict(row) if is_dataclass(row) else dict(row) for row in rows]
    columns = list(records[0])
    if not columns or any(not _IDENTIFIER.fullmatch(column) for column in columns):
        raise ValueError("Rows must have valid SQL column identifiers")
    if any(set(record) != set(columns) for record in records):
        raise ValueError("All rows must have the same columns")
    placeholders = ", ".join("?" for _ in columns)
    names = ", ".join(f'"{column}"' for column in columns)
    sql = f'INSERT OR REPLACE INTO "{table}" ({names}) VALUES ({placeholders})'
    conn.executemany(sql, [tuple(record[column] for column in columns) for record in records])
    if commit:
        conn.commit()
    return len(records)
