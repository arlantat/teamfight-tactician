"""Official TFT news parsing, cache, and API behavior."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from tft.config import NEWS_LISTING_URL, STATIC_SCHEMA_PATH
from tft.db.connection import get_connection, run_schema
from tft.exceptions import NewsSourceError
from tft.news.parse import (
    classify_kind,
    heading_outline,
    mid_patch_labels,
    parse_article,
    parse_listing,
    patch_label,
    strip_html,
)
from tft.news.service import load_news
from tft.web.app import create_app

ORIGIN = "https://teamfighttactics.leagueoflegends.com"
LISTING_URL = f"{ORIGIN}/en-us/news/game-updates/"
PATCH_URL = f"{ORIGIN}/en-us/news/game-updates/teamfight-tactics-patch-18-2"
NOW = datetime(2026, 9, 17, 4, 0, tzinfo=UTC)


def _next_html(page: dict[str, object]) -> str:
    payload = json.dumps({"props": {"pageProps": {"page": page}}})
    return f'<html><script id="__NEXT_DATA__" type="application/json">{payload}</script></html>'


def _card(
    title: str,
    *,
    content_id: str,
    revision: str,
    url: str,
    published: str = "2026-09-09T18:00:00.000Z",
    description: str = "It’s the first main patch of Enchanted Wilds.",
    tags: list[str] | None = None,
    action_type: str = "weblink",
) -> dict[str, object]:
    return {
        "title": title,
        "publishedAt": published,
        "description": {"type": "html", "body": description},
        "analytics": {"contentId": content_id, "rev": revision},
        "action": {"type": action_type, "payload": {"url": url}},
        "tags": [{"machineName": name} for name in tags or []],
        "media": {"url": "https://cmsassets.example/cover.jpg"},
    }


def listing_html() -> str:
    return _next_html(
        {
            "blades": [
                {
                    "type": "articleCardGrid",
                    "items": [
                        _card(
                            "TFT Patch 18.2 Rundown",
                            content_id="rundown-18-2",
                            revision="rundown-rev",
                            url="https://www.youtube.com/watch?v=0WKctj8947s",
                            action_type="youtube_video",
                            description="Everything you need to know about patch 18.2 with Riot Truexy",
                        ),
                        _card(
                            "Teamfight Tactics patch 18.2",
                            content_id="patch-18-2",
                            revision="listing-rev",
                            url="/en-us/news/game-updates/teamfight-tactics-patch-18-2",
                            tags=["patch_notes"],
                        ),
                        _card(
                            "TFT Set 18 - Enchanted Wilds | Teamfight Tactics",
                            content_id="set-overview",
                            revision="set-rev",
                            url="/en-us/set-overview/tft-set-18-enchanted-wilds/",
                            published="2026-08-26T16:00:00.000Z",
                            description="Fight to flourish in a forest brimming with wild magic.",
                        ),
                    ],
                }
            ]
        }
    )


def article_html(revision: str = "article-rev") -> str:
    body = """
        <h2>&nbsp;</h2>
        <h2>MID-PATCH UPDATE</h2>
        <h4>SEPTEMBER 14</h4>
        <p>Camille and LeBlanc numbers changed. This paragraph must not be stored.</p>
        <h2>PATCH HIGHLIGHTS</h2>
        <h4>UNITS</h4>
        <h2>COSMETICS BEING CONVERTED NEXT PATCH (18.3)</h2>
    """
    return _next_html(
        {
            "analytics": {"contentId": "patch-18-2", "rev": revision},
            "blades": [{"type": "patchNotesRichText", "richText": {"body": body}}],
        }
    )


def test_listing_parses_official_next_data_without_article_bodies() -> None:
    """Riot's listing blade is enough to classify notes, rundowns, and other updates."""
    cards = parse_listing(listing_html(), ORIGIN)
    assert [card["kind"] for card in cards] == ["rundown", "patch_notes", "other"]
    patch = cards[1]
    assert patch["url"] == PATCH_URL
    assert patch["title"] == "Teamfight Tactics patch 18.2"
    assert "Camille" not in patch["description"]
    assert patch["revision"] == "listing-rev"
    assert cards[0]["url"].startswith("https://www.youtube.com/")


def test_article_keeps_headings_and_drops_body_copy() -> None:
    """Mid-patch detection uses official headings, not the copyrighted article."""
    revision, headings = parse_article(article_html())
    assert revision == "article-rev"
    texts = [heading["text"] for heading in headings]
    assert texts[0] == "MID-PATCH UPDATE"
    assert "&nbsp;" not in texts
    assert "Camille" not in texts
    assert mid_patch_labels(headings) == ["MID-PATCH UPDATE", "SEPTEMBER 14"]
    assert "UNITS" not in mid_patch_labels(headings)


def test_kind_and_patch_label_use_official_titles() -> None:
    """Video rundowns stay distinct from written patch notes."""
    assert classify_kind("TFT Patch 18.2 Rundown", []) == "rundown"
    assert classify_kind("Teamfight Tactics patch 18.2", ["patch_notes"]) == "patch_notes"
    assert classify_kind("Teamfight Tactics patch 18.2", []) == "patch_notes"
    assert patch_label("Teamfight Tactics patch 18.2") == "18.2"
    assert strip_html("<p>Buffs and <em>nerfs</em>.</p>") == "Buffs and nerfs."


def test_missing_payload_is_a_specific_error() -> None:
    """A changed Riot page must not be parsed as an empty successful listing."""
    with pytest.raises(NewsSourceError, match="structured payload"):
        parse_listing("<html></html>", ORIGIN)
    assert heading_outline("<p>No headings</p>") == []


def test_refresh_fetches_patch_outlines_and_reuses_them_until_revision_changes(
    tmp_path: Path,
) -> None:
    """Listing plus the latest written notes are fetched; unchanged revisions stay cached."""
    database = tmp_path / "tft.db"
    pages = {
        LISTING_URL: listing_html(),
        PATCH_URL: article_html("article-rev"),
    }
    calls: list[str] = []

    def fetch(url: str) -> str:
        calls.append(url)
        if url not in pages:
            raise NewsSourceError(f"unexpected {url}")
        return pages[url]

    first = load_news(database, now=NOW, fetch_html=fetch, listing_url=LISTING_URL)
    assert calls == [LISTING_URL, PATCH_URL]
    patch = next(item for item in first["articles"] if item["kind"] == "patch_notes")
    assert patch["revision"] == "article-rev"
    assert patch["mid_patch"] == ["MID-PATCH UPDATE", "SEPTEMBER 14"]
    assert patch["patch"] == "18.2"
    assert first["articles"][0]["kind"] == "patch_notes"
    assert all("Camille" not in json.dumps(item["headings"]) for item in first["articles"])

    calls.clear()
    cached = load_news(
        database,
        now=NOW + timedelta(minutes=5),
        fetch_html=fetch,
        listing_url=LISTING_URL,
    )
    assert calls == []
    assert cached["stale"] is False
    assert cached["articles"][0]["revision"] == "article-rev"

    calls.clear()
    listing_only = load_news(
        database,
        now=NOW + timedelta(minutes=31),
        fetch_html=fetch,
        listing_url=LISTING_URL,
    )
    assert calls == [LISTING_URL]
    assert listing_only["articles"][0]["revision"] == "article-rev"

    pages[LISTING_URL] = listing_html().replace("listing-rev", "listing-rev-2")
    pages[PATCH_URL] = article_html("article-rev-2")
    calls.clear()
    updated = load_news(
        database,
        now=NOW + timedelta(minutes=62),
        fetch_html=fetch,
        listing_url=LISTING_URL,
    )
    assert calls == [LISTING_URL, PATCH_URL]
    patch = next(item for item in updated["articles"] if item["kind"] == "patch_notes")
    assert patch["revision"] == "article-rev-2"


def test_failed_refresh_returns_cached_notes(tmp_path: Path) -> None:
    """A Riot outage must not hide notes that were already downloaded."""
    database = tmp_path / "tft.db"
    load_news(database, now=NOW, fetch_html=lambda url: listing_html() if url == LISTING_URL else article_html(), listing_url=LISTING_URL)
    stale = load_news(
        database,
        now=NOW + timedelta(minutes=31),
        fetch_html=lambda url: (_ for _ in ()).throw(NewsSourceError("down")),
        listing_url=LISTING_URL,
    )
    assert stale["stale"] is True
    assert stale["articles"][0]["kind"] == "patch_notes"


def test_news_tables_survive_a_catalog_refresh(tmp_path: Path) -> None:
    """Catalog DROP TABLE statements must not delete official notes."""
    database = tmp_path / "tft.db"
    load_news(database, now=NOW, fetch_html=lambda url: listing_html() if url == LISTING_URL else article_html(), listing_url=LISTING_URL)
    conn = get_connection(database)
    try:
        with conn:
            run_schema(conn, STATIC_SCHEMA_PATH)
        titles = [row["title"] for row in conn.execute("SELECT title FROM news_articles")]
    finally:
        conn.close()
    assert "Teamfight Tactics patch 18.2" in titles


def test_news_api_serves_cached_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The browser reads notes through the local API without a Riot developer key."""
    payload = {
        "source_url": NEWS_LISTING_URL,
        "fetched_at": NOW.isoformat(),
        "stale": False,
        "articles": [
            {
                "content_id": "patch-18-2",
                "url": PATCH_URL,
                "title": "Teamfight Tactics patch 18.2",
                "description": "Buffs.",
                "published_at": "2026-09-09T18:00:00.000Z",
                "revision": "article-rev",
                "kind": "patch_notes",
                "image_url": None,
                "patch": "18.2",
                "headings": [{"level": 2, "text": "MID-PATCH UPDATE"}],
                "mid_patch": ["MID-PATCH UPDATE"],
            }
        ],
    }
    monkeypatch.setattr("tft.web.app.load_news", lambda db_path: payload)
    with TestClient(create_app(tmp_path / "tft.db")) as client:
        response = client.get("/api/news")
    assert response.status_code == 200
    assert response.json()["articles"][0]["mid_patch"] == ["MID-PATCH UPDATE"]
    assert response.headers["cache-control"] == "no-store"


def test_news_api_is_unavailable_without_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A first-load source failure is an explicit empty state, not a 500."""
    monkeypatch.setattr(
        "tft.web.app.load_news",
        Mock(side_effect=NewsSourceError("down")),
    )
    with TestClient(create_app(tmp_path / "tft.db")) as client:
        response = client.get("/api/news")
    assert response.status_code == 503
    assert "patch notes" in response.json()["detail"].lower()
