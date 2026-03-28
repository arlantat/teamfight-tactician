"""SQLite connection helpers."""

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open (or create) a SQLite database and return a connection.

    Args:
        db_path: Filesystem path to the ``.db`` file.

    Returns:
        An open ``sqlite3.Connection`` with WAL journal mode enabled.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    log.debug("Opened SQLite connection → %s", db_path)
    return conn


def run_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """Execute a ``.sql`` DDL file against *conn*.

    Args:
        conn: An open SQLite connection.
        schema_path: Path to a SQL file containing DDL statements.
    """
    ddl = schema_path.read_text(encoding="utf-8")
    conn.executescript(ddl)
    log.info("Schema applied from %s", schema_path.name)


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    """Bulk-insert a list of dicts into *table* with INSERT OR REPLACE.

    Args:
        conn: An open SQLite connection.
        table: Target table name.
        rows: List of dicts whose keys match the table columns.

    Returns:
        Number of rows inserted.
    """
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
    conn.commit()
    return len(rows)
