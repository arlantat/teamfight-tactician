"""Delta Engine v2 — Advanced Challenger vs Grandmaster skill-gap analysis.

Replaces the original simplistic analysis with investment-score-based
composition classification, Exodia (3★ 4/5-cost) spot detection, and
deep behavioral delta metrics (utility uptime, cap-out, BIS deviation,
bailout floor).

Usage (via the thin wrapper script)::

    .venv/bin/python scripts/delta_engine.py
"""

import json
import logging
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from tabulate import tabulate

from tft.config import DB_PATH

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Riot ``rarity`` field → TFT cost tier.
RARITY_TO_COST: dict[int, int] = {0: 1, 1: 2, 2: 3, 4: 4, 6: 5, 7: 6, 9: 11}

# Star level → pool copies consumed.
STAR_TO_COPIES: dict[int, int] = {1: 1, 2: 3, 3: 9}

# CDragon roles split by archetype.
DAMAGE_ROLES: frozenset[str] = frozenset({
    "ADCarry", "ADCaster", "ADCasterFormSwapper", "ADFighter",
    "ADReaper", "ADSpecialist", "APCarry", "APCaster",
    "APFighter", "APReaper", "APSpecialist", "HFighter",
})
DEFENSIVE_ROLES: frozenset[str] = frozenset({"ADTank", "APTank"})

# Base components (excluded from "completed item" count).
_COMPONENT_ITEMS: frozenset[str] = frozenset({
    "TFT_Item_BFSword", "TFT_Item_ChainVest", "TFT_Item_GiantsBelt",
    "TFT_Item_NeedlesslyLargeRod", "TFT_Item_NegatronCloak",
    "TFT_Item_RecurveBow", "TFT_Item_SparringGloves",
    "TFT_Item_Spatula", "TFT_Item_TearOfTheGoddess", "TFT_Item_FryingPan",
})

# Resistance-reduction (shred/sunder) item keywords (matched case-insensitive).
_SHRED_KEYWORDS: frozenset[str] = frozenset({
    "ionicspark", "statikkshiv", "spectralgauntlet", "lastwhisper",
})

# Anti-heal (Grievous Wounds) item keywords.
_ANTIHEAL_KEYWORDS: frozenset[str] = frozenset({
    "redbuff", "morellonomicon", "rapidfirecannon",
})

# Summoned units — not real champions.
_SUMMON_KEYWORDS: frozenset[str] = frozenset({
    "Tibbers", "Voidling", "Soldier", "Prop", "Chest",
    "ArmoryKey", "FreljordProp",
})

# Unique passives — not real team synergies.
_UNIQUE_TRAIT_KEYWORDS: frozenset[str] = frozenset({
    "Unique", "Teamup", "TheBoss", "DarkChild", "RuneMage",
    "Soulbound", "HexMech", "Caretaker", "Emperor",
})

# Dynamic threshold bounds.
_THRESHOLD_DIVISOR: int = 50
_THRESHOLD_FLOOR: int = 10
_THRESHOLD_CAP: int = 75

# Default report output path (relative to project root).
REPORT_FILENAME: str = "delta_report.md"

# Type alias for champion lookup entries.
ChampInfo = tuple[str, int, str | None]  # (display_name, cost, role)

# Pre-built champion CDragon traits: {api_name_lower: set[display_trait_names]}.
ChampTraits = dict[str, set[str]]


# ---------------------------------------------------------------------------
# Lookup builders
# ---------------------------------------------------------------------------

def _build_champion_lookup(conn: sqlite3.Connection) -> dict[str, ChampInfo]:
    """Build ``{api_name: (name, cost, role)}`` with case-insensitive keys.

    Args:
        conn: Open SQLite connection.

    Returns:
        Case-insensitive dict mapping champion api_name to info tuple.
    """
    rows = conn.execute(
        "SELECT api_name, name, cost, role FROM champions",
    ).fetchall()
    lookup: dict[str, ChampInfo] = {}
    for r in rows:
        entry: ChampInfo = (r["name"].strip(), r["cost"], r["role"])
        lookup[r["api_name"]] = entry
        lookup[r["api_name"].lower()] = entry
    return lookup


def _build_trait_lookup(conn: sqlite3.Connection) -> dict[str, str]:
    """Build ``{api_name: display_name}`` for traits."""
    rows = conn.execute("SELECT api_name, name FROM traits").fetchall()
    return {r["api_name"]: r["name"] for r in rows}


def _build_champ_traits_lookup(conn: sqlite3.Connection) -> ChampTraits:
    """Build ``{api_name_lower: set[display_trait_names]}`` for champions.

    Used by the Cap-Out metric to check if a 5-cost shares any active trait
    with the rest of the composition.
    """
    rows = conn.execute("SELECT api_name, traits FROM champions").fetchall()
    lookup: ChampTraits = {}
    for r in rows:
        trait_set = set(json.loads(r["traits"]))
        lookup[r["api_name"].lower()] = trait_set
    return lookup


def _build_item_lookup(conn: sqlite3.Connection) -> dict[str, str]:
    """Build ``{api_name: display_name}`` for items."""
    rows = conn.execute("SELECT api_name, name FROM items").fetchall()
    return {r["api_name"]: r["name"] for r in rows}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_team_trait(name: str) -> bool:
    """True if the trait api_name is a shared team synergy."""
    return not any(kw in name for kw in _UNIQUE_TRAIT_KEYWORDS)


def _is_real_champion(cid: str) -> bool:
    """True if the character_id is a playable champion, not a summon."""
    return not any(kw in cid for kw in _SUMMON_KEYWORDS)


def _clean_trait_name(api: str) -> str:
    """Strip set prefix: ``TFT16_Ionia`` → ``Ionia``."""
    parts = api.split("_", 1)
    return parts[1] if len(parts) > 1 else api


def _completed_item_count(item_names: list[str]) -> int:
    """Count non-component items on a unit."""
    return sum(1 for i in item_names if i not in _COMPONENT_ITEMS)


def _unit_cost(u: dict, cl: dict[str, ChampInfo]) -> int:
    """Get cost from champion lookup, falling back to rarity mapping."""
    info = cl.get(u.get("character_id", "")) or cl.get(
        u.get("character_id", "").lower(),
    )
    return info[1] if info else RARITY_TO_COST.get(u.get("rarity", 0), 0)


def _unit_role(u: dict, cl: dict[str, ChampInfo]) -> str | None:
    """Get CDragon role from champion lookup."""
    info = cl.get(u.get("character_id", "")) or cl.get(
        u.get("character_id", "").lower(),
    )
    return info[2] if info else None


def _unit_name(u: dict, cl: dict[str, ChampInfo]) -> str:
    """Get display name from champion lookup."""
    info = cl.get(u.get("character_id", "")) or cl.get(
        u.get("character_id", "").lower(),
    )
    return info[0] if info else u.get("character_id", "?")


def _matches_keywords(item: str, kws: frozenset[str]) -> bool:
    """Case-insensitive substring match against keyword set."""
    low = item.lower()
    return any(kw in low for kw in kws)


def _dynamic_threshold(chall_n: int, gm_n: int) -> int:
    """Scale minimum-games threshold with dataset size.

    Uses ``min(chall, gm) // 20``, floored at 10 and capped at 100.
    """
    return max(_THRESHOLD_FLOOR, min(_THRESHOLD_CAP, min(chall_n, gm_n) // _THRESHOLD_DIVISOR))


# ---------------------------------------------------------------------------
# Task 1 — Advanced Composition Classifier
# ---------------------------------------------------------------------------

def classify_comp_v2(
    row: pd.Series,
    cl: dict[str, ChampInfo],
    tl: dict[str, str],
) -> dict[str, Any]:
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
    units: list[dict] = json.loads(row["units_json"])
    traits: list[dict] = json.loads(row["traits_json"])
    real = [u for u in units if _is_real_champion(u.get("character_id", ""))]

    # ── Score itemised units (≥2 completed items) ─────────────────────
    scored: list[tuple[dict, int, str | None]] = []
    for u in real:
        if _completed_item_count(u.get("itemNames", [])) >= 2:
            star = u.get("tier", 1)
            score = (star * 10) + _unit_cost(u, cl)
            scored.append((u, score, _unit_role(u, cl)))

    # Fall back to all real units if nobody qualifies.
    if not scored:
        for u in real:
            star = u.get("tier", 1)
            score = (star * 10) + _unit_cost(u, cl)
            scored.append((u, score, _unit_role(u, cl)))

    # ── Carry & Tank ──────────────────────────────────────────────────
    dmg = [(u, s) for u, s, r in scored if r in DAMAGE_ROLES]
    tnk = [(u, s) for u, s, r in scored if r in DEFENSIVE_ROLES]

    carry_u = max(dmg, key=lambda x: x[1])[0] if dmg else (
        max(scored, key=lambda x: x[1])[0] if scored else None
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
        t for t in traits
        if t.get("tier_current", 0) >= 1 and _is_team_trait(t.get("name", ""))
    ]
    if active:
        best = max(active, key=lambda t: (
            t.get("tier_current", 0), t.get("num_units", 0), t.get("style", 0),
        ))
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
        "comp_name": comp_name, "comp_group": comp_group,
        "carry_id": carry_id,
        "carry_name": carry_nm, "carry_star": carry_st,
        "carry_cost": carry_co, "carry_items": json.dumps(carry_it),
        "tank_id": tank_id, "tank_name": tank_nm,
        "comp_type": comp_type, "all_board_items": json.dumps(all_items),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(db_path: Path | None = None) -> pd.DataFrame:
    """Load match_participants joined with players and matches.

    Args:
        db_path: Override for the database file path.

    Returns:
        DataFrame with all participant, player-tier, and match columns.
    """
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    query = """
        SELECT mp.match_id, mp.puuid, mp.placement, mp.level, mp.gold_left,
               mp.time_eliminated, mp.traits_json, mp.units_json,
               mp.augments_json, p.tier, m.game_version
        FROM match_participants mp
        JOIN players p ON mp.puuid = p.puuid
        JOIN matches m ON mp.match_id = m.match_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    log.info("Loaded %d participant rows from %s", len(df), db_path.name)
    return df


# ---------------------------------------------------------------------------
# Task 2 — Exodia Report (3★ 4/5-cost)
# ---------------------------------------------------------------------------

def compute_exodia_report(
    df: pd.DataFrame,
    cl: dict[str, ChampInfo],
) -> pd.DataFrame:
    """Analyse games where a player hit a 3★ 4-cost or 5-cost unit.

    Metrics per tier: frequency, average placement, lobby pool proxy
    (copies held by other 7 players), and desperation index (all other
    units at 1★).

    Args:
        df: Enriched DataFrame (post-classification).
        cl: Champion lookup.

    Returns:
        Summary DataFrame with one row per tier plus a delta row.
        Empty DataFrame if no Exodia games exist.
    """
    # ── Identify Exodia games ─────────────────────────────────────────
    exodia_rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        for u in json.loads(row["units_json"]):
            cid = u.get("character_id", "")
            cost = RARITY_TO_COST.get(u.get("rarity", 0), 0)
            if cost >= 4 and u.get("tier") == 3 and _is_real_champion(cid):
                exodia_rows.append({
                    "match_id": row["match_id"], "puuid": row["puuid"],
                    "tier": row["tier"], "placement": row["placement"],
                    "exodia_id": cid, "exodia_cost": cost,
                    "units_json": row["units_json"],
                })
                break  # one exodia unit per game

    if not exodia_rows:
        log.warning("No 3★ 4/5-cost games found.")
        return pd.DataFrame()

    edf = pd.DataFrame(exodia_rows)
    log.info("Found %d Exodia games.", len(edf))

    total_c = len(df[df["tier"] == "CHALLENGER"])
    total_g = len(df[df["tier"] == "GRANDMASTER"])

    # ── Per-game metrics ──────────────────────────────────────────────
    metrics: list[dict[str, Any]] = []
    for _, er in edf.iterrows():
        uid = er["exodia_id"]

        # Lobby Pool Proxy — copies of the unit across other 7 boards.
        lobby = df[(df["match_id"] == er["match_id"]) & (df["puuid"] != er["puuid"])]
        copies = 0
        for _, lr in lobby.iterrows():
            for lu in json.loads(lr["units_json"]):
                if lu.get("character_id") == uid:
                    copies += STAR_TO_COPIES.get(lu.get("tier", 1), 1)

        # Desperation — are ALL other real units 1★?
        others = [
            u for u in json.loads(er["units_json"])
            if u.get("character_id") != uid and _is_real_champion(u.get("character_id", ""))
        ]
        desperate = all(u.get("tier", 1) == 1 for u in others) if others else False

        metrics.append({
            "tier": er["tier"], "placement": er["placement"],
            "name": _unit_name({"character_id": uid}, cl),
            "cost": er["exodia_cost"],
            "lobby_copies": copies, "desperate": desperate,
        })

    mdf = pd.DataFrame(metrics)

    # ── Aggregate by tier ─────────────────────────────────────────────
    rows: list[dict[str, Any]] = []
    for tier, total in [("CHALLENGER", total_c), ("GRANDMASTER", total_g)]:
        td = mdf[mdf["tier"] == tier]
        if td.empty:
            continue
        rows.append({
            "Tier": tier[:5],
            "Exodia Games": len(td),
            "Freq %": f"{len(td) / total:.1%}" if total else "—",
            "Avg Place": round(td["placement"].mean(), 2),
            "Avg Lobby Copies": round(td["lobby_copies"].mean(), 2),
            "Desperation %": f"{td['desperate'].mean():.0%}",
        })

    # Delta row.
    c_freq = len(mdf[mdf["tier"] == "CHALLENGER"]) / total_c if total_c else 0
    g_freq = len(mdf[mdf["tier"] == "GRANDMASTER"]) / total_g if total_g else 0
    rows.append({
        "Tier": "Δ", "Exodia Games": "",
        "Freq %": f"{c_freq - g_freq:+.1%}",
        "Avg Place": "", "Avg Lobby Copies": "", "Desperation %": "",
    })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Task 3 — Deep Behavioral Deltas
# ---------------------------------------------------------------------------

def compute_behavioral_deltas(
    df: pd.DataFrame,
    cl: dict[str, ChampInfo],
    il: dict[str, str],
    ct: ChampTraits | None = None,
    tl: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Compute per-comp behavioral metrics for qualifying compositions.

    Metrics:
    * **Utility_Uptime** — % of games with ≥1 shred AND ≥1 anti-heal item.
    * **Cap_Out** — avg count of 2★ 5-costs sharing zero active traits.
    * **BIS_Deviation** — % of top-4 games with ≤1 of the carry's top-3 items.
    * **Bailout_Floor** — avg placement when carry ended 1★ (Standard only).

    Args:
        df: Enriched DataFrame (post-classification).
        cl: Champion lookup.
        il: Item lookup (for display names).
        ct: Champion traits lookup (for Cap-Out).
        tl: Trait lookup (for Cap-Out reverse mapping).

    Returns:
        DataFrame with one row per qualifying composition.
    """
    ct = ct or {}
    tl = tl or {}
    # Build reverse trait mapping: display_name_lower → api_name
    # so we can match CDragon traits against active trait api_names.
    trait_display_to_api: dict[str, str] = {
        v.lower(): k for k, v in tl.items()
    }
    # ── Dynamic threshold ─────────────────────────────────────────────
    c_total = len(df[df["tier"] == "CHALLENGER"])
    g_total = len(df[df["tier"] == "GRANDMASTER"])
    threshold = _dynamic_threshold(c_total, g_total)
    log.info(
        "Dynamic threshold: %d (from %d Chall / %d GM games).",
        threshold, c_total, g_total,
    )

    counts = df.groupby(["comp_group", "tier"]).size().unstack(fill_value=0)
    for t in ("CHALLENGER", "GRANDMASTER"):
        if t not in counts.columns:
            counts[t] = 0

    qualified = counts[
        (counts["CHALLENGER"] >= threshold)
        & (counts["GRANDMASTER"] >= threshold)
    ].index.tolist()

    log.info("%d comps qualify at threshold %d.", len(qualified), threshold)
    if not qualified:
        log.warning("No comps meet threshold. Returning empty.")
        return pd.DataFrame()

    # ── Per-comp × tier metrics ───────────────────────────────────────
    rows: list[dict[str, Any]] = []
    for comp in qualified:
        comp_df = df[df["comp_group"] == comp]
        comp_rows: dict[str, dict[str, Any]] = {}
        carry_all_items: Counter[str] = Counter()

        for tier in ("CHALLENGER", "GRANDMASTER"):
            tdf = comp_df[comp_df["tier"] == tier]
            if tdf.empty:
                continue
            n = len(tdf)

            # ── Utility Uptime ────────────────────────────────────────
            util_count = 0
            for _, r in tdf.iterrows():
                items = json.loads(r["all_board_items"])
                has_shred = any(_matches_keywords(i, _SHRED_KEYWORDS) for i in items)
                has_anti = any(_matches_keywords(i, _ANTIHEAL_KEYWORDS) for i in items)
                if has_shred and has_anti:
                    util_count += 1

            # ── Cap-Out (unlinked 2★ 5-costs) ────────────────────────
            cap_scores: list[int] = []
            for _, r in tdf.iterrows():
                # Active trait api_names on this board.
                active_apis = {
                    t["name"]
                    for t in json.loads(r["traits_json"])
                    if t.get("tier_current", 0) >= 1
                }
                # Convert to display names for matching against CDragon.
                active_display = set()
                for api in active_apis:
                    display = tl.get(api, _clean_trait_name(api))
                    active_display.add(display.lower())

                units = json.loads(r["units_json"])
                unlinked = 0
                for u in units:
                    if (RARITY_TO_COST.get(u.get("rarity", 0), 0) == 5
                            and u.get("tier", 1) >= 2
                            and _is_real_champion(u.get("character_id", ""))):
                        cid = u["character_id"].lower()
                        champ_traits = ct.get(cid, set())
                        # Check overlap: any CDragon trait in active set?
                        shared = any(
                            t.lower() in active_display for t in champ_traits
                        )
                        if not shared:
                            unlinked += 1
                cap_scores.append(unlinked)

            # ── BIS Deviation (Top-4 games) ───────────────────────────
            # Collect carry items for this tier.
            tier_carry_items: Counter[str] = Counter()
            for _, r in tdf.iterrows():
                tier_carry_items.update(json.loads(r["carry_items"]))
            carry_all_items.update(tier_carry_items)

            # ── Bailout Floor (1★ carry in Standard comps) ────────────
            bailout_placements: list[int] = []
            if "(Standard)" in comp:
                for _, r in tdf.iterrows():
                    if r["carry_star"] == 1:
                        bailout_placements.append(r["placement"])

            comp_rows[tier] = {
                "n": n,
                "util_pct": util_count / n if n else 0,
                "cap_avg": sum(cap_scores) / n if n else 0,
                "top4_n": len(tdf[tdf["placement"] <= 4]),
                "bailout_avg": (
                    sum(bailout_placements) / len(bailout_placements)
                    if bailout_placements else None
                ),
                "win_rate": len(tdf[tdf["placement"] <= 4]) / n if n else 0,
            }

        if "CHALLENGER" not in comp_rows or "GRANDMASTER" not in comp_rows:
            continue

        c = comp_rows["CHALLENGER"]
        g = comp_rows["GRANDMASTER"]

        # ── BIS Deviation using combined top-3 items ──────────────────
        top3 = [item for item, _ in carry_all_items.most_common(3)]
        for tier_key, cr in comp_rows.items():
            tdf = comp_df[
                (comp_df["tier"] == tier_key) & (comp_df["placement"] <= 4)
            ]
            deviated = 0
            for _, r in tdf.iterrows():
                citems = set(json.loads(r["carry_items"]))
                overlap = len(citems & set(top3))
                if overlap <= 1:
                    deviated += 1
            cr["bis_dev"] = deviated / len(tdf) if len(tdf) else 0

        rows.append({
            "Comp": comp,
            "C Games": c["n"], "G Games": g["n"],
            "C WR%": f"{c['win_rate']:.0%}", "G WR%": f"{g['win_rate']:.0%}",
            "C Util%": f"{c['util_pct']:.0%}",
            "G Util%": f"{g['util_pct']:.0%}",
            "Δ Util": f"{c['util_pct'] - g['util_pct']:+.0%}",
            "C Cap": round(c["cap_avg"], 2), "G Cap": round(g["cap_avg"], 2),
            "Δ Cap": round(c["cap_avg"] - g["cap_avg"], 2),
            "C BIS%": f"{c['bis_dev']:.0%}", "G BIS%": f"{g['bis_dev']:.0%}",
            "Δ BIS": f"{c['bis_dev'] - g['bis_dev']:+.0%}",
            "C Bail": round(c["bailout_avg"], 2) if c["bailout_avg"] else "—",
            "G Bail": round(g["bailout_avg"], 2) if g["bailout_avg"] else "—",
            "Δ Bail": (
                round(c["bailout_avg"] - g["bailout_avg"], 2)
                if c["bailout_avg"] and g["bailout_avg"] else "—"
            ),
            "_sort": c["util_pct"] - g["util_pct"],
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result.sort_values("_sort", ascending=False, inplace=True)
        result.drop(columns=["_sort"], inplace=True)
    return result


# ---------------------------------------------------------------------------
# Task 4 — Report Output
# ---------------------------------------------------------------------------

def _build_comp_popularity(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Build a comp-popularity table with per-tier play-rate percentages.

    Args:
        df: Enriched DataFrame (post-classification).

    Returns:
        DataFrame with comp_group, Challenger %, Grandmaster %, and Total %.
    """
    total_c = len(df[df["tier"] == "CHALLENGER"])
    total_g = len(df[df["tier"] == "GRANDMASTER"])
    total_all = len(df)

    counts = df.groupby(["comp_group", "tier"]).size().unstack(fill_value=0)
    for t in ("CHALLENGER", "GRANDMASTER"):
        if t not in counts.columns:
            counts[t] = 0

    pop = pd.DataFrame({
        "Comp": counts.index,
        "C Games": counts["CHALLENGER"].values,
        "C %": [f"{v / total_c:.1%}" if total_c else "—" for v in counts["CHALLENGER"]],
        "G Games": counts["GRANDMASTER"].values,
        "G %": [f"{v / total_g:.1%}" if total_g else "—" for v in counts["GRANDMASTER"]],
        "Total": (counts["CHALLENGER"] + counts["GRANDMASTER"]).values,
        "Total %": [
            f"{v / total_all:.1%}" if total_all else "—"
            for v in counts["CHALLENGER"] + counts["GRANDMASTER"]
        ],
    })
    pop.sort_values("Total", ascending=False, inplace=True)
    return pop.head(20)


def format_report(
    behavioral_df: pd.DataFrame,
    exodia_df: pd.DataFrame,
    popularity_df: pd.DataFrame,
) -> str:
    """Build the full analysis report as a Markdown string.

    Args:
        behavioral_df: Deep behavioral deltas per comp.
        exodia_df: Exodia (3★ 4/5-cost) summary.
        popularity_df: Comp popularity by tier.

    Returns:
        The complete report as a Markdown-formatted string.
    """
    sep = "═" * 78
    lines: list[str] = []
    out = lines.append

    out(f"\n{sep}")
    out("  TFT DELTA ENGINE v2 — Advanced Challenger vs GM Skill-Gap Report")
    out(f"{sep}\n")

    # ── Comp Popularity ───────────────────────────────────────────────
    out("## Composition Popularity (Top 20 by play-rate)\n")
    out("C=Challenger, G=Grandmaster. Percentages are share of that tier's total games.\n")
    out(tabulate(
        popularity_df, headers="keys", tablefmt="github", showindex=False,
    ))

    # ── Table 1: Deep Analytics ───────────────────────────────────────
    out(f"\n{sep}")
    out("## Table 1 — Deep Behavioral Deltas (sorted by Utility Uptime Δ)\n")
    out("**Key**: C=Challenger, G=Grandmaster, Δ=C−G")
    out("  Util%=Shred+AntiHeal uptime, Cap=Unlinked 2★ 5-costs,")
    out("  BIS%=Top-4 games with ≤1 best items, Bail=Avg place when carry 1★\n")

    if behavioral_df.empty:
        out("_No comps met the dynamic threshold in both tiers._\n")
    else:
        out(tabulate(
            behavioral_df, headers="keys", tablefmt="github", showindex=False,
        ))

    # ── Table 2: Exodia Report ────────────────────────────────────────
    out(f"\n{sep}")
    out("## Table 2 — Exodia Report (3★ 4-cost / 5-cost Highrolls)\n")
    out("**Lobby Copies** = copies of the 3★ unit held by other 7 players")
    out("  (lower = more uncontested).")
    out("**Desperation%** = games where all OTHER units were 1★")
    out("  (sold entire board to hit 3★).\n")

    if exodia_df.empty:
        out("_No 3★ 4/5-cost games found in dataset._\n")
    else:
        out(tabulate(
            exodia_df, headers="keys", tablefmt="github", showindex=False,
        ))

    out(f"\n{sep}")
    out("  Analysis complete ✓")
    out(f"{sep}\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(db_path: Path | None = None) -> None:
    """Execute the full delta-engine v2 pipeline end-to-end.

    Args:
        db_path: Optional override for the database path.
    """
    from tft.config import PROJECT_ROOT

    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cl = _build_champion_lookup(conn)
        tl = _build_trait_lookup(conn)
        il = _build_item_lookup(conn)
        ct = _build_champ_traits_lookup(conn)
    finally:
        conn.close()

    # Load & classify.
    df = load_data(db_path)

    log.info("Classifying compositions (v2)…")
    enriched = df.apply(lambda r: classify_comp_v2(r, cl, tl), axis=1)
    enriched_df = pd.DataFrame(enriched.tolist())
    df = pd.concat([df, enriched_df], axis=1)

    log.info("Comp groups (for matching):\n%s",
             df["comp_group"].value_counts().head(15).to_string())

    # Analyses.
    popularity_df = _build_comp_popularity(df)
    exodia_df = compute_exodia_report(df, cl)
    behavioral_df = compute_behavioral_deltas(df, cl, il, ct=ct, tl=tl)

    # Build and print report.
    report = format_report(behavioral_df, exodia_df, popularity_df)
    print(report)

    # Write to file.
    report_path = PROJECT_ROOT / REPORT_FILENAME
    report_path.write_text(report, encoding="utf-8")
    log.info("Report written to %s", report_path)
