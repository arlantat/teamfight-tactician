"""Fetch CommunityDragon TFT snapshots and parse their active champion roster."""

import json
import logging
import re
from typing import Any

import requests

from tft.config import CDRAGON_URL, REQUEST_TIMEOUT_SECONDS
from tft.db.models import ChampionRow, TraitRow
from tft.etl.icons import icon_url
from tft.etl.items import parse_augments, parse_items

log = logging.getLogger(__name__)

# Keep parser imports available from the original public module.
__all__ = [
    "derive_set_prefix",
    "fetch_cdragon_data",
    "find_active_set",
    "find_set",
    "parse_augments",
    "parse_champions",
    "parse_items",
    "parse_traits",
]
_SPECIAL_SUFFIXES = re.compile(
    r"_(TURBO|PAIRS|PVEMODE|MacaoMode|CarouselOfChaos)$",
    re.IGNORECASE,
)


def fetch_cdragon_data() -> dict[str, Any]:
    """Download the current English TFT snapshot, raising on HTTP failure."""
    log.info("Fetching TFT data from %s", CDRAGON_URL)
    response = requests.get(CDRAGON_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("setData"), list):
        raise ValueError("CDragon response has no setData list")
    log.info("Downloaded %d bytes of TFT data", len(response.content))
    return data


def find_active_set(set_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the highest numbered standard set, preferring its canonical mutator."""
    if not set_data:
        raise ValueError("CDragon contains no sets")
    candidates = [
        entry for entry in set_data if not _SPECIAL_SUFFIXES.search(entry.get("mutator", ""))
    ]
    candidates = candidates or set_data
    number = max(entry.get("number", 0) for entry in candidates)
    return find_set(candidates, number)


def find_set(set_data: list[dict[str, Any]], set_number: int) -> dict[str, Any]:
    """Select a numbered set without silently falling back to another release."""
    candidates = [entry for entry in set_data if entry.get("number") == set_number]
    if not candidates:
        raise ValueError(f"Set {set_number} is unavailable in this CDragon snapshot")
    canonical = f"TFTSet{set_number}"
    return min(
        candidates,
        key=lambda entry: (
            entry.get("mutator") != canonical,
            bool(_SPECIAL_SUFFIXES.search(entry.get("mutator", ""))),
            len(entry.get("mutator", "")),
        ),
    )


def derive_set_prefix(mutator: str, set_number: int) -> str:
    """Return a legacy TFT item prefix; current selection uses explicit set IDs."""
    match = re.match(r"TFTSet(\d+)", mutator)
    return f"TFT{match.group(1) if match else set_number}"


def parse_champions(champions_raw: list[dict[str, Any]]) -> list[ChampionRow]:
    """Preserve playable champions and variants, excluding traitless PvE units.

    Set 18 uses DA_18 and other DA_* identifiers, so an API-name prefix is
    deliberately not used as a roster filter. Trait membership distinguishes
    playable Riftbeasts from ordinary neutral monsters and summoned props.
    """
    rows: list[ChampionRow] = []
    seen: set[str] = set()
    for champion in champions_raw:
        cost = champion.get("cost")
        if not cost or cost <= 0 or not champion.get("traits"):
            continue
        api_name = champion["apiName"]
        if api_name in seen:
            continue
        seen.add(api_name)
        ability = champion.get("ability") or {}
        square = icon_url(champion.get("squareIcon"))
        tile = icon_url(champion.get("tileIcon"))
        splash = icon_url(champion.get("icon")) or square or tile
        rows.append(
            ChampionRow(
                api_name=api_name,
                name=champion.get("name") or api_name,
                cost=int(cost),
                role=champion.get("role"),
                traits=json.dumps(champion["traits"], ensure_ascii=False),
                icon_url=splash,
                square_icon_url=square or tile or splash,
                ability_name=ability.get("name") or "",
                ability_description=ability.get("desc") or "",
                ability_icon_url=icon_url(ability.get("icon")),
                ability_variables=json.dumps(ability.get("variables") or [], ensure_ascii=False),
                stats=json.dumps(champion.get("stats") or {}, ensure_ascii=False),
            )
        )
    return rows


def parse_traits(traits_raw: list[dict[str, Any]]) -> list[TraitRow]:
    """Parse trait descriptions, breakpoint effects, and icons into typed rows."""
    return [
        TraitRow(
            api_name=trait["apiName"],
            name=trait.get("name") or trait["apiName"],
            effects=json.dumps(trait.get("effects") or [], ensure_ascii=False),
            icon_url=icon_url(trait.get("icon")),
            description=trait.get("desc") or "",
        )
        for trait in traits_raw
    ]
