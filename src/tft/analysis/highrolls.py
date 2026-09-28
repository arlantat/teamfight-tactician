"""Summarize observed three-star four- and five-cost champion boards."""

import json
import logging
from typing import Any

import pandas as pd

from tft.analysis.models import ChampInfo
from tft.analysis.units import _is_real_champion, _unit_cost, _unit_name
from tft.config import ANALYSIS_TIERS, STAR_TO_COPIES

log = logging.getLogger(__name__)


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
    if df.empty:
        return pd.DataFrame()
    for _, row in df.iterrows():
        if row["tier"] not in ANALYSIS_TIERS:
            continue
        for u in json.loads(row["units_json"]):
            cid = u.get("character_id", "")
            cost = _unit_cost(u, cl)
            if cost in {4, 5} and u.get("tier") == 3 and _is_real_champion(cid):
                exodia_rows.append(
                    {
                        "match_id": row["match_id"],
                        "puuid": row["puuid"],
                        "tier": row["tier"],
                        "placement": row["placement"],
                        "exodia_id": cid,
                        "exodia_cost": cost,
                        "units_json": row["units_json"],
                    }
                )
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
                if lu.get("character_id", "").lower() == uid.lower():
                    copies += STAR_TO_COPIES.get(lu.get("tier", 1), 1)

        # Desperation — are ALL other real units 1★?
        others = [
            u
            for u in json.loads(er["units_json"])
            if u.get("character_id") != uid and _is_real_champion(u.get("character_id", ""))
        ]
        desperate = all(u.get("tier", 1) == 1 for u in others) if others else False

        metrics.append(
            {
                "tier": er["tier"],
                "placement": er["placement"],
                "name": _unit_name({"character_id": uid}, cl),
                "cost": er["exodia_cost"],
                "lobby_copies": copies,
                "desperate": desperate,
            }
        )

    mdf = pd.DataFrame(metrics)

    # ── Aggregate by tier ─────────────────────────────────────────────
    rows: list[dict[str, Any]] = []
    for tier, total in [("CHALLENGER", total_c), ("GRANDMASTER", total_g)]:
        td = mdf[mdf["tier"] == tier]
        if td.empty:
            continue
        rows.append(
            {
                "Tier": tier[:5],
                "Exodia Games": len(td),
                "Freq %": f"{len(td) / total:.1%}" if total else "—",
                "Avg Place": round(td["placement"].mean(), 2),
                "Avg Lobby Copies": round(td["lobby_copies"].mean(), 2),
                "Other 1★%": f"{td['desperate'].mean():.0%}",
            }
        )

    # Delta row.
    c_freq = len(mdf[mdf["tier"] == "CHALLENGER"]) / total_c if total_c else 0
    g_freq = len(mdf[mdf["tier"] == "GRANDMASTER"]) / total_g if total_g else 0
    rows.append(
        {
            "Tier": "Δ",
            "Exodia Games": "",
            "Freq %": f"{c_freq - g_freq:+.1%}",
            "Avg Place": "",
            "Avg Lobby Copies": "",
            "Other 1★%": "",
        }
    )

    return pd.DataFrame(rows)
