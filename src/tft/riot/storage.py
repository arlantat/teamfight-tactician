"""Additive match migrations and atomic, complete-match persistence."""

import sqlite3
from dataclasses import asdict

from tft.config import COMPLETED_MATCHES_PATH, MATCH_SCHEMA_PATH, MATCH_UPSERT_PATH
from tft.db.connection import insert_rows, run_schema
from tft.db.models import MatchParticipantRow, MatchRow, PlayerRow
from tft.exceptions import MatchDataError


def migrate_match_schema(conn: sqlite3.Connection) -> None:
    """Create tables and add nullable provenance to legacy match records."""
    with conn:
        run_schema(conn, MATCH_SCHEMA_PATH)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
        for name in ("set_number", "game_datetime", "queue_id", "participant_count"):
            if name not in columns:
                conn.execute(f"ALTER TABLE matches ADD COLUMN {name} INTEGER")


def store_players(conn: sqlite3.Connection, players: list[PlayerRow]) -> None:
    """Update observed league tiers without replacing referenced player rows."""
    with conn:
        conn.executemany(
            "INSERT INTO players(puuid, tier) VALUES (?, ?) "
            "ON CONFLICT(puuid) DO UPDATE SET tier = excluded.tier",
            [(player.puuid, player.tier) for player in players],
        )


def complete_match_ids(conn: sqlite3.Connection, set_number: int, queue_id: int) -> set[str]:
    """Return only matches with verified provenance and all participant rows."""
    rows = conn.execute(COMPLETED_MATCHES_PATH.read_text(), (set_number, queue_id))
    return {row[0] for row in rows}


def store_match(
    conn: sqlite3.Connection,
    match: MatchRow,
    participants: list[MatchParticipantRow],
) -> int:
    """Save a header and every participant in one transaction, or roll back.

    Incomplete historical matches are repaired by replacing their snapshots.
    Existing observed league tiers remain attached to participants; previously
    unseen opponents receive UNKNOWN until a league lookup establishes a tier.
    """
    if (
        not participants
        or match.participant_count != len(participants)
        or len({participant.puuid for participant in participants}) != len(participants)
        or any(participant.match_id != match.match_id for participant in participants)
    ):
        raise MatchDataError("Cannot store an incomplete or mismatched participant roster")
    with conn:
        conn.executemany(
            "INSERT INTO players(puuid, tier) VALUES (?, 'UNKNOWN') ON CONFLICT(puuid) DO NOTHING",
            [(participant.puuid,) for participant in participants],
        )
        conn.execute(MATCH_UPSERT_PATH.read_text(), asdict(match))
        conn.execute("DELETE FROM match_participants WHERE match_id = ?", (match.match_id,))
        return insert_rows(conn, "match_participants", participants, commit=False)
