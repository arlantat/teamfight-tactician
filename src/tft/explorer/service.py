"""Answer explorer queries over the locally stored ranked boards."""

import logging
from pathlib import Path

from tft.explorer.aggregate import breakdowns, focus_breakdown, summarize
from tft.explorer.dataset import load_boards
from tft.explorer.filters import apply_filters
from tft.explorer.models import Board, BoardSet, ExplorerQuery, ExplorerResult

log = logging.getLogger(__name__)


def _scoped(board_set: BoardSet, query: ExplorerQuery) -> list[Board]:
    """Restrict boards to the selected game version and player rank."""
    return [
        board
        for board in board_set.boards
        if (query.game_version is None or board.game_version == query.game_version)
        and (query.rank is None or board.rank == query.rank)
    ]


def explore_boards(board_set: BoardSet, query: ExplorerQuery) -> ExplorerResult:
    """Filter boards and compute the summary and every breakdown.

    Args:
        board_set: Parsed stored boards.
        query: Scope, filters, and optional focus unit.

    Returns:
        Baseline and filtered outcomes plus per-entity statistics.
    """
    scoped = _scoped(board_set, query)
    filtered = apply_filters(scoped, query.filters)
    summary = summarize(filtered)
    tables = breakdowns(filtered, summary["avg_place"])
    log.debug("Explorer matched %d of %d scoped boards", len(filtered), len(scoped))
    return ExplorerResult(
        versions=list(board_set.versions),
        ranks=list(board_set.ranks),
        has_augments=board_set.has_augments,
        base=summarize(scoped),
        filtered=summary,
        units=tables["units"],
        unit_stars=tables["unit_stars"],
        items=tables["items"],
        traits=tables["traits"],
        augments=tables["augments"],
        levels=tables["levels"],
        focus=focus_breakdown(filtered, query.focus_unit) if query.focus_unit else None,
    )


def explore(db_path: Path, query: ExplorerQuery) -> ExplorerResult:
    """Load stored boards and answer one explorer query.

    Args:
        db_path: Existing SQLite database with static and match tables.
        query: Scope, filters, and optional focus unit.

    Returns:
        Explorer statistics; empty when no compatible matches are stored.
    """
    return explore_boards(load_boards(db_path), query)
