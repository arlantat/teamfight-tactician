"""Parse Riot match JSON into database-ready row dicts.

Each function accepts raw JSON structures returned by the Riot TFT Match API
and produces dicts whose keys match the corresponding ``schema.sql`` columns.
"""

import json
import logging
from dataclasses import asdict
from typing import Any

from tft.db.models import MatchParticipantRow, MatchRow

log = logging.getLogger(__name__)


def extract_version_prefix(game_version: str) -> str:
    """Extract a comparable version prefix from a full game_version string.

    The Riot ``game_version`` field looks like
    ``"Version 16.6.666.6666"`` — this function returns ``"Version 16.6"``
    so we can compare patches without caring about hotfix numbers.

    Args:
        game_version: Raw game_version string from match JSON.

    Returns:
        A shortened version prefix (e.g. ``"Version 16.6"``).
    """
    parts = game_version.split(".")
    # "Version 16.6.xxx" → ["Version 16", "6", "xxx", ...]
    return ".".join(parts[:2]) if len(parts) >= 2 else game_version


def is_current_version(match_json: dict[str, Any], version_prefix: str) -> bool:
    """Check whether a match belongs to the current game version.

    Args:
        match_json: Full match dict from the Riot API.
        version_prefix: Shortened version prefix to check against.

    Returns:
        ``True`` if the match's game_version starts with *version_prefix*.
    """
    match_version = match_json.get("info", {}).get("game_version", "")
    return extract_version_prefix(match_version) == version_prefix


def parse_match_metadata(match_json: dict[str, Any]) -> dict[str, Any]:
    """Extract the match-level row from a Riot match dict.

    Args:
        match_json: Full match dict from the Riot API.

    Returns:
        A dict ready for insertion into the ``matches`` table.
    """
    info = match_json.get("info", {})
    row = MatchRow(
        match_id=match_json.get("metadata", {}).get("match_id", ""),
        game_version=info.get("game_version", ""),
    )
    return asdict(row)


def parse_match_participants(
    match_json: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract per-player rows from a Riot match dict.

    Args:
        match_json: Full match dict from the Riot API.

    Returns:
        List of dicts ready for insertion into ``match_participants``.
    """
    match_id = match_json.get("metadata", {}).get("match_id", "")
    participants: list[dict[str, Any]] = match_json.get("info", {}).get(
        "participants", [],
    )

    rows: list[dict[str, Any]] = []
    for p in participants:
        row = MatchParticipantRow(
            match_id=match_id,
            puuid=p.get("puuid", ""),
            placement=p.get("placement", 0),
            level=p.get("level", 0),
            gold_left=p.get("gold_left", 0),
            time_eliminated=p.get("time_eliminated", 0.0),
            traits_json=json.dumps(p.get("traits", []), ensure_ascii=False),
            units_json=json.dumps(p.get("units", []), ensure_ascii=False),
            augments_json=json.dumps(p.get("augments", []), ensure_ascii=False),
        )
        rows.append(asdict(row))

    return rows
