"""Load stored ranked boards into compact explorer snapshots.

Boards are read with the same set and ranked-queue scope as the analysis
pipeline and cached until the database file changes.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from tft.analysis.data import load_data
from tft.config import ANALYSIS_SUMMON_KEYWORDS, EXPLORER_UNTRACKED_RANK
from tft.explorer.models import Board, BoardSet, BoardUnit

log = logging.getLogger(__name__)

_SUMMON_KEYWORDS = tuple(keyword.lower() for keyword in ANALYSIS_SUMMON_KEYWORDS)


def _is_playable(character_id: str) -> bool:
    """True if the lowercase identifier is a champion rather than a summon or prop."""
    return bool(character_id) and not any(key in character_id for key in _SUMMON_KEYWORDS)


def _parse_units(raw: list[Any]) -> tuple[BoardUnit, ...]:
    """Convert stored Riot unit objects, skipping summons and malformed entries."""
    units: list[BoardUnit] = []
    for unit in raw:
        if not isinstance(unit, dict):
            continue
        character_id = str(unit.get("character_id") or "").lower()
        if not _is_playable(character_id):
            continue
        items = unit.get("itemNames") or []
        star = unit.get("tier")
        units.append(BoardUnit(
            id=character_id,
            star=star if type(star) is int and star > 0 else 1,
            items=tuple(str(item).lower() for item in items if isinstance(item, str) and item),
        ))
    return tuple(units)


def _parse_traits(raw: list[Any]) -> dict[str, int]:
    """Map each active trait to its source breakpoint tier."""
    traits: dict[str, int] = {}
    for trait in raw:
        if not isinstance(trait, dict):
            continue
        name = trait.get("name")
        tier = trait.get("tier_current")
        if isinstance(name, str) and name and type(tier) is int and tier > 0:
            traits[name.lower()] = tier
    return traits


def parse_board(row: dict[str, Any]) -> Board | None:
    """Build one board from a stored participant row.

    Args:
        row: Participant columns produced by the analysis participant query.

    Returns:
        The board, or None if its stored JSON is unreadable.
    """
    try:
        units = json.loads(row["units_json"])
        traits = json.loads(row["traits_json"])
        augments = json.loads(row["augments_json"] or "[]")
    except (json.JSONDecodeError, TypeError) as exc:
        log.warning("Skipping unreadable board %s: %s", row.get("match_id"), exc)
        return None
    if not all(isinstance(value, list) for value in (units, traits, augments)):
        log.warning("Skipping malformed board %s", row.get("match_id"))
        return None
    tier = row.get("tier")
    return Board(
        placement=int(row["placement"]),
        level=int(row["level"]),
        rank=tier if isinstance(tier, str) and tier else EXPLORER_UNTRACKED_RANK,
        game_version=str(row.get("game_version") or ""),
        units=_parse_units(units),
        traits=_parse_traits(traits),
        augments=frozenset(str(item).lower() for item in augments if isinstance(item, str)),
    )


@lru_cache(maxsize=4)
def _cached_boards(path: str, revision: tuple[int, ...]) -> BoardSet:
    """Parse every stored board once per database file revision."""
    frame = load_data(Path(path))
    if frame.empty:
        return BoardSet(boards=())
    boards = tuple(
        board
        for row in frame.to_dict(orient="records")
        if (board := parse_board(row)) is not None
    )
    log.info("Explorer loaded %d boards from %s", len(boards), Path(path).name)
    return BoardSet(
        boards=boards,
        versions=tuple(sorted({board.game_version for board in boards}, reverse=True)),
        ranks=tuple(sorted({board.rank for board in boards})),
        has_augments=any(board.augments for board in boards),
    )


def load_boards(db_path: Path) -> BoardSet:
    """Return every compatible stored board, reusing parsed data when unchanged.

    Args:
        db_path: Existing SQLite database with static and match tables.

    Returns:
        Parsed boards plus the versions and ranks present.

    Raises:
        FileNotFoundError: If the database does not exist.
    """
    resolved = db_path.resolve()
    stat = resolved.stat()
    revision = [stat.st_mtime_ns, stat.st_size]
    # WAL-mode writes land in the sidecar file before a checkpoint touches the database.
    wal = resolved.with_name(f"{resolved.name}-wal")
    if wal.is_file():
        wal_stat = wal.stat()
        revision += [wal_stat.st_mtime_ns, wal_stat.st_size]
    return _cached_boards(str(resolved), tuple(revision))
