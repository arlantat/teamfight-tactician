"""Persist official TFT news metadata so catalog refreshes cannot wipe it."""

import json
import sqlite3
from datetime import datetime

from tft.config import NEWS_SCHEMA_PATH
from tft.db.connection import insert_rows, run_schema
from tft.news.models import Heading, NewsArticleRow


def ensure_news_schema(conn: sqlite3.Connection) -> None:
    """Create news tables if needed without dropping catalog or match data."""
    run_schema(conn, NEWS_SCHEMA_PATH)


def read_articles(conn: sqlite3.Connection) -> list[NewsArticleRow]:
    """Return cached articles, newest first, with patch notes ahead of rundowns."""
    rows = conn.execute(
        """
        SELECT content_id, url, title, description, published_at, revision,
               listing_revision, kind, image_url, headings, fetched_at
        FROM news_articles
        ORDER BY published_at DESC,
                 CASE kind WHEN 'patch_notes' THEN 0 WHEN 'rundown' THEN 1 ELSE 2 END
        """
    ).fetchall()
    return [NewsArticleRow(**dict(row)) for row in rows]


def read_listing_meta(conn: sqlite3.Connection) -> dict[str, str] | None:
    """Return the last successful listing fetch, if any."""
    row = conn.execute(
        "SELECT listing_fetched_at, source_url FROM news_meta WHERE id = 1"
    ).fetchone()
    return dict(row) if row is not None else None


def replace_news(
    conn: sqlite3.Connection,
    articles: list[NewsArticleRow],
    *,
    fetched_at: datetime,
    source_url: str,
) -> None:
    """Replace the cached feed in the caller's transaction."""
    conn.execute("DELETE FROM news_articles")
    insert_rows(conn, "news_articles", articles, commit=False)
    insert_rows(
        conn,
        "news_meta",
        [
            {
                "id": 1,
                "listing_fetched_at": fetched_at.isoformat(),
                "source_url": source_url,
            }
        ],
        commit=False,
    )


def decode_headings(raw: str) -> list[Heading]:
    """Read a stored heading outline, treating corrupt JSON as empty."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    headings: list[Heading] = []
    for item in value:
        if (
            isinstance(item, dict)
            and isinstance(item.get("level"), int)
            and isinstance(item.get("text"), str)
            and item["text"]
        ):
            headings.append({"level": item["level"], "text": item["text"]})
    return headings
