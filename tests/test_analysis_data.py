"""Regression tests for catalog-compatible analysis and legacy match schemas."""

import sqlite3
from pathlib import Path

import pytest

from tft.analysis.data import load_data
from tft.config import MATCH_SCHEMA_PATH


def test_catalog_scope_excludes_other_sets_and_unverified_queues(tmp_path: Path) -> None:
    """An unknown version shared across sets cannot mix incompatible boards."""
    path = tmp_path / "scoped.db"
    version = "TFT Unreal Version ?.?.?.?"
    matches = [
        ("current", version, 18, 1100),
        ("previous", version, 17, 1100),
        ("casual", version, 18, 1090),
        ("unknown-set", version, None, 1100),
        ("unknown-queue", version, 18, None),
    ]
    conn = sqlite3.connect(path)
    try:
        conn.executescript(MATCH_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("CREATE TABLE metadata (set_number INTEGER)")
        conn.execute("INSERT INTO metadata VALUES (18)")
        conn.executemany(
            "INSERT INTO matches (match_id, game_version, set_number, queue_id) VALUES (?, ?, ?, ?)",
            matches,
        )
        conn.execute("INSERT INTO players VALUES ('tracked', 'CHALLENGER')")
        conn.executemany(
            "INSERT INTO match_participants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(match_id, "tracked", 1, 9, 0, 1000, "[]", "[]", "[]")
             for match_id, _, _, _ in matches],
        )
        conn.execute(
            "INSERT INTO match_participants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("current", "opponent", 8, 7, 0, 500, "[]", "[]", "[]"),
        )
        conn.commit()
    finally:
        conn.close()

    for selected_version in (None, version):
        frame = load_data(path, selected_version)
        assert set(frame["match_id"]) == {"current"}
        assert set(frame["puuid"]) == {"tracked", "opponent"}
        assert frame["tier"].isna().sum() == 1
    assert load_data(path, "different-version").empty


@pytest.mark.parametrize("metadata_shape", ["absent", "legacy", "current"])
def test_old_match_schema_handles_catalog_provenance(
    tmp_path: Path, metadata_shape: str,
) -> None:
    """Old tables keep legacy behavior, but cannot qualify for a verified set."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE matches (match_id TEXT PRIMARY KEY, game_version TEXT NOT NULL)")
        conn.executescript(MATCH_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.executemany("INSERT INTO matches VALUES (?, ?)", [("one", "v1"), ("two", "v2")])
        conn.executemany(
            "INSERT INTO match_participants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(match_id, "tracked", 1, 9, 0, 1000, "[]", "[]", "[]")
             for match_id in ("one", "two")],
        )
        if metadata_shape == "current":
            conn.execute("CREATE TABLE metadata (set_number INTEGER)")
            conn.execute("INSERT INTO metadata VALUES (18)")
        elif metadata_shape == "legacy":
            conn.execute("CREATE TABLE metadata (patch TEXT)")
            conn.execute("INSERT INTO metadata VALUES ('v1')")
        conn.commit()
    finally:
        conn.close()

    frame = load_data(path)
    if metadata_shape == "current":
        assert frame.empty
        assert load_data(path, "v1").empty
    else:
        assert set(frame["match_id"]) == {"one", "two"}
        assert set(load_data(path, "v1")["match_id"]) == {"one"}
