"""Contracts for the normalized supplemental ability payload."""

from typing import Any, NotRequired, TypedDict

type CurveValues = dict[str, list[list[int | float]]]


class AbilityForm(TypedDict):
    """One ability variant, preserving curve points and symbolic calculations."""

    name: str
    label: str
    description: str
    curve_values: CurveValues
    attribute_calcs: dict[str, Any]
    attribute_values: dict[str, list[int | float]]
    footer: list[dict[str, Any]]


class AbilityCorrection(TypedDict):
    """A patch-note correction; source notes disclose interpretation limits."""

    field: str
    values: NotRequired[list[list[int | float]]]
    value: NotRequired[int | float]
    source_url: str


class AbilitySource(TypedDict):
    """Provenance distinguishing the reference export from verified changes."""

    name: str
    url: str
    generated: str
    patch: str
    core_hash: str
    verified_patch: str
    verification_note: str
    corrections: list[AbilityCorrection]
    patch_notes_url: str
    notes: NotRequired[list[str]]


class AbilityDetails(TypedDict):
    """The JSON payload stored alongside a CommunityDragon champion."""

    source: AbilitySource
    forms: list[AbilityForm]
    stat_corrections: NotRequired[dict[str, int | float]]
