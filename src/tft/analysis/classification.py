"""Classify compositions from their final board and static champion roles."""

import json

import pandas as pd

from tft.analysis.models import ChampInfo, ClassifiedBoard, Trait, Unit
from tft.analysis.units import (
    _clean_trait_name,
    _completed_item_count,
    _is_real_champion,
    _is_team_trait,
    _unit_cost,
    _unit_name,
    _unit_role,
)
from tft.config import (
    ANALYSIS_MIN_ITEMS,
    ANALYSIS_STAR_WEIGHT,
    DAMAGE_ROLES,
    DEFENSIVE_ROLES,
)


def classify_comp_v2(
    row: pd.Series,
    cl: dict[str, ChampInfo],
    tl: dict[str, str],
) -> ClassifiedBoard:
    """Classify a board using Investment Score and CDragon roles.

    Investment Score = ``(star_level × 10) + unit_cost``.
    Primary Carry = highest-score itemised unit with a damage role.
    Primary Tank  = highest-score itemised unit with a defensive role.

    Args:
        row: DataFrame row with ``units_json`` and ``traits_json``.
        cl: Champion lookup.
        tl: Trait lookup.

    Returns:
        Dict with comp_name, carry/tank info, comp_type, and board items.
    """
    units: list[Unit] = json.loads(row["units_json"])
    traits: list[Trait] = json.loads(row["traits_json"])
    real = [u for u in units if _is_real_champion(u.get("character_id", ""))]

    # ── Score itemised units (≥2 completed items) ─────────────────────
    scored: list[tuple[Unit, int, str | None]] = []
    for u in real:
        if _completed_item_count(u.get("itemNames", [])) >= ANALYSIS_MIN_ITEMS:
            star = u.get("tier", 1)
            score = (star * ANALYSIS_STAR_WEIGHT) + _unit_cost(u, cl)
            scored.append((u, score, _unit_role(u, cl)))

    # Fall back to all real units if nobody qualifies.
    if not scored:
        for u in real:
            star = u.get("tier", 1)
            score = (star * ANALYSIS_STAR_WEIGHT) + _unit_cost(u, cl)
            scored.append((u, score, _unit_role(u, cl)))

    # ── Carry & Tank ──────────────────────────────────────────────────
    dmg = [(u, s) for u, s, r in scored if r in DAMAGE_ROLES]
    tnk = [(u, s) for u, s, r in scored if r in DEFENSIVE_ROLES]

    carry_u = (
        max(dmg, key=lambda x: x[1])[0]
        if dmg
        else (max(scored, key=lambda x: x[1])[0] if scored else None)
    )
    tank_u = max(tnk, key=lambda x: x[1])[0] if tnk else None

    carry_id = carry_u["character_id"] if carry_u else ""
    carry_nm = _unit_name(carry_u, cl) if carry_u else "Unknown"
    carry_st = carry_u.get("tier", 1) if carry_u else 1
    carry_co = _unit_cost(carry_u, cl) if carry_u else 0
    carry_it = carry_u.get("itemNames", []) if carry_u else []
    tank_nm = _unit_name(tank_u, cl) if tank_u else "Flex"
    tank_id = tank_u["character_id"] if tank_u else ""

    # ── Reroll check ──────────────────────────────────────────────────
    comp_type = "Reroll" if (carry_co <= 3 and carry_st == 3) else "Standard"

    # ── Primary trait ─────────────────────────────────────────────────
    active = [
        t for t in traits if t.get("tier_current", 0) >= 1 and _is_team_trait(t.get("name", ""))
    ]
    if active:
        best = max(
            active,
            key=lambda t: (
                t.get("tier_current", 0),
                t.get("num_units", 0),
                t.get("style", 0),
            ),
        )
        t_name = tl.get(best["name"], _clean_trait_name(best["name"]))
        t_count = best.get("num_units", 0)
    else:
        t_name, t_count = "Flex", 0

    comp_name = f"{t_count} {t_name} {carry_nm} & {tank_nm} ({comp_type})"
    # Grouping key strips the trait count to prevent fragmentation.
    comp_group = f"{t_name} {carry_nm} & {tank_nm} ({comp_type})"

    # ── Flatten all board items ───────────────────────────────────────
    all_items: list[str] = []
    for u in real:
        all_items.extend(u.get("itemNames", []))

    return {
        "comp_name": comp_name,
        "comp_group": comp_group,
        "carry_id": carry_id,
        "carry_name": carry_nm,
        "carry_star": carry_st,
        "carry_cost": carry_co,
        "carry_items": json.dumps(carry_it),
        "tank_id": tank_id,
        "tank_name": tank_nm,
        "comp_type": comp_type,
        "all_board_items": json.dumps(all_items),
    }
