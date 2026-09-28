"""Load a reviewed MetaTFT reference export without claiming live verification."""

import json
import logging
from pathlib import Path
from typing import Any

import requests

from tft.abilities.corrections import apply_corrections
from tft.abilities.forms import build_forms, index_units
from tft.abilities.models import AbilityDetails, AbilitySource
from tft.config import (
    METATFT_ABILITY_URL,
    METATFT_REVIEWED_CORE_HASH,
    METATFT_REVIEWED_PATCH,
    METATFT_REVIEWED_SET,
    REQUEST_TIMEOUT_SECONDS,
    RIOT_ABILITY_PATCH_NOTES_URL,
)
from tft.db.models import ChampionRow

log = logging.getLogger(__name__)

_SOURCE_NOTES: dict[str, list[str]] = {
    "TFT18_Ashe": [
        "The source describes arrow damage as reduced by its falloff value, but "
        "whether that value means damage lost or retained is unverified. The "
        "display preserves the source value without inverting it."
    ],
    "TFT18_Brambleback": [
        "The patch changes the flat Armor ignore constant to 20%; applying this "
        "constant at every star level is inferred from that wording. The AP term "
        "changes to 25% at 1 and 2 stars; the source's 70% at 3 stars and 80% at "
        "4 stars are retained because those levels were not listed."
    ],
}


def load_ability_details(
    champions: list[ChampionRow],
    source_path: Path | None = None,
    *,
    patch: str | None = METATFT_REVIEWED_PATCH,
) -> dict[str, AbilityDetails]:
    """Load supplemental numeric abilities for exact CommunityDragon asset IDs.

    Args:
        champions: The selected CommunityDragon roster.
        source_path: Optional local reference export for reproducible updates.
        patch: Target TFT patch; only the reviewed 18.2 reference is supported.

    Returns:
        Payloads keyed by the original champion API names. Unknown or ambiguous
        variant matches are skipped and logged, without guessing unit identity.

    Raises:
        ValueError: The source set, fingerprint, target patch, or shape is not
            supported. A newer PBE export requires review before ingestion.
        requests.RequestException: The source could not be downloaded.
    """
    data = _read_source(source_path)
    metadata = _validate_source(data, patch)
    units = index_units(data)
    details: dict[str, AbilityDetails] = {}
    for champion in champions:
        unit = units.get(champion.api_name)
        if unit is None:
            log.warning("No exact supplemental ability match for %s", champion.api_name)
            continue
        forms = build_forms(champion, unit)
        if not forms:
            log.warning("No unambiguous ability form for %s", champion.api_name)
            continue
        source: AbilitySource = {
            "name": "MetaTFT",
            "url": METATFT_ABILITY_URL,
            "generated": metadata["generated"],
            "patch": metadata["patch"],
            "core_hash": metadata["coreHash"],
            "verified_patch": METATFT_REVIEWED_PATCH,
            "verification_note": (
                "Reference dataset marked PBE. Main patch 18.2 ability changes "
                "were cross-checked with Riot's notes, and the listed September 14 "
                "corrections were applied. Other values have not been independently "
                "verified against the live client."
            ),
            "corrections": apply_corrections(unit["apiName"], forms),
            "patch_notes_url": RIOT_ABILITY_PATCH_NOTES_URL,
        }
        if notes := _SOURCE_NOTES.get(unit["apiName"]):
            source["notes"] = list(notes)
        details[champion.api_name] = {"source": source, "forms": forms}
        if unit["apiName"] == "TFT18_Maokai":
            stats = {"mana": 100, "initialMana": 30}
            details[champion.api_name]["stat_corrections"] = stats
            source["corrections"].extend(
                {
                    "field": f"stats.{field}",
                    "value": value,
                    "source_url": RIOT_ABILITY_PATCH_NOTES_URL,
                }
                for field, value in stats.items()
            )
    log.info(
        "Supplemental ability coverage: %d/%d champions, %d forms (reference export: %s)",
        len(details),
        len(champions),
        sum(len(detail["forms"]) for detail in details.values()),
        metadata["patch"],
    )
    return details


def _read_source(source_path: Path | None) -> dict[str, Any]:
    """Read one JSON reference export with HTTP and top-level validation."""
    if source_path is not None:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    else:
        response = requests.get(METATFT_ABILITY_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Ability source must be a JSON object")
    return data


def _validate_source(data: dict[str, Any], patch: str | None) -> dict[str, str]:
    """Fail closed when a different export could invalidate reviewed corrections."""
    metadata = data.get("_metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Ability source has no metadata")
    expected = {
        "set": METATFT_REVIEWED_SET,
        "coreHash": METATFT_REVIEWED_CORE_HASH,
        "patch": "pbe",
    }
    if patch != METATFT_REVIEWED_PATCH or any(
        metadata.get(field) != value for field, value in expected.items()
    ):
        raise ValueError(
            "Ability reference is not reviewed for the requested patch; "
            "expected the known Set 18 PBE fingerprint with Riot 18.2 corrections"
        )
    if not isinstance(metadata.get("generated"), str) or not metadata["generated"]:
        raise ValueError("Ability source has no generation timestamp")
    return metadata
