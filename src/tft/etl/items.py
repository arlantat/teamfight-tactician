"""Select set-scoped items and augments from CommunityDragon's shared catalog."""

import json
import re
from collections.abc import Collection
from typing import Any

from tft.config import CDRAGON_SUPPORT_ITEM_TAG
from tft.db.models import AugmentRow, ItemRow
from tft.etl.icons import icon_url

_TIER_NAMES = {1: "silver", 2: "gold", 3: "prismatic"}
_ROMAN_TIERS = {"i": "silver", "ii": "gold", "iii": "prismatic"}


def _select_entries(
    all_items: list[dict[str, Any]],
    active_ids: Collection[str],
) -> list[dict[str, Any]]:
    """Resolve explicit membership and reject incomplete source snapshots."""
    if isinstance(active_ids, str):
        raise TypeError("Use the active set's item/augment ID list, not a set prefix")
    by_id = {item["apiName"]: item for item in all_items}
    missing = set(active_ids) - by_id.keys()
    if missing:
        raise ValueError(
            f"CDragon catalog is missing {len(missing)} selected IDs: {sorted(missing)[:5]}"
        )
    return [by_id[api_name] for api_name in sorted(set(active_ids))]


def item_category(item: dict[str, Any]) -> str:
    """Classify source equipment while preserving internal rewards as special."""
    api_name = item["apiName"].lower()
    name = (item.get("name") or "").lower()
    tags = {str(tag).lower() for tag in item.get("tags") or []}
    if "_assist_" in api_name or "armory" in api_name:
        return "special"
    if "consumable" in tags or "consumable" in api_name:
        return "consumable"
    if "component" in tags:
        return "component"
    if item.get("associatedTraits") or "emblem" in name:
        return "emblem"
    if CDRAGON_SUPPORT_ITEM_TAG in tags:
        return "support"
    if "artifact" in api_name or "_ornn" in api_name:
        return "artifact"
    if name.startswith("radiant ") or "radiant" in api_name:
        return "radiant"
    if "support" in api_name:
        return "support"
    if len(item.get("composition") or []) == 2:
        return "completed"
    return "special"


def parse_items(
    all_items: list[dict[str, Any]],
    active_item_ids: Collection[str],
) -> list[ItemRow]:
    """Parse exactly the current set's item IDs, retaining recipes and effects."""
    rows: list[ItemRow] = []
    for item in _select_entries(all_items, active_item_ids):
        if item.get("isAugment"):
            continue
        rows.append(
            ItemRow(
                api_name=item["apiName"],
                name=item.get("name") or item["apiName"],
                description=item.get("desc") or "",
                icon_url=icon_url(item.get("icon")),
                composition=json.dumps(item.get("composition") or [], ensure_ascii=False),
                effects=json.dumps(item.get("effects") or {}, ensure_ascii=False),
                category=item_category(item),
            )
        )
    return rows


def augment_tier(item: dict[str, Any]) -> str:
    """Use explicit source tier or its asset suffix; leave unknown values honest."""
    tier = item.get("tier")
    if tier in _TIER_NAMES:
        return _TIER_NAMES[tier]
    if isinstance(tier, str) and tier.lower() in _TIER_NAMES.values():
        return tier.lower()
    path = item.get("icon") or ""
    match = re.search(r"(?:_|-)(iii|ii|i)(?:\.[^/]*)?$", path, re.IGNORECASE)
    if match:
        return _ROMAN_TIERS[match.group(1).lower()]
    match = re.search(r"([123])(?:\.(?:tex|dds|png))$", path, re.IGNORECASE)
    return _TIER_NAMES[int(match.group(1))] if match else "unknown"


def parse_augments(
    all_items: list[dict[str, Any]],
    active_augment_ids: Collection[str],
) -> list[AugmentRow]:
    """Parse the selected set's augment allowlist, including reused augment IDs."""
    return [
        AugmentRow(
            api_name=item["apiName"],
            name=item.get("name") or item["apiName"],
            description=item.get("desc") or "",
            icon_url=icon_url(item.get("icon")),
            effects=json.dumps(item.get("effects") or {}, ensure_ascii=False),
            tier=augment_tier(item),
        )
        for item in _select_entries(all_items, active_augment_ids)
    ]
