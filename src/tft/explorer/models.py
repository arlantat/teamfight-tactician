"""Typed boards, filters, and result rows used by the match explorer.

Identifiers are stored lowercase so filters match regardless of the casing
used by Riot match payloads and the CommunityDragon catalog.
"""

from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True, slots=True)
class BoardUnit:
    """One final-board unit with its star level and held items."""

    id: str
    star: int
    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Board:
    """One player's end-of-game snapshot with the fields the explorer filters on."""

    placement: int
    level: int
    rank: str
    game_version: str
    units: tuple[BoardUnit, ...]
    traits: dict[str, int]  # Active trait id -> source tier_current (1 = first breakpoint)
    augments: frozenset[str]

    @property
    def unit_ids(self) -> frozenset[str]:
        """Distinct unit identifiers on the board."""
        return frozenset(unit.id for unit in self.units)


@dataclass(frozen=True, slots=True)
class UnitFilter:
    """Require a unit, optionally at given star levels, item counts, or with items."""

    id: str
    stars: frozenset[int] = frozenset()
    items: tuple[str, ...] = ()
    min_items: int = 0
    exclude: bool = False


@dataclass(frozen=True, slots=True)
class ItemFilter:
    """Require at least ``min_count`` copies of an item anywhere on the board."""

    id: str
    min_count: int = 1
    exclude: bool = False


@dataclass(frozen=True, slots=True)
class TraitFilter:
    """Require a trait active within an inclusive range of breakpoint tiers."""

    id: str
    min_tier: int = 1
    max_tier: int | None = None
    exclude: bool = False


@dataclass(frozen=True, slots=True)
class AugmentFilter:
    """Require a selected augment."""

    id: str
    exclude: bool = False


@dataclass(frozen=True, slots=True)
class LevelFilter:
    """Require a final player level within an inclusive range."""

    min_level: int = 1
    max_level: int | None = None
    exclude: bool = False


type SimpleFilter = UnitFilter | ItemFilter | TraitFilter | AugmentFilter | LevelFilter


@dataclass(frozen=True, slots=True)
class AnyFilter:
    """Match boards satisfying at least one alternative (logical OR)."""

    alternatives: tuple[SimpleFilter, ...]
    exclude: bool = False


type Filter = SimpleFilter | AnyFilter


@dataclass(frozen=True, slots=True)
class ExplorerQuery:
    """A complete explorer request: scope, AND-combined filters, and a focus unit."""

    filters: tuple[Filter, ...] = ()
    game_version: str | None = None
    rank: str | None = None
    focus_unit: str | None = None


@dataclass(frozen=True, slots=True)
class BoardSet:
    """All stored boards and the scopes available for selection."""

    boards: tuple[Board, ...]
    versions: tuple[str, ...] = ()
    ranks: tuple[str, ...] = ()
    has_augments: bool = False


class Summary(TypedDict):
    """Aggregate outcome of a set of boards."""

    games: int
    avg_place: float | None
    top4: float | None
    win: float | None
    placements: list[int]  # Count per placement, index 0 = first place


class StatRow(TypedDict, total=False):
    """Outcome of boards containing one entity, keyed by the identifying fields."""

    id: str
    star: int
    tier: int
    level: int
    items: list[str]
    item_count: int
    games: int
    frequency: float
    avg_place: float
    delta: float
    top4: float
    win: float


class FocusBreakdown(TypedDict):
    """Star levels, item counts, single items, and full builds on one unit."""

    unit: str
    games: int
    stars: list[StatRow]
    item_counts: list[StatRow]
    items: list[StatRow]
    builds: list[StatRow]


class ExplorerResult(TypedDict):
    """Response returned to the browser for one explorer query."""

    versions: list[str]
    ranks: list[str]
    has_augments: bool
    base: Summary
    filtered: Summary
    units: list[StatRow]
    unit_stars: list[StatRow]
    items: list[StatRow]
    traits: list[StatRow]
    augments: list[StatRow]
    levels: list[StatRow]
    focus: FocusBreakdown | None
