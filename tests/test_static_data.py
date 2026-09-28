"""Integration tests for atomic static refreshes and their persisted provenance."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from tft.db.connection import DatabaseRow, get_connection, insert_rows
from tft.db.models import ChampionRow
from tft.etl.static_data import refresh_static_data
from tft.web.catalog import read_catalog


@pytest.fixture()
def snapshot(tmp_path: Path) -> Path:
    """Write a compact snapshot matching Set 18's live membership structure."""
    data: dict[str, Any] = {
        "items": [
            {"apiName": "TFT_Item_Sword", "name": "Sword", "tags": ["component"]},
            {
                "apiName": "TFT11_Augment_Chaos",
                "name": "Chaos",
                "isAugment": True,
                "icon": "chaos_iii.tex",
            },
        ],
        "setData": [
            {
                "number": 18,
                "name": "Set10",
                "mutator": "TFTSet18",
                "champions": [
                    {"apiName": "DA_18_Ahri", "name": "Ahri", "cost": 4, "traits": ["Blossom"]}
                ],
                "traits": [{"apiName": "DA_18_Blossom", "name": "Blossom", "desc": "Bloom."}],
                "items": ["TFT_Item_Sword"],
                "augments": ["TFT11_Augment_Chaos"],
            }
        ],
        "version": "16.18.8175716+branch.releases-16-18.content.release",
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_refresh_records_provenance_and_is_idempotent(snapshot: Path, tmp_path: Path) -> None:
    """The catalog retains current set identity without confusing build and patch."""
    db_path = tmp_path / "catalog.db"
    refresh_static_data(db_path, source_path=snapshot, patch="18.2")
    metadata = refresh_static_data(db_path, source_path=snapshot, patch="18.2")
    conn = get_connection(db_path)
    try:
        assert metadata.set_name == "Enchanted Wilds"
        assert metadata.source_set_name == "Set10"
        assert metadata.patch == "18.2"
        assert metadata.source_version.startswith("16.18.")
        assert conn.execute("SELECT COUNT(*) FROM champions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0] == 1
        row = conn.execute("SELECT * FROM champions").fetchone()
        assert row["api_name"] == "DA_18_Ahri"
        assert json.loads(row["traits"]) == ["Blossom"]
        assert conn.execute("SELECT tier FROM augments").fetchone()[0] == "prismatic"
    finally:
        conn.close()


def test_patch_defaults_to_unknown(snapshot: Path, tmp_path: Path) -> None:
    """A CDragon content build must never be advertised as a TFT patch number."""
    metadata = refresh_static_data(tmp_path / "catalog.db", source_path=snapshot)
    assert metadata.patch is None
    assert metadata.source_version is not None


def test_failed_refresh_rolls_back_schema_rows_and_preserves_matches(
    snapshot: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An insertion failure after DROP/CREATE restores the whole previous catalog."""
    db_path = tmp_path / "catalog.db"
    refresh_static_data(db_path, source_path=snapshot, patch="previous")
    conn = get_connection(db_path)
    try:
        conn.execute("CREATE TABLE matches (match_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO matches VALUES ('saved-match')")
        conn.execute("UPDATE champions SET name = 'Previous Ahri'")
        conn.commit()
    finally:
        conn.close()

    def fail_after_champions(
        conn: sqlite3.Connection,
        table: str,
        rows: list[DatabaseRow],
        *,
        commit: bool = True,
    ) -> int:
        """Fail after schema replacement and one successful batch insertion."""
        if table == "traits":
            raise sqlite3.IntegrityError("simulated insertion failure")
        return insert_rows(conn, table, rows, commit=commit)

    monkeypatch.setattr("tft.etl.static_data.insert_rows", fail_after_champions)
    with pytest.raises(sqlite3.IntegrityError, match="simulated"):
        refresh_static_data(db_path, source_path=snapshot, patch="new")
    conn = get_connection(db_path)
    try:
        assert conn.execute("SELECT name FROM champions").fetchone()[0] == "Previous Ahri"
        assert conn.execute("SELECT patch FROM metadata").fetchone()[0] == "previous"
        assert conn.execute("SELECT match_id FROM matches").fetchone()[0] == "saved-match"
    finally:
        conn.close()


def test_successful_refresh_preserves_match_tables(snapshot: Path, tmp_path: Path) -> None:
    """A successful static update leaves harvested match history untouched."""
    db_path = tmp_path / "catalog.db"
    conn = get_connection(db_path)
    try:
        conn.execute("CREATE TABLE matches (match_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO matches VALUES ('saved-match')")
        conn.commit()
    finally:
        conn.close()
    refresh_static_data(db_path, source_path=snapshot)
    conn = get_connection(db_path)
    try:
        assert conn.execute("SELECT match_id FROM matches").fetchone()[0] == "saved-match"
    finally:
        conn.close()


def test_missing_set_does_not_create_database(snapshot: Path, tmp_path: Path) -> None:
    """Invalid snapshots fail during parsing, before opening the destination."""
    db_path = tmp_path / "uncreated.db"
    with pytest.raises(ValueError, match="Set 19 is unavailable"):
        refresh_static_data(db_path, set_number=19, source_path=snapshot)
    assert not db_path.exists()


def test_supplemental_abilities_survive_catalog_roundtrip(
    snapshot: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sourced formulas and verified stat corrections reach the browser intact."""
    payload = {
        "source": {"name": "MetaTFT", "patch": "pbe"},
        "forms": [{"name": "Spirit Bomb", "description": "455 AP", "label": "Base"}],
        "stat_corrections": {"mana": 100},
    }

    def supplement(
        champions: list[ChampionRow], source_path: Path | None, *, patch: str
    ) -> dict[str, Any]:
        """Stand in for a reviewed, independently tested source adapter."""
        assert patch == "18.2"
        assert source_path is None
        return {champions[0].api_name: payload}

    monkeypatch.setattr("tft.etl.static_data.load_ability_details", supplement)
    database = tmp_path / "enriched.db"
    refresh_static_data(database, source_path=snapshot, patch="18.2", with_abilities=True)
    champion = read_catalog(database)["champions"][0]
    assert champion["ability_detail"] == payload
    assert champion["stats"]["mana"] == 100


def test_unreviewed_ability_source_keeps_previous_catalog(
    snapshot: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed supplemental export cannot partially replace a good catalog."""
    database = tmp_path / "preserved.db"
    refresh_static_data(database, source_path=snapshot, patch="18.2")
    before = read_catalog(database)

    def unreviewed(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Reject a reference export whose fingerprint changed."""
        raise ValueError("Unreviewed source")

    monkeypatch.setattr("tft.etl.static_data.load_ability_details", unreviewed)
    with pytest.raises(ValueError, match="Unreviewed"):
        refresh_static_data(database, source_path=snapshot, patch="18.2", with_abilities=True)
    assert read_catalog(database) == before
