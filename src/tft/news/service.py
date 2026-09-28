"""Refresh and serve official TFT news without copying article bodies."""

import json
import logging
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from tft.config import (
    DB_PATH,
    NEWS_CACHE_TTL_SECONDS,
    NEWS_FEED_LIMIT,
    NEWS_LISTING_URL,
    NEWS_PATCH_ARTICLE_LIMIT,
)
from tft.db.connection import get_connection
from tft.exceptions import NewsSourceError
from tft.news.models import Heading, ListingCard, NewsArticleRow, NewsPayload
from tft.news.parse import mid_patch_labels, parse_article, parse_listing, patch_label
from tft.news.source import fetch_html
from tft.news.store import (
    decode_headings,
    ensure_news_schema,
    read_articles,
    read_listing_meta,
    replace_news,
)

log = logging.getLogger(__name__)

FetchHtml = Callable[[str], str]


def load_news(
    db_path: Path = DB_PATH,
    *,
    now: datetime | None = None,
    fetch_html: FetchHtml = fetch_html,
    listing_url: str = NEWS_LISTING_URL,
) -> NewsPayload:
    """Return official TFT news, refreshing the local cache when it is stale.

    Args:
        db_path: SQLite file shared with the catalog; news tables are additive.
        now: Clock for cache expiry; defaults to the current UTC time.
        fetch_html: HTTP getter, replaced in tests.
        listing_url: Official game-updates listing.

    Returns:
        Listing teasers, heading outlines, and cache freshness.

    Raises:
        NewsSourceError: Riot's site could not be read and nothing is cached.
    """
    moment = now or datetime.now(UTC)
    conn = get_connection(db_path)
    try:
        ensure_news_schema(conn)
        cached = _payload(conn, stale=False)
        if cached is not None and _cache_is_fresh(conn, moment):
            return cached
        try:
            _refresh(conn, moment, fetch_html, listing_url)
        except NewsSourceError:
            if cached is not None:
                log.warning("Official TFT news refresh failed; serving cached notes")
                return _payload(conn, stale=True) or cached
            raise
        return _payload(conn, stale=False) or _empty_payload(moment, listing_url, stale=False)
    finally:
        conn.close()


def _refresh(
    conn: sqlite3.Connection,
    moment: datetime,
    fetch_html: FetchHtml,
    listing_url: str,
) -> None:
    """Download the listing and a small number of patch-note outlines."""
    origin = _origin(listing_url)
    cards = parse_listing(fetch_html(listing_url), origin)[:NEWS_FEED_LIMIT]
    existing = {row.content_id: row for row in read_articles(conn)}
    fetched = 0
    rows: list[NewsArticleRow] = []
    for card in cards:
        previous = existing.get(card["content_id"])
        headings, revision = _existing_outline(previous, card)
        if _should_fetch_article(card, headings, previous, fetched):
            try:
                article_rev, headings = parse_article(fetch_html(card["url"]))
                revision = article_rev or card["revision"]
                fetched += 1
            except NewsSourceError as exc:
                log.warning("Patch notes article unavailable: %s", exc)
        rows.append(
            NewsArticleRow(
                content_id=card["content_id"],
                url=card["url"],
                title=card["title"],
                description=card["description"],
                published_at=card["published_at"],
                revision=revision,
                listing_revision=card["revision"],
                kind=card["kind"],
                image_url=card["image_url"],
                headings=json.dumps(headings),
                fetched_at=moment.isoformat(),
            )
        )
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        replace_news(conn, rows, fetched_at=moment, source_url=listing_url)
    log.info("Cached %d official TFT news items (%d patch outlines)", len(rows), fetched)


def _should_fetch_article(
    card: ListingCard,
    headings: list[Heading],
    previous: NewsArticleRow | None,
    fetched: int,
) -> bool:
    """Fetch a patch-note page when the outline is missing or the CMS revision changed."""
    if card["kind"] != "patch_notes" or fetched >= NEWS_PATCH_ARTICLE_LIMIT:
        return False
    if not headings or previous is None:
        return True
    return previous.listing_revision != card["revision"]


def _existing_outline(
    previous: NewsArticleRow | None, card: ListingCard
) -> tuple[list[Heading], str]:
    """Reuse a stored outline until the matching article page is fetched."""
    if previous is None:
        return [], card["revision"]
    headings = decode_headings(previous.headings)
    revision = previous.revision if headings else card["revision"]
    return headings, revision


def _cache_is_fresh(conn: sqlite3.Connection, moment: datetime) -> bool:
    """True when the listing was fetched inside the configured TTL."""
    meta = read_listing_meta(conn)
    if meta is None:
        return False
    try:
        fetched_at = datetime.fromisoformat(meta["listing_fetched_at"])
    except ValueError:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    return moment - fetched_at < timedelta(seconds=NEWS_CACHE_TTL_SECONDS)


def _payload(conn: sqlite3.Connection, *, stale: bool) -> NewsPayload | None:
    """Serialize cached rows, or None when the cache is empty."""
    meta = read_listing_meta(conn)
    articles = read_articles(conn)
    if meta is None or not articles:
        return None
    return {
        "source_url": meta["source_url"],
        "fetched_at": meta["listing_fetched_at"],
        "stale": stale,
        "articles": [_public_article(row) for row in articles],
    }


def _public_article(row: NewsArticleRow) -> dict[str, object]:
    """Browser JSON: teasers and outlines, never the copyrighted body."""
    headings = [heading for heading in decode_headings(row.headings) if heading["text"]]
    return {
        "content_id": row.content_id,
        "url": row.url,
        "title": row.title,
        "description": row.description,
        "published_at": row.published_at,
        "revision": row.revision,
        "kind": row.kind,
        "image_url": row.image_url,
        "patch": patch_label(row.title),
        "headings": headings,
        "mid_patch": mid_patch_labels(headings),
    }


def _empty_payload(moment: datetime, listing_url: str, *, stale: bool) -> NewsPayload:
    """Fallback when a refresh stored no rows."""
    return {
        "source_url": listing_url,
        "fetched_at": moment.isoformat(),
        "stale": stale,
        "articles": [],
    }


def _origin(url: str) -> str:
    """Site origin used to resolve relative article paths."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise NewsSourceError("Official TFT news listing URL is invalid")
    return f"{parsed.scheme}://{parsed.netloc}"
