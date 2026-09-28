"""Regression tests for numbered-set selection and the Set 18 source shape."""

import json

import pytest

from tft.etl.cdragon import (
    derive_set_prefix,
    find_active_set,
    find_set,
    parse_augments,
    parse_champions,
    parse_items,
    parse_traits,
)
from tft.etl.items import augment_tier, item_category


def test_set_selection_uses_number_and_canonical_mutator() -> None:
    """Canonical Set 18 wins despite its upstream Set10 name and mode variants."""
    sets = [
        {"number": 18, "name": "Set10", "mutator": "TFTSet18_Evolved"},
        {"number": 19, "name": "Set19", "mutator": "TFTSet19"},
        {"number": 18, "name": "Set10", "mutator": "TFTSet18_TURBO"},
        {"number": 18, "name": "Set10", "mutator": "TFTSet18"},
    ]
    assert find_set(sets, 18)["mutator"] == "TFTSet18"
    assert find_active_set(sets)["number"] == 19


def test_active_set_excludes_special_modes() -> None:
    """A higher special-mode number does not replace the standard ranked set."""
    sets = [
        {"number": 18, "mutator": "TFTSet18"},
        {"number": 19, "mutator": "TFTSet19_PVEMODE"},
    ]
    assert find_active_set(sets)["number"] == 18


def test_unavailable_set_fails_without_falling_back() -> None:
    """Explicit set selection cannot silently return the previous release."""
    with pytest.raises(ValueError, match="Set 18 is unavailable"):
        find_set([{"number": 17, "mutator": "TFTSet17"}], 18)
    with pytest.raises(ValueError, match="no sets"):
        find_active_set([])


def test_legacy_prefix_helper_remains_available() -> None:
    """Existing callers can still derive prefixes independently of roster selection."""
    assert derive_set_prefix("TFTSet18", 18) == "TFT18"
    assert derive_set_prefix("Unknown", 99) == "TFT99"


def test_champions_preserve_new_ids_variants_and_ability_data() -> None:
    """Traits retain playable Riftbeasts and alternate forms while excluding props."""
    raw = [
        {"apiName": "TFT_BlueGolem", "cost": 1, "traits": []},
        {"apiName": "DA_18_Prop", "cost": 0, "traits": ["Elderwood"]},
        {"apiName": "DA_18_Unpriced", "traits": ["Elderwood"]},
        {
            "apiName": "DA_Gromp18_AP",
            "name": "Gromp",
            "cost": 2,
            "traits": ["Riftbeast", "Adaptor"],
            "icon": "None",
            "squareIcon": "assets/gromp.dds",
            "stats": {"hp": 750.0},
            "ability": {
                "name": "Leap",
                "desc": "Deal @Damage@ damage.",
                "icon": "assets/gromp_spell.tex",
                "variables": [{"name": "Damage", "value": [0, 100, 150, 200]}],
            },
        },
        {"apiName": "DA_Lux18_Blossom", "cost": 5, "traits": ["Blossom", "Avatar"]},
    ]
    rows = parse_champions(raw)
    assert [row.api_name for row in rows] == ["DA_Gromp18_AP", "DA_Lux18_Blossom"]
    champion = rows[0]
    assert json.loads(champion.traits) == ["Riftbeast", "Adaptor"]
    assert json.loads(champion.stats) == {"hp": 750.0}
    assert champion.icon_url == champion.square_icon_url
    assert champion.icon_url.endswith("/assets/gromp.png")
    assert champion.ability_name == "Leap"
    assert champion.ability_description == "Deal @Damage@ damage."
    assert champion.ability_icon_url.endswith("/assets/gromp_spell.png")
    assert json.loads(champion.ability_variables)[0]["value"] == [0, 100, 150, 200]


def test_traits_preserve_descriptions_and_breakpoints() -> None:
    """Descriptions and source effect objects remain available to the UI."""
    rows = parse_traits(
        [
            {
                "apiName": "DA_18_Elderwood",
                "name": "Elderwood",
                "desc": "Grow plants.",
                "effects": [{"minUnits": 3, "maxUnits": 4, "variables": {"Health": 200}}],
                "icon": "assets/elderwood.tex",
            }
        ]
    )
    assert rows[0].description == "Grow plants."
    assert json.loads(rows[0].effects)[0]["minUnits"] == 3
    assert rows[0].icon_url.endswith("/assets/elderwood.png")


def test_item_membership_uses_active_ids_and_preserves_recipes() -> None:
    """Global entries from inactive releases cannot leak through a prefix rule."""
    raw = [
        {"apiName": "TFT_Item_BFSword", "name": "B.F. Sword", "tags": ["component"]},
        {
            "apiName": "TFT_Item_InfinityEdge",
            "name": "Infinity Edge",
            "composition": ["TFT_Item_BFSword", "TFT_Item_BFSword"],
            "effects": {"AD": 25},
            "desc": "Critical strikes.",
        },
        {"apiName": "DA_18_Emblem", "name": "Elderwood Emblem"},
        {"apiName": "TFT17_Item_OldEmblem", "name": "Old Emblem"},
        {"apiName": "TFT_Item_Retired", "composition": ["A", "B"]},
    ]
    rows = parse_items(raw, ["TFT_Item_InfinityEdge", "TFT_Item_BFSword", "DA_18_Emblem"])
    assert {row.api_name for row in rows} == {
        "TFT_Item_InfinityEdge",
        "TFT_Item_BFSword",
        "DA_18_Emblem",
    }
    completed = next(row for row in rows if row.name == "Infinity Edge")
    assert completed.category == "completed"
    assert json.loads(completed.composition) == ["TFT_Item_BFSword", "TFT_Item_BFSword"]
    assert json.loads(completed.effects) == {"AD": 25}
    assert next(row for row in rows if row.name == "B.F. Sword").category == "component"


def test_incomplete_membership_raises() -> None:
    """A missing selected source record stops a refresh instead of dropping data."""
    with pytest.raises(ValueError, match="missing 1 selected IDs"):
        parse_items([], ["DA_18_Missing"])
    with pytest.raises(TypeError, match="not a set prefix"):
        parse_items([], "TFT18")


def test_support_source_tag_overrides_legacy_asset_name() -> None:
    """Support items may retain an old Radiant or Ornn identifier after migration."""
    assert (
        item_category(
            {
                "apiName": "TFT_Item_RadiantVirtue",
                "name": "Virtue of the Martyr",
                "tags": ["{27557a09}"],
            }
        )
        == "support"
    )
    assert (
        item_category(
            {
                "apiName": "TFT_Assist_ItemArmorySupport",
                "name": "Support Anvil",
            }
        )
        == "special"
    )


def test_augments_include_reused_ids_only_when_active() -> None:
    """Reused old identifiers are valid members of the new set's explicit list."""
    raw = [
        {
            "apiName": "TFT11_Augment_Calltochaos",
            "name": "Call to Chaos",
            "icon": "chaos_iii.tex",
            "effects": {"Gold": 52},
        },
        {"apiName": "TFT17_Augment_Retired", "name": "Retired", "icon": "old_ii.tex"},
    ]
    rows = parse_augments(raw, ["TFT11_Augment_Calltochaos"])
    assert len(rows) == 1
    assert rows[0].tier == "prismatic"
    assert json.loads(rows[0].effects) == {"Gold": 52}


@pytest.mark.parametrize(
    ("icon", "tier"),
    [
        ("augment-i.tex", "silver"),
        ("augment_ii.dds", "gold"),
        ("augment_iii.png", "prismatic"),
        ("salvage2.tex", "gold"),
        ("unclassified.tex", "unknown"),
    ],
)
def test_augment_tier_uses_source_icon_conventions(icon: str, tier: str) -> None:
    """Unknown assets remain unknown instead of inventing an augment tier."""
    assert augment_tier({"icon": icon}) == tier


@pytest.mark.parametrize(
    ("api_name", "name", "category"),
    [
        ("TFT_Item_Artifact_Test", "Test", "artifact"),
        ("TFT_Item_Support_Test", "Test", "support"),
        ("TFT5_Item_Radiant", "Radiant Test", "radiant"),
        ("TFT_Consumable_Test", "Test", "consumable"),
        ("TFT_Assist_Gold_20", "20 Gold", "special"),
    ],
)
def test_item_categories_separate_equipment_from_internal_rewards(
    api_name: str,
    name: str,
    category: str,
) -> None:
    """The UI can expose equipment categories without treating rewards as gear."""
    assert item_category({"apiName": api_name, "name": name}) == category
