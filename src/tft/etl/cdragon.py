"""CommunityDragon data fetch and parse pipeline.

Responsibilities:
    - Fetch the full TFT JSON from CDragon.
    - Detect the currently active set.
    - Parse champions, traits, and items into typed model objects.
"""

import json
import logging
import re
from dataclasses import asdict
from typing import Any

import requests

from tft.config import CDRAGON_URL, REQUEST_TIMEOUT_SECONDS
from tft.db.models import ChampionRow, ItemRow, TraitRow
from tft.etl.icons import icon_url

log = logging.getLogger(__name__)

# Mutator suffixes for non-standard game modes — excluded when detecting the
# active set so we get the canonical ranked-play definition.
_SPECIAL_SUFFIXES = re.compile(
    r"_(TURBO|PAIRS|PVEMODE|MacaoMode|CarouselOfChaos)$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_cdragon_data() -> dict[str, Any]:
    """Download the full CDragon TFT JSON and return it as a dict.

    Raises:
        requests.HTTPError: If the request fails (4xx / 5xx).
    """
    log.info("Fetching CDragon TFT data from %s …", CDRAGON_URL)
    resp = requests.get(CDRAGON_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    log.info("Download complete (%d bytes).", len(resp.content))
    return resp.json()


def find_active_set(set_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the standard set entry with the highest set number.

    Special mutators (TURBO, PAIRS, PVEMODE, etc.) are excluded so we get
    the canonical ranked-play definition.

    Args:
        set_data: The ``setData`` list from the CDragon JSON.

    Returns:
        The dict for the active set (contains ``champions``, ``traits``, etc.).
    """
    candidates = [
        s for s in set_data
        if not _SPECIAL_SUFFIXES.search(s.get("mutator", ""))
    ]
    if not candidates:
        candidates = set_data  # fallback

    highest_num = max(s.get("number", 0) for s in candidates)
    same_num = [s for s in candidates if s.get("number", 0) == highest_num]

    # Prefer the shortest mutator string (e.g. "TFTSet16" over "TFTSet16_Evolved")
    best = min(same_num, key=lambda s: len(s.get("mutator", "")))
    return best


def derive_set_prefix(mutator: str, set_number: int) -> str:
    """Turn a mutator like ``TFTSet16`` into the item-prefix ``TFT16``.

    Args:
        mutator: The ``mutator`` field from the active set dict.
        set_number: The ``number`` field from the active set dict.

    Returns:
        A prefix string such as ``"TFT16"`` used to match set-specific items.
    """
    match = re.match(r"(TFTSet\d+)", mutator)
    prefix = match.group(1) if match else f"TFTSet{set_number}"
    return prefix.replace("TFTSet", "TFT")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_champions(champions_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse raw champion dicts into ``ChampionRow`` dicts.

    Filters out units where cost is 0 or missing (target dummies, trait
    props, etc.).

    Args:
        champions_raw: ``champions`` list from the active set.

    Returns:
        List of dicts ready for DB insertion.
    """
    rows: list[dict[str, Any]] = []
    for ch in champions_raw:
        cost = ch.get("cost")
        if not cost or cost <= 0:
            continue

        row = ChampionRow(
            api_name=ch["apiName"],
            name=ch.get("name", ""),
            cost=cost,
            role=ch.get("role"),
            traits=json.dumps(ch.get("traits", []), ensure_ascii=False),
            icon_url=icon_url(ch.get("icon")),
        )
        rows.append(asdict(row))
    return rows


def parse_traits(traits_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse raw trait dicts into ``TraitRow`` dicts.

    Args:
        traits_raw: ``traits`` list from the active set.

    Returns:
        List of dicts ready for DB insertion.
    """
    rows: list[dict[str, Any]] = []
    for tr in traits_raw:
        row = TraitRow(
            api_name=tr["apiName"],
            name=tr.get("name", ""),
            effects=json.dumps(tr.get("effects", []), ensure_ascii=False),
            icon_url=icon_url(tr.get("icon")),
        )
        rows.append(asdict(row))
    return rows


def parse_items(
    all_items: list[dict[str, Any]],
    set_prefix: str,
) -> list[dict[str, Any]]:
    """Parse the global items list and return only relevant items.

    Included:
        * **Base components** — items referenced as ingredients by crafted items.
        * **Standard crafted items** — ``TFT_Item_*`` with exactly 2 components.
        * **Set-specific Emblems** — ``{set_prefix}_Item_*`` with ``Emblem``
          in the name and exactly 2 components.

    Args:
        all_items: The top-level ``items`` list from the CDragon JSON.
        set_prefix: e.g. ``"TFT16"`` — used to find set-specific Emblems.

    Returns:
        List of dicts ready for DB insertion.
    """
    # Standard crafted items
    standard_crafted = [
        i for i in all_items
        if i.get("apiName", "").startswith("TFT_Item_")
        and i.get("composition")
        and len(i["composition"]) == 2
    ]

    # Collect all component apiNames referenced by those crafted items
    component_names: set[str] = set()
    for item in standard_crafted:
        component_names.update(item["composition"])

    base_components = [
        i for i in all_items
        if i.get("apiName") in component_names
    ]

    # Craftable Emblems for this set
    set_emblems = [
        i for i in all_items
        if i.get("apiName", "").startswith(f"{set_prefix}_Item_")
        and "Emblem" in (i.get("name") or "")
        and i.get("composition")
        and len(i["composition"]) == 2
    ]

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for item in base_components + standard_crafted + set_emblems:
        api = item["apiName"]
        if api in seen:
            continue
        seen.add(api)

        row = ItemRow(
            api_name=api,
            name=item.get("name", ""),
            description=item.get("desc") or "",
            icon_url=icon_url(item.get("icon")),
        )
        rows.append(asdict(row))

    return rows
