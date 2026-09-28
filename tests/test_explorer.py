"""Regression tests for explorer filters, statistics, board loading, and API."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tft.config import MATCH_SCHEMA_PATH
from tft.exceptions import ExplorerQueryError
from tft.explorer.aggregate import breakdowns, focus_breakdown, summarize
from tft.explorer.dataset import load_boards, parse_board
from tft.explorer.filters import apply_filters, parse_filters
from tft.explorer.models import Board, BoardSet, BoardUnit, ExplorerQuery
from tft.explorer.service import explore_boards
from tft.web.app import create_app


def _board(
    placement: int,
    units: list[tuple[str, int, tuple[str, ...]]],
    traits: dict[str, int] | None = None,
    level: int = 8,
    augments: tuple[str, ...] = (),
    rank: str = "CHALLENGER",
    version: str = "v1",
) -> Board:
    """Build a board from compact unit tuples of (id, star, items)."""
    return Board(
        placement=placement,
        level=level,
        rank=rank,
        game_version=version,
        units=tuple(BoardUnit(uid, star, items) for uid, star, items in units),
        traits=traits or {},
        augments=frozenset(augments),
    )


@pytest.fixture()
def boards() -> list[Board]:
    """Four boards with overlapping units, items, traits, and augments."""
    return [
        _board(1, [("mage", 3, ("rod", "rod", "hat")), ("guard", 2, ())],
               {"wild": 2}, level=9, augments=("spark",)),
        _board(3, [("mage", 2, ("rod",)), ("guard", 2, ("vest",))], {"wild": 1}),
        _board(6, [("guard", 1, ("vest", "vest")), ("scout", 2, ())],
               {"wild": 1}, level=7, rank="GRANDMASTER"),
        _board(8, [("scout", 1, ("rod",))], level=6, version="v2"),
    ]


def _placements(rows: list[Board]) -> list[int]:
    """Placements of the given boards, in order."""
    return [board.placement for board in rows]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ([{"kind": "unit", "id": "MAGE"}], [1, 3]),
        ([{"kind": "unit", "id": "mage", "stars": [3]}], [1]),
        ([{"kind": "unit", "id": "mage", "items": ["rod", "rod"]}], [1]),
        ([{"kind": "unit", "id": "guard", "min_items": 1}], [3, 6]),
        ([{"kind": "unit", "id": "mage", "exclude": True}], [6, 8]),
        ([{"kind": "item", "id": "vest", "min_count": 2}], [6]),
        ([{"kind": "item", "id": "rod"}], [1, 3, 8]),
        ([{"kind": "trait", "id": "wild", "min_tier": 2}], [1]),
        ([{"kind": "trait", "id": "wild", "max_tier": 1}], [3, 6]),
        ([{"kind": "augment", "id": "spark"}], [1]),
        ([{"kind": "level", "min": 7, "max": 8}], [3, 6]),
        ([{"kind": "unit", "id": "guard"}, {"kind": "item", "id": "rod"}], [1, 3]),
        (
            [{"kind": "any", "filters": [
                {"kind": "unit", "id": "mage", "stars": [3]},
                {"kind": "unit", "id": "scout", "stars": [1]},
            ]}],
            [1, 8],
        ),
        (
            [{"kind": "any", "exclude": True, "filters": [
                {"kind": "unit", "id": "mage"}, {"kind": "level", "max": 6},
            ]}],
            [6],
        ),
    ],
)
def test_filters_combine_with_and_or_and_exclude(
    boards: list[Board], spec: list[dict[str, Any]], expected: list[int],
) -> None:
    """Filters match unit constraints, counts, tiers, and logical groups."""
    assert _placements(apply_filters(boards, parse_filters(json.dumps(spec)))) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '{"kind": "unit"}',
        '[{"kind": "unit"}]',
        '[{"kind": "unit", "id": "a", "stars": [4]}]',
        '[{"kind": "unit", "id": "a", "stars": [true]}]',
        '[{"kind": "unit", "id": "a", "items": ["a", "b", "c", "d"]}]',
        '[{"kind": "level", "min": 9, "max": 8}]',
        '[{"kind": "any", "filters": []}]',
        '[{"kind": "any", "filters": [{"kind": "any", "filters": []}]}]',
        '[{"kind": "mystery", "id": "a"}]',
        '[{"kind": "augment", "id": "a", "exclude": "yes"}]',
        json.dumps([{"kind": "augment", "id": "a"}] * 25),
    ],
)
def test_invalid_filters_are_rejected(raw: str) -> None:
    """Malformed or oversized requests fail with a specific error."""
    with pytest.raises(ExplorerQueryError):
        parse_filters(raw)


def test_summary_and_breakdowns_count_each_board_once(boards: list[Board]) -> None:
    """Rows report distinct-board games, rates, frequency, and delta."""
    summary = summarize(boards)
    assert summary == {
        "games": 4, "avg_place": 4.5, "top4": 0.5, "win": 0.25,
        "placements": [1, 0, 1, 0, 0, 1, 0, 1],
    }
    tables = breakdowns(boards, summary["avg_place"])
    rod = next(row for row in tables["items"] if row["id"] == "rod")
    assert (rod["games"], rod["frequency"], rod["avg_place"]) == (3, 0.75, 4.0)
    assert rod["delta"] == -0.5
    mage = next(row for row in tables["units"] if row["id"] == "mage")
    assert (mage["games"], mage["top4"], mage["win"]) == (2, 1.0, 0.5)
    assert {(row["id"], row["star"]) for row in tables["unit_stars"]} >= {
        ("mage", 3), ("mage", 2), ("guard", 1),
    }
    assert {(row["id"], row["tier"]) for row in tables["traits"]} == {("wild", 1), ("wild", 2)}
    assert [row["level"] for row in tables["levels"]] == [6, 7, 8, 9]
    assert tables["augments"][0]["id"] == "spark"


def test_focus_breakdown_describes_one_unit(boards: list[Board]) -> None:
    """Focus rows compare stars, item counts, items, and builds of one unit."""
    focus = focus_breakdown(boards, "guard")
    assert focus["games"] == 3
    assert [row["star"] for row in focus["stars"]] == [1, 2]
    assert [row["item_count"] for row in focus["item_counts"]] == [0, 1, 2]
    assert {row["id"] for row in focus["items"]} == {"vest"}
    assert sorted(tuple(row["items"]) for row in focus["builds"]) == [
        ("vest",), ("vest", "vest"),
    ]
    assert focus["stars"][0]["frequency"] == round(1 / 3, 4)


def test_explore_scopes_by_version_and_rank(boards: list[Board]) -> None:
    """Base statistics honour the selected version and rank before filtering."""
    board_set = BoardSet(tuple(boards), ("v2", "v1"), ("CHALLENGER", "GRANDMASTER"), True)
    query = ExplorerQuery(
        filters=parse_filters('[{"kind": "unit", "id": "guard"}]'),
        game_version="v1",
        rank="CHALLENGER",
        focus_unit="guard",
    )
    result = explore_boards(board_set, query)
    assert result["base"]["games"] == 2
    assert result["filtered"]["games"] == 2
    assert result["focus"] is not None and result["focus"]["games"] == 2
    assert result["versions"] == ["v2", "v1"]


def test_parse_board_normalises_ids_and_skips_summons() -> None:
    """Stored Riot payloads become lowercase boards without summoned units."""
    board = parse_board({
        "match_id": "m1", "placement": 2, "level": 8, "tier": None, "game_version": "v1",
        "units_json": json.dumps([
            {"character_id": "TFT18_Ahri", "tier": 2, "itemNames": ["TFT_Item_Rod"]},
            {"character_id": "TFT18_Prop", "tier": 1, "itemNames": []},
        ]),
        "traits_json": json.dumps([
            {"name": "TFT18_Wild", "tier_current": 1},
            {"name": "TFT18_Idle", "tier_current": 0},
        ]),
        "augments_json": json.dumps(["TFT_Augment_Spark"]),
    })
    assert board is not None
    assert board.units == (BoardUnit("tft18_ahri", 2, ("tft_item_rod",)),)
    assert board.traits == {"tft18_wild": 1}
    assert board.augments == frozenset({"tft_augment_spark"})
    assert board.rank == "UNTRACKED"
    assert parse_board({"match_id": "bad", "units_json": "{", "traits_json": "[]",
                        "augments_json": "[]"}) is None


def _write_matches(path: Path) -> None:
    """Create a catalog-scoped database with one complete two-player match."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(MATCH_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("CREATE TABLE metadata (set_number INTEGER)")
        conn.execute("INSERT INTO metadata VALUES (18)")
        conn.execute(
            "INSERT INTO matches (match_id, game_version, set_number, queue_id) "
            "VALUES ('m1', 'v1', 18, 1100)"
        )
        conn.execute("INSERT INTO players VALUES ('tracked', 'CHALLENGER')")
        for puuid, placement, unit in (("tracked", 1, "TFT18_Ahri"), ("rival", 5, "TFT18_Zed")):
            conn.execute(
                "INSERT INTO match_participants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("m1", puuid, placement, 8, 0, 1000, "[]",
                 json.dumps([{"character_id": unit, "tier": 2, "itemNames": []}]), "[]"),
            )
        conn.commit()
    finally:
        conn.close()


def test_load_boards_refreshes_after_database_changes(tmp_path: Path) -> None:
    """Cached boards are reused until the database file changes."""
    path = tmp_path / "matches.db"
    _write_matches(path)
    first = load_boards(path)
    assert load_boards(path) is first
    assert first.ranks == ("CHALLENGER", "UNTRACKED")
    conn = sqlite3.connect(path)
    try:
        conn.execute("DELETE FROM match_participants WHERE puuid = 'rival'")
        conn.commit()
    finally:
        conn.close()
    assert len(load_boards(path).boards) == 1


def test_explorer_api_filters_stored_boards(tmp_path: Path) -> None:
    """The endpoint validates filters and returns filtered statistics."""
    path = tmp_path / "matches.db"
    _write_matches(path)
    with TestClient(create_app(path)) as client:
        filters = json.dumps([{"kind": "unit", "id": "TFT18_Ahri", "stars": [2]}])
        response = client.get("/api/explorer", params={"filters": filters, "focus": "TFT18_Ahri"})
        invalid = client.get("/api/explorer", params={"filters": "[{}]"})
        untracked = client.get("/api/explorer", params={"rank": "UNTRACKED"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["base"]["games"] == 2
    assert payload["filtered"]["games"] == 1
    assert payload["units"][0]["id"] == "tft18_ahri"
    assert payload["focus"]["stars"][0]["star"] == 2
    assert response.headers["cache-control"] == "no-store"
    assert invalid.status_code == 400
    assert untracked.json()["filtered"]["games"] == 1


def test_explorer_api_without_matches_is_empty(tmp_path: Path) -> None:
    """A static-only database yields an empty explorer rather than an error."""
    path = tmp_path / "static-only.db"
    sqlite3.connect(path).close()
    with TestClient(create_app(path)) as client:
        response = client.get("/api/explorer")
    assert response.status_code == 200
    payload = response.json()
    assert payload["base"]["games"] == 0
    assert payload["filtered"]["avg_place"] is None
    assert payload["units"] == [] and payload["focus"] is None
    with TestClient(create_app(tmp_path / "absent.db")) as client:
        assert client.get("/api/explorer").status_code == 503
