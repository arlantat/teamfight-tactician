"""Shared pytest fixtures."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "tft" / "db" / "schema.sql"


@pytest.fixture()
def in_memory_db() -> Iterator[sqlite3.Connection]:
    """Yield an in-memory SQLite connection with the schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(ddl)
        yield conn
    finally:
        conn.close()
