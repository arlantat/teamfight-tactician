"""Regression coverage for source validation, migrations and atomic harvesting."""

import sqlite3
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import replace
from typing import cast
from unittest.mock import Mock

import pytest

from tft.db.models import PlayerRow
from tft.etl.match_parser import parse_match_metadata, parse_match_participants
from tft.exceptions import MatchDataError, RiotApiError
from tft.riot.client import RiotClient
from tft.riot.harvest import harvest_server
from tft.riot.models import HarvestOptions, HarvestResult, MatchPayload
from tft.riot.storage import complete_match_ids, migrate_match_schema, store_match, store_players


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    """Use foreign keys to catch orphan inserts and unsafe replacement behavior."""
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    migrate_match_schema(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def payload() -> MatchPayload:
    """Represent current live keys, with an unknown version and absent augments."""
    return cast(MatchPayload, {
        "metadata": {"match_id": "NA1_18", "participants": ["a", "b"]},
        "info": {
            "game_version": "TFT Unreal Version ?.?.?.?",
            "tft_set_number": 18,
            "game_datetime": 1789315200000,
            "queue_id": 1100,
            "participants": [
                {
                    "puuid": puuid, "placement": index + 1, "level": 9,
                    "gold_left": 2, "time_eliminated": 1800.5,
                    "traits": [{"name": "DA_Trait18", "num_units": 2}],
                    "units": [{"character_id": "DA_Cinderling18", "itemNames": ["DA_GiantSlayer"]}],
                }
                for index, puuid in enumerate(("a", "b"))
            ],
        },
    })


def test_unknown_version_and_missing_augments_are_preserved(payload: MatchPayload) -> None:
    """A placeholder version cannot reject a verified current-set match."""
    match = parse_match_metadata(payload)
    assert match.game_version == "TFT Unreal Version ?.?.?.?"
    assert match.set_number == 18
    assert match.participant_count == 2
    assert parse_match_participants(payload)[0].augments_json == "[]"
    assert "DA_Cinderling18" in parse_match_participants(payload)[0].units_json


def test_explicit_null_augments_are_stored_as_empty_array(payload: MatchPayload) -> None:
    """A JSON null augment list is the same omission as a missing key."""
    payload["info"]["participants"][0]["augments"] = None
    assert parse_match_participants(payload)[0].augments_json == "[]"


def test_incomplete_source_roster_is_rejected(payload: MatchPayload) -> None:
    """A truncated participant array must not receive a completeness marker."""
    payload["info"]["participants"].pop()
    with pytest.raises(MatchDataError, match="complete source roster"):
        parse_match_participants(payload)


def test_legacy_migration_preserves_rows_and_can_repeat() -> None:
    """Adding metadata never classifies or deletes historical matches."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE matches(match_id TEXT PRIMARY KEY, game_version TEXT NOT NULL)")
        connection.execute("INSERT INTO matches VALUES ('old', 'Version 16.9.1')")
        connection.commit()
        migrate_match_schema(connection)
        migrate_match_schema(connection)
        assert connection.execute(
            "SELECT match_id, game_version, set_number, participant_count FROM matches"
        ).fetchone() == ("old", "Version 16.9.1", None, None)
    finally:
        connection.close()


def test_atomic_failure_rolls_back_new_match(conn: sqlite3.Connection, payload: MatchPayload) -> None:
    """A failure on a later participant must remove the header and early rows."""
    conn.execute(
        "CREATE TRIGGER reject_b BEFORE INSERT ON match_participants "
        "WHEN NEW.puuid = 'b' BEGIN SELECT RAISE(ABORT, 'bad participant'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="bad participant"):
        store_match(conn, parse_match_metadata(payload), parse_match_participants(payload))
    for table in ("matches", "match_participants", "players"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_repair_and_idempotence(conn: sqlite3.Connection, payload: MatchPayload) -> None:
    """Incomplete old snapshots get repaired; repeated upserts retain tiers."""
    conn.execute("INSERT INTO matches(match_id, game_version) VALUES ('NA1_18', 'unknown')")
    conn.commit()
    assert complete_match_ids(conn, 18, 1100) == set()
    store_players(conn, [PlayerRow("a", "CHALLENGER")])
    match, participants = parse_match_metadata(payload), parse_match_participants(payload)
    store_match(conn, match, participants)
    store_match(conn, match, participants)
    assert complete_match_ids(conn, 18, 1100) == {"NA1_18"}
    assert conn.execute("SELECT COUNT(*) FROM match_participants").fetchone()[0] == 2
    assert conn.execute("SELECT tier FROM players WHERE puuid = 'a'").fetchone()[0] == "CHALLENGER"
    store_players(conn, [PlayerRow("a", "GRANDMASTER")])
    assert conn.execute("SELECT COUNT(*) FROM match_participants").fetchone()[0] == 2
    conn.execute("DELETE FROM match_participants WHERE puuid = 'b'")
    conn.commit()
    assert complete_match_ids(conn, 18, 1100) == set()


def test_atomic_failed_repair_preserves_previous_match(
    conn: sqlite3.Connection, payload: MatchPayload,
) -> None:
    """An interrupted refresh leaves a previous complete match unchanged."""
    match, participants = parse_match_metadata(payload), parse_match_participants(payload)
    store_match(conn, match, participants)
    conn.execute(
        "CREATE TRIGGER reject_b BEFORE INSERT ON match_participants "
        "WHEN NEW.puuid = 'b' BEGIN SELECT RAISE(ABORT, 'bad participant'); END"
    )
    with pytest.raises(sqlite3.IntegrityError):
        store_match(conn, replace(match, game_version="changed"), participants)
    assert complete_match_ids(conn, 18, 1100) == {"NA1_18"}
    assert conn.execute("SELECT game_version FROM matches").fetchone()[0] == match.game_version


def test_harvest_filters_set_queue_and_resumes(
    conn: sqlite3.Connection, payload: MatchPayload,
) -> None:
    """Only actual requested ranked set records are saved, without a patch guess."""
    old = deepcopy(payload)
    old["metadata"]["match_id"] = "old"
    old["info"]["tft_set_number"] = 17
    casual = deepcopy(payload)
    casual["metadata"]["match_id"] = "casual"
    casual["info"]["queue_id"] = 1090
    cases = {"NA1_18": payload, "old": old, "casual": casual}
    client = Mock(spec=RiotClient)
    client.get_league.return_value = [{"puuid": "a", "leaguePoints": 100}]
    client.get_match_ids.return_value = list(cases)
    client.get_match.side_effect = cases.__getitem__
    options = HarvestOptions(challengers=1, grandmasters=0)
    result = HarvestResult()
    harvest_server(client, conn, options, result)
    assert (result.matches_saved, result.participants_saved, result.matches_skipped) == (1, 2, 2)
    client.get_match.reset_mock()
    harvest_server(client, conn, options, HarvestResult())
    assert "NA1_18" not in [call.args[0] for call in client.get_match.call_args_list]


def test_failed_match_is_retryable(conn: sqlite3.Connection, payload: MatchPayload) -> None:
    """A source failure is visible and leaves no header that would skip retries."""
    client = Mock(spec=RiotClient)
    client.get_league.return_value = [{"puuid": "a", "leaguePoints": 100}]
    client.get_match_ids.return_value = ["NA1_18"]
    client.get_match.side_effect = RiotApiError("network")
    options = HarvestOptions(challengers=1, grandmasters=0)
    result = HarvestResult()
    harvest_server(client, conn, options, result)
    assert result.request_failures == 1
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0
    client.get_match.side_effect = None
    client.get_match.return_value = payload
    harvest_server(client, conn, options, result)
    assert result.matches_saved == 1


def test_invalid_player_scope_fails_before_requests() -> None:
    """The user cannot accidentally request zero players or an unbounded history."""
    with pytest.raises(ValueError):
        HarvestOptions(challengers=-1)
    with pytest.raises(ValueError):
        HarvestOptions(matches_per_player=101)
