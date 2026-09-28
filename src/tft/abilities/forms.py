"""Exact source-identity joins and normalized champion ability variants."""

import json
from copy import deepcopy
from typing import Any

from tft.abilities.models import AbilityForm, CurveValues
from tft.db.models import ChampionRow


def index_units(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index only explicit asset aliases, rejecting ambiguous source identities."""
    units = data.get("units")
    aliases = data.get("unitAssetNames")
    if not isinstance(units, list) or not isinstance(aliases, dict):
        raise ValueError("Ability source has no units list or asset alias mapping")
    by_name: dict[str, dict[str, Any]] = {}
    by_asset: dict[str, dict[str, Any]] = {}
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("apiName"), str):
            raise ValueError("Ability source contains an invalid unit")
        name = unit["apiName"]
        if name in by_name:
            raise ValueError(f"Duplicate ability unit identity: {name}")
        by_name[name] = unit
        for asset in unit.get("assetNames", []):
            if not isinstance(asset, str):
                raise ValueError("Ability source contains a non-string asset alias")
            if asset in by_asset:
                raise ValueError(f"Ambiguous ability asset alias: {asset}")
            by_asset[asset] = unit
    for asset, name in aliases.items():
        if name not in by_name:
            continue
        unit = by_name[name]
        if asset in by_asset and by_asset[asset] is not unit:
            raise ValueError(f"Conflicting ability asset alias: {asset}")
        by_asset[asset] = unit
    return by_asset


def build_forms(champion: ChampionRow, unit: dict[str, Any]) -> list[AbilityForm]:
    """Select Avatar traits exactly, otherwise preserve AD/AP alternate abilities.

    Source asset aliases establish unit identity. Explicit trait arrays on Lux
    variants then establish the origin, including Solar/Sunbeam and Lunar/Moonbeam.
    Descriptive names are never used as an identity fallback.
    """
    traits = frozenset(json.loads(champion.traits))
    extra = unit.get("extraAbilities") or {}
    unit_variants = [value for value in extra.values() if value.get("traits")]
    if unit_variants:
        selected = [value for value in unit_variants if frozenset(value["traits"]) == traits]
        if len(selected) == 1:
            label = ", ".join(trait for trait in selected[0]["traits"] if trait != "Avatar")
            return [_normalize_form(unit, selected[0], label)]
        if selected or traits != frozenset(unit.get("traits", [])):
            return []
        return [_normalize_form(unit, unit.get("ability") or {}, "Base")]

    primary_asset = (unit.get("assetNames") or [""])[0]
    label = primary_asset.rsplit("_", 1)[-1]
    label = label if label in {"AD", "AP"} else "Ability"
    forms = [_normalize_form(unit, unit.get("ability") or {}, label)]
    forms.extend(
        _normalize_form(unit, variant, variant.get("variant") or "Alternate")
        for variant in extra.values()
        if variant.get("desc")
    )
    return [form for form in forms if form["description"]]


def _normalize_form(
    unit: dict[str, Any], ability: dict[str, Any], label: str
) -> AbilityForm:
    """Merge explicit curve points while keeping each form's calculations isolated."""
    curves: CurveValues = {}
    for owner in (unit, ability):
        # Full curveTable values are authoritative over tooltip-extracted values
        # from the same owner. Alternate forms may supply their own overrides.
        for field in ("curveValues", "curveTable"):
            curves.update(deepcopy(owner.get(field) or {}))
    footer = deepcopy(ability.get("footer") or [])
    for entry in footer:
        row = entry.get("row")
        if row in curves:
            entry["values"] = deepcopy(curves[row])
        if "curveValues" in entry:
            entry["curveValues"] = {
                key: deepcopy(curves.get(key, points))
                for key, points in entry["curveValues"].items()
            }
    return {
        "name": ability.get("name") or "",
        "label": label,
        "description": ability.get("desc") or "",
        "curve_values": curves,
        "attribute_calcs": deepcopy(ability.get("attributeCalcs") or {}),
        "attribute_values": deepcopy(ability.get("attributeValues") or {}),
        "footer": footer,
    }
