"""Dataclass models for database rows.

Each dataclass here corresponds 1-to-1 with a table in ``schema.sql``.
They serve as the contract between the ETL layer and the DB layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChampionRow:
    """A single champion record ready for DB insertion."""

    api_name: str
    name: str
    cost: int
    traits: str       # JSON-encoded list[str]
    icon_url: str | None


@dataclass(frozen=True, slots=True)
class TraitRow:
    """A single trait record ready for DB insertion."""

    api_name: str
    name: str
    effects: str      # JSON-encoded list[dict]
    icon_url: str | None


@dataclass(frozen=True, slots=True)
class ItemRow:
    """A single item record ready for DB insertion."""

    api_name: str
    name: str
    description: str
    icon_url: str | None
