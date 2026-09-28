"""Compare observed composition outcomes across ranked player samples.

The final-board metrics are associations, not evidence of in-game decisions.
"""

import json
import logging
from collections import Counter
from typing import Any

import pandas as pd

from tft.analysis.models import ChampInfo, ChampTraits
from tft.analysis.units import (
    _clean_trait_name,
    _dynamic_threshold,
    _is_real_champion,
    _matches_keywords,
    _unit_cost,
)
from tft.config import ANALYSIS_ANTIHEAL_KEYWORDS, ANALYSIS_SHRED_KEYWORDS

log = logging.getLogger(__name__)


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
    if df.empty:
        return pd.DataFrame()
    # ── Dynamic threshold ─────────────────────────────────────────────
    c_total = len(df[df["tier"] == "CHALLENGER"])
    g_total = len(df[df["tier"] == "GRANDMASTER"])
    threshold = _dynamic_threshold(c_total, g_total)
    log.info(
        "Dynamic threshold: %d (from %d Chall / %d GM games).",
        threshold,
        c_total,
        g_total,
    )

    counts = df.groupby(["comp_group", "tier"]).size().unstack(fill_value=0)
    for t in ("CHALLENGER", "GRANDMASTER"):
        if t not in counts.columns:
            counts[t] = 0

    qualified = counts[
        (counts["CHALLENGER"] >= threshold) & (counts["GRANDMASTER"] >= threshold)
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
                has_shred = any(_matches_keywords(i, ANALYSIS_SHRED_KEYWORDS) for i in items)
                has_anti = any(_matches_keywords(i, ANALYSIS_ANTIHEAL_KEYWORDS) for i in items)
                if has_shred and has_anti:
                    util_count += 1

            # ── Cap-Out (unlinked 2★ 5-costs) ────────────────────────
            cap_scores: list[int] = []
            for _, r in tdf.iterrows():
                # Active trait api_names on this board.
                active_apis = {
                    t["name"] for t in json.loads(r["traits_json"]) if t.get("tier_current", 0) >= 1
                }
                # Convert to display names for matching against CDragon.
                active_display = set()
                for api in active_apis:
                    display = tl.get(api, _clean_trait_name(api))
                    active_display.add(display.lower())

                units = json.loads(r["units_json"])
                unlinked = 0
                for u in units:
                    if (
                        _unit_cost(u, cl) == 5
                        and u.get("tier", 1) >= 2
                        and _is_real_champion(u.get("character_id", ""))
                    ):
                        cid = u["character_id"].lower()
                        champ_traits = ct.get(cid, set())
                        # Check overlap: any CDragon trait in active set?
                        shared = any(t.lower() in active_display for t in champ_traits)
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
                    if bailout_placements
                    else None
                ),
                "top4_rate": len(tdf[tdf["placement"] <= 4]) / n if n else 0,
            }

        if "CHALLENGER" not in comp_rows or "GRANDMASTER" not in comp_rows:
            continue

        c = comp_rows["CHALLENGER"]
        g = comp_rows["GRANDMASTER"]

        # ── BIS Deviation using combined top-3 items ──────────────────
        top3 = [item for item, _ in carry_all_items.most_common(3)]
        for tier_key, cr in comp_rows.items():
            tdf = comp_df[(comp_df["tier"] == tier_key) & (comp_df["placement"] <= 4)]
            deviated = 0
            for _, r in tdf.iterrows():
                citems = set(json.loads(r["carry_items"]))
                overlap = len(citems & set(top3))
                if overlap <= 1:
                    deviated += 1
            cr["bis_dev"] = deviated / len(tdf) if len(tdf) else 0

        rows.append(
            {
                "Comp": comp,
                "C Games": c["n"],
                "G Games": g["n"],
                "C Top 4%": f"{c['top4_rate']:.0%}",
                "G Top 4%": f"{g['top4_rate']:.0%}",
                "C Util%": f"{c['util_pct']:.0%}",
                "G Util%": f"{g['util_pct']:.0%}",
                "Δ Util": f"{c['util_pct'] - g['util_pct']:+.0%}",
                "C Cap": round(c["cap_avg"], 2),
                "G Cap": round(g["cap_avg"], 2),
                "Δ Cap": round(c["cap_avg"] - g["cap_avg"], 2),
                "C BIS%": f"{c['bis_dev']:.0%}",
                "G BIS%": f"{g['bis_dev']:.0%}",
                "Δ BIS": f"{c['bis_dev'] - g['bis_dev']:+.0%}",
                "C Bail": round(c["bailout_avg"], 2) if c["bailout_avg"] else "—",
                "G Bail": round(g["bailout_avg"], 2) if g["bailout_avg"] else "—",
                "Δ Bail": (
                    round(c["bailout_avg"] - g["bailout_avg"], 2)
                    if c["bailout_avg"] and g["bailout_avg"]
                    else "—"
                ),
                "_sort": c["util_pct"] - g["util_pct"],
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result.sort_values("_sort", ascending=False, inplace=True)
        result.drop(columns=["_sort"], inplace=True)
    return result
