"""Typed representations used by local match analytics."""

from dataclasses import dataclass
from typing import TypedDict

import pandas as pd

type ChampInfo = tuple[str, int, str | None]
type ChampTraits = dict[str, set[str]]


class Unit(TypedDict, total=False):
    """Stored final-board unit fields used by the analysis pipeline."""

    character_id: str
    rarity: int
    tier: int
    itemNames: list[str]


class Trait(TypedDict, total=False):
    """Stored final-board trait fields used by the classifier."""

    name: str
    tier_current: int
    num_units: int
    style: int


class ClassifiedBoard(TypedDict):
    """Composition labels and carry information derived from a board."""

    comp_name: str
    comp_group: str
    carry_id: str
    carry_name: str
    carry_star: int
    carry_cost: int
    carry_items: str
    tank_id: str
    tank_name: str
    comp_type: str
    all_board_items: str


@dataclass(frozen=True)
class AnalysisLookups:
    """Static champion, trait, and item lookups for one analysis run."""

    champions: dict[str, ChampInfo]
    traits: dict[str, str]
    champion_traits: ChampTraits
    items: dict[str, str]


@dataclass(frozen=True)
class AnalysisResult:
    """Analysis tables and provenance shared by the CLI and local web API."""

    versions: list[str]
    sample_count: int
    population: pd.DataFrame
    behavioral: pd.DataFrame
    highrolls: pd.DataFrame
