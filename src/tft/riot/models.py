"""Typed source contracts for the verified TFT league and match responses."""

from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from tft.config import (
    DEFAULT_SET_NUMBER,
    HARVESTER_MATCH_COUNT,
    HARVESTER_TOP_CHALLENGERS,
    HARVESTER_TOP_GRANDMASTERS,
    RIOT_MATCH_COUNT_MAX,
    TFT_SERVERS,
)


class LeagueEntry(TypedDict):
    """Fields used from current league entries, which contain PUUID directly."""

    puuid: str
    leaguePoints: int


class MatchMetadata(TypedDict):
    """Match identity and the complete roster reported by Riot."""

    match_id: str
    participants: list[str]


class MatchParticipant(TypedDict):
    """End-game participant snapshot; current responses omit or null augments."""

    puuid: str
    placement: int
    level: int
    gold_left: int
    time_eliminated: float
    traits: list[dict[str, Any]]
    units: list[dict[str, Any]]
    augments: NotRequired[list[str] | None]


class MatchInfo(TypedDict):
    """Actual set and queue identify the mode even when the patch is unknown."""

    game_version: str
    tft_set_number: int
    game_datetime: int
    queue_id: int
    participants: list[MatchParticipant]


class MatchPayload(TypedDict):
    """Raw payload supplied by the TFT match endpoint."""

    metadata: MatchMetadata
    info: MatchInfo


@dataclass(frozen=True, slots=True)
class HarvestOptions:
    """An explicit, bounded sample of ranked players and their recent matches."""

    servers: tuple[str, ...] = ("NA",)
    challengers: int = HARVESTER_TOP_CHALLENGERS
    grandmasters: int = HARVESTER_TOP_GRANDMASTERS
    matches_per_player: int = HARVESTER_MATCH_COUNT
    set_number: int = DEFAULT_SET_NUMBER

    def __post_init__(self) -> None:
        """Reject invalid bounds before making any requests."""
        if not self.servers or any(server not in TFT_SERVERS for server in self.servers):
            raise ValueError("Choose one or more supported TFT servers")
        if self.challengers < 0 or self.grandmasters < 0:
            raise ValueError("Player counts cannot be negative")
        if self.challengers + self.grandmasters == 0:
            raise ValueError("Choose at least one Challenger or Grandmaster")
        if not 1 <= self.matches_per_player <= RIOT_MATCH_COUNT_MAX:
            raise ValueError(f"Matches per player must be 1–{RIOT_MATCH_COUNT_MAX}")
        if self.set_number < 1:
            raise ValueError("Set number must be positive")


@dataclass(slots=True)
class HarvestResult:
    """Counts for a harvest, including visible skips and recoverable failures."""

    players: int = 0
    matches_saved: int = 0
    participants_saved: int = 0
    matches_skipped: int = 0
    request_failures: int = 0
