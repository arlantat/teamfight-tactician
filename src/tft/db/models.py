"""Dataclass models for database rows.

Each dataclass here corresponds 1-to-1 with a table in ``schema.sql`` or
``match_schema.sql``.  They serve as the contract between the ETL layer and
the DB layer.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Static data tables  (schema.sql)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChampionRow:
    """A single champion record ready for DB insertion."""

    api_name: str
    name: str
    cost: int
    role: str | None  # CDragon role tag  e.g. 'APCaster', 'ADTank'
    traits: str  # JSON-encoded list[str]
    icon_url: str | None
    square_icon_url: str | None = None
    ability_name: str = ""
    ability_description: str = ""
    ability_icon_url: str | None = None
    ability_variables: str = "[]"  # JSON array of named star-level value arrays
    stats: str = "{}"  # JSON object of source combat stats
    ability_detail: str = "{}"  # JSON object of supplemental forms, formulas, and provenance


@dataclass(frozen=True, slots=True)
class TraitRow:
    """A single trait record ready for DB insertion."""

    api_name: str
    name: str
    effects: str  # JSON-encoded list[dict]
    icon_url: str | None
    description: str = ""


@dataclass(frozen=True, slots=True)
class ItemRow:
    """A single item record ready for DB insertion."""

    api_name: str
    name: str
    description: str
    icon_url: str | None
    composition: str = "[]"  # JSON array of component api_names
    effects: str = "{}"  # JSON object of source effect values
    category: str = "special"


@dataclass(frozen=True, slots=True)
class AugmentRow:
    """A currently available augment and its source effect values."""

    api_name: str
    name: str
    description: str
    icon_url: str | None
    effects: str
    tier: str


@dataclass(frozen=True, slots=True)
class StaticDataMetadata:
    """Provenance of the single static catalog snapshot in the database."""

    set_number: int
    set_name: str
    patch: str | None
    source_url: str
    fetched_at: str
    source_set_name: str
    mutator: str
    source_version: str | None = None


# ---------------------------------------------------------------------------
# Match harvester tables  (match_schema.sql)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlayerRow:
    """A ranked player record."""

    puuid: str
    tier: str  # 'CHALLENGER' or 'GRANDMASTER'


@dataclass(frozen=True, slots=True)
class MatchRow:
    """A single TFT match record."""

    match_id: str
    game_version: str
    set_number: int | None = None
    game_datetime: int | None = None
    queue_id: int | None = None
    participant_count: int | None = None


@dataclass(frozen=True, slots=True)
class MatchParticipantRow:
    """One player's end-game snapshot within a match."""

    match_id: str
    puuid: str
    placement: int
    level: int
    gold_left: int
    time_eliminated: float
    traits_json: str  # JSON array of trait objects
    units_json: str  # JSON array of unit objects
    augments_json: str  # JSON array of augment strings
