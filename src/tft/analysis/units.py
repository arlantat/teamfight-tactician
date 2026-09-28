"""Unit classification helpers for stored TFT match boards."""

from tft.analysis.models import ChampInfo, Unit
from tft.config import (
    ANALYSIS_COMPONENT_ITEMS,
    ANALYSIS_SUMMON_KEYWORDS,
    ANALYSIS_THRESHOLD_CAP,
    ANALYSIS_THRESHOLD_DIVISOR,
    ANALYSIS_THRESHOLD_FLOOR,
    ANALYSIS_UNIQUE_TRAIT_KEYWORDS,
    RARITY_TO_COST,
)


def _is_team_trait(name: str) -> bool:
    """True if the trait api_name is a shared team synergy."""
    return not any(kw in name for kw in ANALYSIS_UNIQUE_TRAIT_KEYWORDS)


def _is_real_champion(cid: str) -> bool:
    """True if the character_id is a playable champion, not a summon."""
    return bool(cid) and not any(
        keyword.lower() in cid.lower() for keyword in ANALYSIS_SUMMON_KEYWORDS
    )


def _clean_trait_name(api: str) -> str:
    """Strip set prefix: ``TFT16_Ionia`` → ``Ionia``."""
    parts = api.split("_", 1)
    return parts[1] if len(parts) > 1 else api


def _completed_item_count(item_names: list[str]) -> int:
    """Count non-component items on a unit."""
    return sum(
        1
        for item in item_names
        if item.lower() not in {component.lower() for component in ANALYSIS_COMPONENT_ITEMS}
    )


def _unit_cost(u: Unit, cl: dict[str, ChampInfo]) -> int:
    """Get cost from champion lookup, falling back to rarity mapping."""
    info = cl.get(u.get("character_id", "")) or cl.get(
        u.get("character_id", "").lower(),
    )
    return info[1] if info else RARITY_TO_COST.get(u.get("rarity", 0), 0)


def _unit_role(u: Unit, cl: dict[str, ChampInfo]) -> str | None:
    """Get CDragon role from champion lookup."""
    info = cl.get(u.get("character_id", "")) or cl.get(
        u.get("character_id", "").lower(),
    )
    return info[2] if info else None


def _unit_name(u: Unit, cl: dict[str, ChampInfo]) -> str:
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

    Uses the smaller tier sample divided by the configured divisor,
    clamped to the configured minimum and maximum sample size.
    """
    return max(
        ANALYSIS_THRESHOLD_FLOOR,
        min(ANALYSIS_THRESHOLD_CAP, min(chall_n, gm_n) // ANALYSIS_THRESHOLD_DIVISOR),
    )
