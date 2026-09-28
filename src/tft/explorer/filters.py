"""Parse browser filter specifications and evaluate them against boards.

Filters are combined with AND. An ``any`` filter holds alternatives combined
with OR, and every filter may be negated with ``"exclude": true``.
"""

import json
from collections import Counter
from collections.abc import Iterable
from typing import Any

from tft.config import (
    EXPLORER_MAX_ALTERNATIVES,
    EXPLORER_MAX_FILTERS,
    EXPLORER_MAX_ITEM_COPIES,
    EXPLORER_MAX_LEVEL,
    EXPLORER_MAX_QUERY_CHARS,
    EXPLORER_MAX_STAR,
    EXPLORER_MAX_TRAIT_TIER,
    EXPLORER_MAX_UNIT_ITEMS,
)
from tft.exceptions import ExplorerQueryError
from tft.explorer.models import (
    AnyFilter,
    AugmentFilter,
    Board,
    Filter,
    ItemFilter,
    LevelFilter,
    SimpleFilter,
    TraitFilter,
    UnitFilter,
)


def _identifier(spec: dict[str, Any]) -> str:
    """Read a required non-empty identifier, normalised to lowercase."""
    value = spec.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ExplorerQueryError("Each filter needs a non-empty id")
    return value.strip().lower()


def _integer(spec: dict[str, Any], key: str, default: int | None, low: int, high: int) -> int | None:
    """Read an optional bounded integer, rejecting booleans and other types."""
    value = spec.get(key, default)
    if value is None:
        return None
    if type(value) is not int or not low <= value <= high:
        raise ExplorerQueryError(f"Filter field {key} must be an integer from {low} to {high}")
    return value


def _exclude(spec: dict[str, Any]) -> bool:
    """Read the optional negation flag."""
    value = spec.get("exclude", False)
    if not isinstance(value, bool):
        raise ExplorerQueryError("Filter field exclude must be true or false")
    return value


def _parse_unit(spec: dict[str, Any]) -> UnitFilter:
    """Build a unit filter with optional stars, item count, and required items."""
    stars = spec.get("stars", [])
    if not isinstance(stars, list) or any(
        type(star) is not int or not 1 <= star <= EXPLORER_MAX_STAR for star in stars
    ):
        raise ExplorerQueryError(f"Unit stars must be integers from 1 to {EXPLORER_MAX_STAR}")
    items = spec.get("items", [])
    if (
        not isinstance(items, list)
        or len(items) > EXPLORER_MAX_UNIT_ITEMS
        or any(not isinstance(item, str) or not item.strip() for item in items)
    ):
        raise ExplorerQueryError(f"A unit filter accepts up to {EXPLORER_MAX_UNIT_ITEMS} items")
    min_items = _integer(spec, "min_items", 0, 0, EXPLORER_MAX_UNIT_ITEMS) or 0
    return UnitFilter(
        id=_identifier(spec),
        stars=frozenset(stars),
        items=tuple(item.strip().lower() for item in items),
        min_items=min_items,
        exclude=_exclude(spec),
    )


def _parse_simple(spec: Any) -> SimpleFilter:
    """Build one non-group filter from its JSON specification."""
    if not isinstance(spec, dict):
        raise ExplorerQueryError("Each filter must be a JSON object")
    kind = spec.get("kind")
    if kind == "unit":
        return _parse_unit(spec)
    if kind == "item":
        count = _integer(spec, "min_count", 1, 1, EXPLORER_MAX_ITEM_COPIES)
        return ItemFilter(_identifier(spec), count or 1, _exclude(spec))
    if kind == "trait":
        low = _integer(spec, "min_tier", 1, 1, EXPLORER_MAX_TRAIT_TIER) or 1
        high = _integer(spec, "max_tier", None, low, EXPLORER_MAX_TRAIT_TIER)
        return TraitFilter(_identifier(spec), low, high, _exclude(spec))
    if kind == "augment":
        return AugmentFilter(_identifier(spec), _exclude(spec))
    if kind == "level":
        low = _integer(spec, "min", 1, 1, EXPLORER_MAX_LEVEL) or 1
        high = _integer(spec, "max", None, low, EXPLORER_MAX_LEVEL)
        return LevelFilter(low, high, _exclude(spec))
    raise ExplorerQueryError(f"Unsupported filter kind: {kind!r}")


def parse_filter(spec: Any) -> Filter:
    """Build one filter, including OR groups of simple alternatives.

    Args:
        spec: Decoded JSON object describing the filter.

    Returns:
        A typed, validated filter.

    Raises:
        ExplorerQueryError: If the specification is malformed or too large.
    """
    if isinstance(spec, dict) and spec.get("kind") == "any":
        alternatives = spec.get("filters")
        if not isinstance(alternatives, list) or not alternatives:
            raise ExplorerQueryError("An OR group needs at least one alternative")
        if len(alternatives) > EXPLORER_MAX_ALTERNATIVES:
            raise ExplorerQueryError(
                f"An OR group accepts up to {EXPLORER_MAX_ALTERNATIVES} alternatives"
            )
        return AnyFilter(tuple(_parse_simple(item) for item in alternatives), _exclude(spec))
    return _parse_simple(spec)


def parse_filters(raw: str | None) -> tuple[Filter, ...]:
    """Decode the JSON filter list sent by the browser.

    Args:
        raw: JSON array text, or None/empty for no filters.

    Returns:
        Validated filters combined with AND.

    Raises:
        ExplorerQueryError: If the text is not a valid, bounded filter list.
    """
    if not raw:
        return ()
    if len(raw) > EXPLORER_MAX_QUERY_CHARS:
        raise ExplorerQueryError("The filter request is too long")
    try:
        specs = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExplorerQueryError("Filters must be a JSON array") from exc
    if not isinstance(specs, list):
        raise ExplorerQueryError("Filters must be a JSON array")
    if len(specs) > EXPLORER_MAX_FILTERS:
        raise ExplorerQueryError(f"Use at most {EXPLORER_MAX_FILTERS} filters")
    return tuple(parse_filter(spec) for spec in specs)


def _unit_matches(board: Board, rule: UnitFilter) -> bool:
    """True if any copy of the unit satisfies every unit constraint."""
    for unit in board.units:
        if unit.id != rule.id:
            continue
        if rule.stars and unit.star not in rule.stars:
            continue
        if len(unit.items) < rule.min_items:
            continue
        held = Counter(unit.items)
        if all(held[item] >= count for item, count in Counter(rule.items).items()):
            return True
    return False


def _positive_match(board: Board, rule: Filter) -> bool:
    """Evaluate a filter without applying its exclude flag."""
    match rule:
        case UnitFilter():
            return _unit_matches(board, rule)
        case ItemFilter():
            held = sum(unit.items.count(rule.id) for unit in board.units)
            return held >= rule.min_count
        case TraitFilter():
            tier = board.traits.get(rule.id, 0)
            return tier >= rule.min_tier and (rule.max_tier is None or tier <= rule.max_tier)
        case AugmentFilter():
            return rule.id in board.augments
        case LevelFilter():
            return board.level >= rule.min_level and (
                rule.max_level is None or board.level <= rule.max_level
            )
        case AnyFilter():
            return any(matches(board, alternative) for alternative in rule.alternatives)
    raise ExplorerQueryError(f"Unsupported filter: {rule!r}")


def matches(board: Board, rule: Filter) -> bool:
    """Evaluate one filter, honouring its exclude flag.

    Args:
        board: Final board snapshot.
        rule: Parsed filter.

    Returns:
        True if the board satisfies the filter.
    """
    return _positive_match(board, rule) != rule.exclude


def apply_filters(boards: Iterable[Board], rules: tuple[Filter, ...]) -> list[Board]:
    """Keep boards that satisfy every filter.

    Args:
        boards: Candidate boards.
        rules: Filters combined with AND.

    Returns:
        Matching boards in their original order.
    """
    return [board for board in boards if all(matches(board, rule) for rule in rules)]
