"""Tests for tft.etl.cdragon parsing functions."""

import json

from tft.etl.cdragon import (
    derive_set_prefix,
    find_active_set,
    parse_champions,
    parse_items,
    parse_traits,
)


# ---------------------------------------------------------------------------
# find_active_set
# ---------------------------------------------------------------------------

class TestFindActiveSet:
    """find_active_set() picks the right set from setData."""

    def test_picks_highest_set_number(self) -> None:
        sets = [
            {"number": 13, "name": "Set13", "mutator": "TFTSet13"},
            {"number": 16, "name": "Set16", "mutator": "TFTSet16"},
            {"number": 14, "name": "Set14", "mutator": "TFTSet14"},
        ]
        result = find_active_set(sets)
        assert result["number"] == 16

    def test_excludes_turbo_modes(self) -> None:
        sets = [
            {"number": 16, "name": "Set16", "mutator": "TFTSet16"},
            {"number": 16, "name": "Set16", "mutator": "TFTSet16_TURBO"},
        ]
        result = find_active_set(sets)
        assert result["mutator"] == "TFTSet16"

    def test_prefers_shortest_mutator(self) -> None:
        sets = [
            {"number": 16, "name": "Set16", "mutator": "TFTSet16"},
            {"number": 16, "name": "Set16", "mutator": "TFTSet16_Evolved"},
        ]
        result = find_active_set(sets)
        assert result["mutator"] == "TFTSet16"


# ---------------------------------------------------------------------------
# derive_set_prefix
# ---------------------------------------------------------------------------

class TestDeriveSetPrefix:
    """derive_set_prefix() normalises mutator → item prefix."""

    def test_standard_mutator(self) -> None:
        assert derive_set_prefix("TFTSet16", 16) == "TFT16"

    def test_fallback_from_number(self) -> None:
        assert derive_set_prefix("SomethingWeird", 99) == "TFT99"


# ---------------------------------------------------------------------------
# parse_champions
# ---------------------------------------------------------------------------

class TestParseChampions:
    """parse_champions() filters and normalises champion data."""

    def test_excludes_cost_zero(self) -> None:
        raw = [
            {"apiName": "TFT16_Dummy", "name": "Dummy", "cost": 0, "traits": []},
            {"apiName": "TFT16_Ahri", "name": "Ahri", "cost": 4, "traits": ["Arcanist"]},
        ]
        result = parse_champions(raw)
        assert len(result) == 1
        assert result[0]["api_name"] == "TFT16_Ahri"

    def test_excludes_missing_cost(self) -> None:
        raw = [{"apiName": "TFT16_Prop", "name": "Prop", "traits": []}]
        result = parse_champions(raw)
        assert len(result) == 0

    def test_traits_stored_as_json(self) -> None:
        raw = [{"apiName": "TFT16_Ahri", "name": "Ahri", "cost": 4, "traits": ["Arcanist", "Ionia"]}]
        result = parse_champions(raw)
        traits = json.loads(result[0]["traits"])
        assert traits == ["Arcanist", "Ionia"]


# ---------------------------------------------------------------------------
# parse_traits
# ---------------------------------------------------------------------------

class TestParseTraits:
    """parse_traits() converts raw trait dicts to row dicts."""

    def test_basic_parse(self) -> None:
        raw = [
            {
                "apiName": "TFT16_Arcanist",
                "name": "Arcanist",
                "effects": [{"minUnits": 2, "maxUnits": 3}],
                "icon": "ASSETS/UX/TraitIcons/Arcanist.tex",
            }
        ]
        result = parse_traits(raw)
        assert len(result) == 1
        assert result[0]["api_name"] == "TFT16_Arcanist"
        assert result[0]["icon_url"] is not None


# ---------------------------------------------------------------------------
# parse_items
# ---------------------------------------------------------------------------

class TestParseItems:
    """parse_items() filters for standard items + set emblems."""

    _SAMPLE_ITEMS = [
        # Base component
        {"apiName": "TFT_Item_BFSword", "name": "B.F. Sword", "composition": [], "desc": "+AD", "icon": "bf.tex"},
        {"apiName": "TFT_Item_NeedlesslyLargeRod", "name": "Rod", "composition": [], "desc": "+AP", "icon": "rod.tex"},
        # Standard crafted
        {"apiName": "TFT_Item_InfinityEdge", "name": "IE", "composition": ["TFT_Item_BFSword", "TFT_Item_NeedlesslyLargeRod"], "desc": "Crit", "icon": "ie.tex"},
        # Augment (should be excluded)
        {"apiName": "TFT16_Augment_Something", "name": "Augment", "composition": [], "desc": "aug", "icon": "aug.tex"},
        # Set emblem (should be included)
        {"apiName": "TFT16_Item_SlayerEmblemItem", "name": "Slayer Emblem", "composition": ["TFT_Item_BFSword", "TFT_Item_NeedlesslyLargeRod"], "desc": "emblem", "icon": "emblem.tex"},
    ]

    def test_includes_components_and_crafted(self) -> None:
        result = parse_items(self._SAMPLE_ITEMS, "TFT16")
        names = {r["name"] for r in result}
        assert "B.F. Sword" in names
        assert "IE" in names

    def test_includes_set_emblems(self) -> None:
        result = parse_items(self._SAMPLE_ITEMS, "TFT16")
        names = {r["name"] for r in result}
        assert "Slayer Emblem" in names

    def test_excludes_augments(self) -> None:
        result = parse_items(self._SAMPLE_ITEMS, "TFT16")
        names = {r["name"] for r in result}
        assert "Augment" not in names

    def test_no_duplicates(self) -> None:
        result = parse_items(self._SAMPLE_ITEMS, "TFT16")
        api_names = [r["api_name"] for r in result]
        assert len(api_names) == len(set(api_names))
