"""Read a consistent catalog snapshot from the static-data database."""

import json
import sqlite3
from pathlib import Path
from typing import Any, TypedDict


class Catalog(TypedDict):
    """Serializable catalog shared with the browser."""

    metadata: dict[str, Any]
    champions: list[dict[str, Any]]
    traits: list[dict[str, Any]]
    items: list[dict[str, Any]]
    augments: list[dict[str, Any]]


class CatalogUnavailableError(RuntimeError):
    """Raised when the catalog is missing, outdated, or incomplete."""


_JSON_COLUMNS = frozenset(
    {"traits", "stats", "ability_variables", "ability_detail", "effects", "composition"}
)
_COLLECTIONS = ("champions", "traits", "items", "augments")


def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert persisted JSON columns into native JSON values."""
    result = dict(row)
    for key in _JSON_COLUMNS.intersection(result):
        result[key] = json.loads(result[key])
    return result


def read_catalog(db_path: Path) -> Catalog:
    """Load all four collections in one read transaction without creating a DB.

    Args:
        db_path: Existing database populated by the static refresh command.

    Returns:
        Current set metadata and normalized catalog collections.

    Raises:
        CatalogUnavailableError: If the database is missing or needs refreshing.
    """
    if not db_path.is_file():
        raise CatalogUnavailableError("The set catalog has not been downloaded yet.")
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        metadata = conn.execute("SELECT * FROM metadata LIMIT 1").fetchone()
        if metadata is None:
            raise CatalogUnavailableError("The catalog has no set metadata.")
        collections = {
            table: [
                _decode_row(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY name")
            ]
            for table in _COLLECTIONS
        }
        if not collections["champions"] or not collections["traits"]:
            raise CatalogUnavailableError("The set catalog is incomplete.")
        return Catalog(metadata=dict(metadata), **collections)
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as exc:
        raise CatalogUnavailableError("The catalog needs a static data refresh.") from exc
    finally:
        if conn is not None:
            conn.close()
