"""Validate live TFT match snapshots and convert them to typed database rows."""

import json
from typing import Any

from tft.db.models import MatchParticipantRow, MatchRow
from tft.exceptions import MatchDataError
from tft.riot.models import MatchPayload


def _required_int(source: dict[str, Any], key: str) -> int:
    """Read an integer field without accepting absent values or booleans."""
    value = source.get(key)
    if type(value) is not int:
        raise MatchDataError(f"Match is missing integer field {key}")
    return value


def parse_match_metadata(match_json: MatchPayload) -> MatchRow:
    """Retain actual set, queue, timestamp and unmodified source version.

    Source game_version can be an unknown placeholder. It is descriptive
    metadata and must never determine set selection or trigger a data purge.
    """
    metadata = match_json.get("metadata", {})
    info = match_json.get("info", {})
    match_id = metadata.get("match_id")
    if not isinstance(match_id, str) or not match_id:
        raise MatchDataError("Match metadata is missing match_id")
    version = info.get("game_version", "")
    if not isinstance(version, str):
        raise MatchDataError("Match game_version must be a string")
    participants = info.get("participants")
    if not isinstance(participants, list) or not participants:
        raise MatchDataError("Match contains no participant snapshots")
    return MatchRow(
        match_id=match_id,
        game_version=version,
        set_number=_required_int(info, "tft_set_number"),
        game_datetime=_required_int(info, "game_datetime"),
        queue_id=_required_int(info, "queue_id"),
        participant_count=len(participants),
    )


def parse_match_participants(match_json: MatchPayload) -> list[MatchParticipantRow]:
    """Require one valid snapshot for every player in the source roster.

    The current endpoint omits augments; an empty array preserves the database
    contract without inventing choices. Traits and units retain source IDs.
    """
    match = parse_match_metadata(match_json)
    roster = match_json["metadata"].get("participants")
    if not isinstance(roster, list) or any(not isinstance(p, str) or not p for p in roster):
        raise MatchDataError("Match metadata is missing its participant roster")
    rows: list[MatchParticipantRow] = []
    for participant in match_json["info"]["participants"]:
        if not isinstance(participant, dict):
            raise MatchDataError("Participant must be an object")
        puuid = participant.get("puuid")
        if not isinstance(puuid, str) or not puuid:
            raise MatchDataError("Participant is missing PUUID")
        traits = participant.get("traits")
        units = participant.get("units")
        augments = participant.get("augments")
        if augments is None:
            # Live match details currently omit augments or send JSON null.
            augments = []
        if not all(isinstance(value, list) for value in (traits, units, augments)):
            raise MatchDataError("Participant traits, units and augments must be arrays")
        eliminated = participant.get("time_eliminated")
        if not isinstance(eliminated, (int, float)) or isinstance(eliminated, bool):
            raise MatchDataError("Participant is missing time_eliminated")
        rows.append(MatchParticipantRow(
            match_id=match.match_id,
            puuid=puuid,
            placement=_required_int(participant, "placement"),
            level=_required_int(participant, "level"),
            gold_left=_required_int(participant, "gold_left"),
            time_eliminated=float(eliminated),
            traits_json=json.dumps(traits, ensure_ascii=False),
            units_json=json.dumps(units, ensure_ascii=False),
            augments_json=json.dumps(augments, ensure_ascii=False),
        ))
    observed = {row.puuid for row in rows}
    if len(observed) != len(rows) or len(set(roster)) != len(roster) or observed != set(roster):
        raise MatchDataError("Participant snapshots do not match the complete source roster")
    return rows
