"""Regression tests for local composition analysis and report generation."""

import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from tft.analysis.behavior import compute_behavioral_deltas
from tft.analysis.classification import classify_comp_v2
from tft.analysis.data import load_data
from tft.analysis.delta_engine import analyze, run
from tft.analysis.highrolls import compute_exodia_report
from tft.analysis.models import AnalysisLookups, ChampInfo, Unit
from tft.analysis.report import build_comp_popularity, format_report
from tft.analysis.units import _dynamic_threshold
from tft.config import ANALYSIS_THRESHOLD_CAP, ANALYSIS_THRESHOLD_FLOOR, PROJECT_ROOT


@pytest.fixture()
def champion_lookup() -> dict[str, ChampInfo]:
    """Supply set-independent champions using the current DA identifier format."""
    return {
        "da_mage": ("Mage", 3, "APCaster"),
        "da_guard": ("Guard", 4, "ADTank"),
        "da_legend": ("Legend", 5, "APCaster"),
        "da_special": ("Special", 6, "APCaster"),
    }


def _board(units: list[Unit]) -> pd.Series:
    """Serialize a final board with an active sample trait."""
    return pd.Series({
        "units_json": json.dumps(units),
        "traits_json": json.dumps([{
            "name": "DA_Wild", "tier_current": 2, "num_units": 4, "style": 2,
        }]),
    })


def test_classifier_uses_current_ids_and_static_costs(
    champion_lookup: dict[str, ChampInfo],
) -> None:
    """DA IDs and CDragon costs take precedence over legacy rarity codes."""
    row = _board([
        {"character_id": "DA_Mage", "tier": 3, "rarity": 6,
         "itemNames": ["FinishedA", "FinishedB"]},
        {"character_id": "DA_Guard", "tier": 2, "rarity": 0,
         "itemNames": ["FinishedC", "FinishedD"]},
        {"character_id": "TFT_Soldier", "tier": 3, "rarity": 6,
         "itemNames": ["SummonA", "SummonB"]},
    ])
    result = classify_comp_v2(row, champion_lookup, {"DA_Wild": "Wild"})
    assert result["carry_name"] == "Mage"
    assert result["carry_cost"] == 3
    assert result["tank_name"] == "Guard"
    assert result["comp_type"] == "Reroll"
    assert result["comp_group"] == "Wild Mage & Guard (Reroll)"
    assert "SummonA" not in json.loads(result["all_board_items"])


def test_components_do_not_qualify_an_itemized_carry(
    champion_lookup: dict[str, ChampInfo],
) -> None:
    """Component-only units cannot outrank a carry with completed items."""
    row = _board([
        {"character_id": "DA_Mage", "tier": 3,
         "itemNames": ["tft_item_bfsword", "TFT_Item_RecurveBow"]},
        {"character_id": "DA_Legend", "tier": 2,
         "itemNames": ["FinishedA", "FinishedB"]},
    ])
    result = classify_comp_v2(row, champion_lookup, {})
    assert result["carry_name"] == "Legend"


def test_empty_board_has_stable_labels() -> None:
    """An eliminated board without units remains reportable."""
    result = classify_comp_v2(pd.Series({"units_json": "[]", "traits_json": "[]"}), {}, {})
    assert result["carry_name"] == "Unknown"
    assert result["comp_type"] == "Standard"
    assert result["all_board_items"] == "[]"


def test_highrolls_use_cost_lookup_and_include_untracked_opponents(
    champion_lookup: dict[str, ChampInfo],
) -> None:
    """Only four/five-cost units qualify and observed opposing copies are counted."""
    frame = pd.DataFrame([
        {"match_id": "one", "puuid": "c", "tier": "CHALLENGER", "placement": 1,
         "units_json": json.dumps([{"character_id": "DA_Guard", "tier": 3, "rarity": 0}])},
        {"match_id": "one", "puuid": "other", "tier": None, "placement": 7,
         "units_json": json.dumps([{"character_id": "da_guard", "tier": 2}])},
        {"match_id": "two", "puuid": "g", "tier": "GRANDMASTER", "placement": 2,
         "units_json": json.dumps([{"character_id": "DA_Special", "tier": 3, "rarity": 6}])},
    ])
    result = compute_exodia_report(frame, champion_lookup)
    challenger = result.iloc[0]
    assert challenger["Exodia Games"] == 1
    assert challenger["Avg Lobby Copies"] == 3
    assert challenger["Freq %"] == "100.0%"
    assert "GRAND" not in set(result["Tier"])


def test_behavior_labels_top_four_rate_and_uses_static_cost(
    champion_lookup: dict[str, ChampInfo],
) -> None:
    """Placement four is a top four, and cap counts use static champion costs."""
    rows = []
    for tier in ("CHALLENGER", "GRANDMASTER"):
        for _ in range(ANALYSIS_THRESHOLD_FLOOR):
            rows.append({
                "tier": tier, "comp_group": "Wild Mage (Standard)",
                "placement": 4, "carry_star": 1, "carry_items": '["FinishedA"]',
                "all_board_items": '["TFT_Item_IonicSpark", "TFT_Item_Morellonomicon"]',
                "traits_json": "[]",
                "units_json": json.dumps([{"character_id": "DA_Legend", "tier": 2, "rarity": 0}]),
            })
    result = compute_behavioral_deltas(pd.DataFrame(rows), champion_lookup, {})
    assert result.iloc[0]["C Top 4%"] == "100%"
    assert result.iloc[0]["C Cap"] == 1
    assert result.iloc[0]["C Util%"] == "100%"
    assert "C WR%" not in result.columns


def test_popularity_denominator_excludes_untracked_tiers() -> None:
    """Untracked opponents should not dilute tracked-tier play rates."""
    frame = pd.DataFrame([
        {"comp_group": "A", "tier": "CHALLENGER"},
        {"comp_group": "A", "tier": "GRANDMASTER"},
        {"comp_group": "B", "tier": "DIAMOND"},
    ])
    result = build_comp_popularity(frame)
    assert len(result) == 1
    assert result.iloc[0]["Total %"] == "100.0%"


def test_threshold_is_bounded() -> None:
    """Sparse samples cannot bypass the minimum and large samples are capped."""
    assert _dynamic_threshold(0, 10000) == ANALYSIS_THRESHOLD_FLOOR
    assert _dynamic_threshold(100000, 100000) == ANALYSIS_THRESHOLD_CAP


def test_missing_database_does_not_create_file(tmp_path: Path) -> None:
    """Analytics should never create a misleading empty database on a typo."""
    path = tmp_path / "absent.db"
    with pytest.raises(FileNotFoundError, match="Database not found"):
        load_data(path)
    assert not path.exists()


def test_report_without_harvested_matches(tmp_path: Path) -> None:
    """A static-only database yields a useful report instead of a stack trace."""
    path = tmp_path / "static.db"
    sqlite3.connect(path).close()
    output = tmp_path / "reports" / "analysis.md"
    assert run(path, output) == output
    report = output.read_text(encoding="utf-8")
    assert "No harvested matches" in report
    assert "Harvest matches" in report


def test_shared_analysis_returns_empty_tables_without_writing_report(tmp_path: Path) -> None:
    """The reusable analysis service has no generated-report side effect."""
    path = tmp_path / "empty.db"
    sqlite3.connect(path).close()
    result = analyze(path)
    assert result.sample_count == 0
    assert result.versions == []
    assert result.population.empty
    assert result.behavioral.empty
    assert result.highrolls.empty
    assert list(tmp_path.iterdir()) == [path]


def test_shared_analysis_counts_only_tracked_samples(monkeypatch: pytest.MonkeyPatch) -> None:
    """Untracked opponents remain contextual data without inflating ranked samples."""
    rows = [
        {"match_id": "one", "puuid": str(index), "tier": tier, "placement": index + 1,
         "units_json": "[]", "traits_json": "[]", "game_version": "test-version"}
        for index, tier in enumerate(("CHALLENGER", "GRANDMASTER", None))
    ]

    def sample_data(db_path: Path, game_version: str | None) -> pd.DataFrame:
        """Return a small harvested sample for shared-service orchestration."""
        return pd.DataFrame(rows)

    def static_lookups(db_path: Path) -> AnalysisLookups:
        """Provide empty lookups for the empty participant boards."""
        return AnalysisLookups({}, {}, {}, {})

    monkeypatch.setattr("tft.analysis.delta_engine.load_data", sample_data)
    monkeypatch.setattr("tft.analysis.delta_engine.load_lookups", static_lookups)
    result = analyze()
    assert result.sample_count == 2
    assert result.versions == ["test-version"]
    assert result.population.iloc[0]["Total"] == 2


def test_load_data_preserves_untracked_rows_and_filters_version(tmp_path: Path) -> None:
    """Patch selection is exact and missing rank labels do not drop opponents."""
    path = tmp_path / "matches.db"
    conn = sqlite3.connect(path)
    try:
        conn.executescript((PROJECT_ROOT / "src/tft/db/match_schema.sql").read_text())
        conn.executemany("INSERT INTO matches (match_id, game_version) VALUES (?, ?)", [("one", "patch-one"), ("two", "patch-two")])
        conn.execute("INSERT INTO players VALUES (?, ?)", ("tracked", "CHALLENGER"))
        conn.executemany("INSERT INTO match_participants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            ("one", "tracked", 1, 9, 0, 1000, "[]", "[]", "[]"),
            ("one", "untracked", 8, 7, 0, 500, "[]", "[]", "[]"),
            ("two", "tracked", 2, 9, 0, 1000, "[]", "[]", "[]"),
        ])
        conn.commit()
    finally:
        conn.close()
    frame = load_data(path, "patch-one")
    assert len(frame) == 2
    assert set(frame["puuid"]) == {"tracked", "untracked"}
    assert frame["tier"].isna().sum() == 1
    assert load_data(path, "patch-one' OR 1=1 --").empty


def test_report_identifies_mixed_versions_and_observation_limits() -> None:
    """The report must expose patch mixing and avoid inferring player actions."""
    report = format_report(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), ["v1", "v2"])
    assert "Multiple game versions" in report
    assert "--game-version" in report
    assert "do not establish a skill gap" in report
    assert "cannot establish whether a player sold units" in report
