"""Placement statistics for filtered boards and their per-entity breakdowns.

Every breakdown counts a board at most once per key, so a board holding two
copies of an item contributes one game to that item's row.
"""

from collections import defaultdict
from collections.abc import Hashable, Iterable, Sequence

from tft.config import EXPLORER_LOBBY_SIZE, EXPLORER_TOP_PLACEMENT
from tft.explorer.models import Board, FocusBreakdown, StatRow, Summary

type Key = tuple[Hashable, ...]

_RATE_DIGITS = 4
_PLACE_DIGITS = 3


class Tally:
    """Placement histograms grouped by an arbitrary hashable key."""

    def __init__(self) -> None:
        """Start with no observed boards."""
        self._counts: dict[Key, list[int]] = defaultdict(lambda: [0] * EXPLORER_LOBBY_SIZE)

    def add(self, keys: Iterable[Key], placement: int) -> None:
        """Record one board's placement under each distinct key.

        Args:
            keys: Keys present on the board; duplicates are counted once.
            placement: Final placement from 1 to the lobby size.
        """
        index = min(max(placement, 1), EXPLORER_LOBBY_SIZE) - 1
        for key in set(keys):
            self._counts[key][index] += 1

    def rows(self, fields: Sequence[str], total: int, baseline: float | None) -> list[StatRow]:
        """Convert histograms into rows sorted by games played.

        Args:
            fields: Row field name for each position of the key tuple.
            total: Boards in the population used for frequency.
            baseline: Average placement subtracted to give each row's delta.

        Returns:
            One statistics row per key.
        """
        rows: list[StatRow] = []
        for key, counts in self._counts.items():
            summary = summarize_counts(counts)
            row = StatRow(
                games=summary["games"],
                frequency=round(summary["games"] / total, _RATE_DIGITS) if total else 0.0,
                avg_place=summary["avg_place"] or 0.0,
                delta=round((summary["avg_place"] or 0.0) - (baseline or 0.0), _PLACE_DIGITS),
                top4=summary["top4"] or 0.0,
                win=summary["win"] or 0.0,
            )
            for name, value in zip(fields, key, strict=True):
                row[name] = list(value) if isinstance(value, tuple) else value
            rows.append(row)
        rows.sort(key=lambda row: (-row["games"], row["avg_place"]))
        return rows


def summarize_counts(counts: Sequence[int]) -> Summary:
    """Summarise a placement histogram.

    Args:
        counts: Boards per placement, index 0 being first place.

    Returns:
        Games, average placement, top-four rate, and win rate.
    """
    games = sum(counts)
    if not games:
        return Summary(games=0, avg_place=None, top4=None, win=None, placements=list(counts))
    weighted = sum((index + 1) * count for index, count in enumerate(counts))
    return Summary(
        games=games,
        avg_place=round(weighted / games, _PLACE_DIGITS),
        top4=round(sum(counts[:EXPLORER_TOP_PLACEMENT]) / games, _RATE_DIGITS),
        win=round(counts[0] / games, _RATE_DIGITS),
        placements=list(counts),
    )


def summarize(boards: Iterable[Board]) -> Summary:
    """Summarise the placements of a collection of boards.

    Args:
        boards: Boards to aggregate.

    Returns:
        Aggregate outcome with a full placement histogram.
    """
    counts = [0] * EXPLORER_LOBBY_SIZE
    for board in boards:
        counts[min(max(board.placement, 1), EXPLORER_LOBBY_SIZE) - 1] += 1
    return summarize_counts(counts)


def breakdowns(boards: Sequence[Board], baseline: float | None) -> dict[str, list[StatRow]]:
    """Build every tabular breakdown of the filtered boards in one pass.

    Args:
        boards: Boards that satisfy the current filters.
        baseline: Their average placement, used for deltas.

    Returns:
        Rows for units, unit star levels, items, traits, augments, and levels.
    """
    tallies = {name: Tally() for name in ("units", "unit_stars", "items", "traits", "augments")}
    levels = Tally()
    for board in boards:
        place = board.placement
        tallies["units"].add(((unit.id,) for unit in board.units), place)
        tallies["unit_stars"].add(((unit.id, unit.star) for unit in board.units), place)
        tallies["items"].add(((item,) for unit in board.units for item in unit.items), place)
        tallies["traits"].add(board.traits.items(), place)
        tallies["augments"].add(((augment,) for augment in board.augments), place)
        levels.add([(board.level,)], place)
    total = len(boards)
    fields = {
        "units": ("id",),
        "unit_stars": ("id", "star"),
        "items": ("id",),
        "traits": ("id", "tier"),
        "augments": ("id",),
    }
    result = {name: tally.rows(fields[name], total, baseline) for name, tally in tallies.items()}
    result["levels"] = sorted(levels.rows(("level",), total, baseline), key=lambda r: r["level"])
    return result


def focus_breakdown(boards: Sequence[Board], unit_id: str) -> FocusBreakdown:
    """Describe how one unit is played on the filtered boards.

    Frequencies are shares of boards fielding the unit, and deltas compare with
    the unit's own average placement.

    Args:
        boards: Boards that satisfy the current filters.
        unit_id: Lowercase unit identifier.

    Returns:
        Star-level, item-count, single-item, and full-build rows.
    """
    holders = [board for board in boards if unit_id in board.unit_ids]
    baseline = summarize(holders)["avg_place"]
    stars, counts, items, builds = Tally(), Tally(), Tally(), Tally()
    for board in holders:
        copies = [unit for unit in board.units if unit.id == unit_id]
        place = board.placement
        stars.add(((unit.star,) for unit in copies), place)
        counts.add(((len(unit.items),) for unit in copies), place)
        items.add(((item,) for unit in copies for item in unit.items), place)
        builds.add(((tuple(sorted(unit.items)),) for unit in copies if unit.items), place)
    total = len(holders)
    return FocusBreakdown(
        unit=unit_id,
        games=total,
        stars=sorted(stars.rows(("star",), total, baseline), key=lambda row: row["star"]),
        item_counts=sorted(
            counts.rows(("item_count",), total, baseline), key=lambda row: row["item_count"]
        ),
        items=items.rows(("id",), total, baseline),
        builds=builds.rows(("items",), total, baseline),
    )
