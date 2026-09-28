"""Integration tests for the read-only local catalog API."""

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from tft.web.app import create_app


def test_frontend_assets_revalidate_after_updates(tmp_path: Path) -> None:
    """Reloading must not reuse stale local JavaScript or stylesheets."""
    with TestClient(create_app(tmp_path / "missing.db")) as client:
        for path in ("/", "/static/app.js", "/static/builder.css"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-cache"


def test_health_does_not_create_database(tmp_path: Path) -> None:
    """The server remains reachable before the first static refresh."""
    database = tmp_path / "missing.db"
    with TestClient(create_app(database)) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        response = client.get("/api/catalog")
    assert response.status_code == 503
    assert "update_static_data.py" in response.json()["detail"]
    assert not database.exists()


def test_legacy_database_has_actionable_error(tmp_path: Path) -> None:
    """Pre-UI databases require a refresh instead of returning partial data."""
    database = tmp_path / "legacy.db"
    conn = sqlite3.connect(database)
    try:
        conn.execute("CREATE TABLE champions (name TEXT)")
        conn.commit()
    finally:
        conn.close()
    with TestClient(create_app(database)) as client:
        response = client.get("/api/catalog")
    assert response.status_code == 503
    assert "refresh" in response.json()["detail"]


def test_catalog_returns_decoded_snapshot(tmp_path: Path) -> None:
    """Browser collections decode nested JSON and retain set provenance."""
    database = tmp_path / "catalog.db"
    conn = sqlite3.connect(database)
    try:
        conn.execute("CREATE TABLE metadata (set_number INTEGER, set_name TEXT, patch TEXT)")
        conn.execute("INSERT INTO metadata VALUES (18, 'Enchanted Wilds', '18.2')")
        conn.execute("CREATE TABLE champions (name TEXT, traits TEXT, stats TEXT)")
        conn.execute(
            "INSERT INTO champions VALUES (?, ?, ?)",
            (
                "Ahri",
                json.dumps(["Blossom", "Spellweaver"]),
                json.dumps({"hp": 800}),
            ),
        )
        conn.execute("CREATE TABLE traits (name TEXT, effects TEXT)")
        conn.execute(
            "INSERT INTO traits VALUES (?, ?)",
            (
                "Blossom",
                json.dumps([{"minUnits": 2}]),
            ),
        )
        conn.execute("CREATE TABLE items (name TEXT, composition TEXT, effects TEXT)")
        conn.execute(
            "INSERT INTO items VALUES (?, ?, ?)",
            (
                "Example item",
                json.dumps(["component_a", "component_b"]),
                json.dumps({"AD": 10}),
            ),
        )
        conn.execute("CREATE TABLE augments (name TEXT, effects TEXT)")
        conn.commit()
    finally:
        conn.close()
    with TestClient(create_app(database)) as client:
        response = client.get("/api/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["set_number"] == 18
    assert payload["champions"][0]["traits"] == ["Blossom", "Spellweaver"]
    assert payload["champions"][0]["stats"]["hp"] == 800
    assert payload["items"][0]["composition"] == ["component_a", "component_b"]
    assert payload["traits"][0]["effects"][0]["minUnits"] == 2
    assert payload["augments"] == []
    assert response.headers["cache-control"] == "no-store"


def test_api_rejects_mutation(tmp_path: Path) -> None:
    """The companion never exposes an unauthenticated catalog write route."""
    with TestClient(create_app(tmp_path / "missing.db")) as client:
        assert client.post("/api/catalog", json={"set_number": 99}).status_code == 405


def test_analysis_empty_state_requires_no_riot_key(tmp_path: Path) -> None:
    """An existing static-only database returns empty, truthful analytics."""
    database = tmp_path / "static-only.db"
    conn = sqlite3.connect(database)
    conn.close()
    with TestClient(create_app(database)) as client:
        response = client.get("/api/analysis")
    assert response.status_code == 200
    assert response.json() == {
        "versions": [],
        "sample_count": 0,
        "population": [],
        "behavioral": [],
        "highrolls": [],
    }


def test_corrupt_json_returns_refresh_error(tmp_path: Path) -> None:
    """Malformed persisted JSON yields a controlled response instead of a 500."""
    database = tmp_path / "broken.db"
    conn = sqlite3.connect(database)
    try:
        conn.execute("CREATE TABLE metadata (set_number INTEGER)")
        conn.execute("INSERT INTO metadata VALUES (18)")
        conn.execute("CREATE TABLE champions (name TEXT, traits TEXT)")
        conn.execute("INSERT INTO champions VALUES ('Ahri', 'bad json')")
        conn.commit()
    finally:
        conn.close()
    with TestClient(create_app(database)) as client:
        assert client.get("/api/catalog").status_code == 503
