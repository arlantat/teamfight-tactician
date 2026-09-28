"""Atomic, reproducible static TFT catalog refreshes with source provenance."""

import json
import logging
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from tft.abilities import load_ability_details
from tft.config import (
    CDRAGON_METADATA_URL,
    CDRAGON_URL,
    DB_PATH,
    DEFAULT_SET_NUMBER,
    METATFT_REVIEWED_PATCH,
    METATFT_REVIEWED_SET,
    REQUEST_TIMEOUT_SECONDS,
    SET_DISPLAY_NAMES,
    STATIC_SCHEMA_PATH,
)
from tft.db.connection import get_connection, insert_rows, run_schema
from tft.db.models import StaticDataMetadata
from tft.etl.cdragon import fetch_cdragon_data, find_set, parse_champions, parse_traits
from tft.etl.items import parse_augments, parse_items

log = logging.getLogger(__name__)


def _source_version(data: dict[str, Any], *, remote: bool) -> str | None:
    """Read build provenance without conflating a CDragon build with a TFT patch."""
    version = data.get("version")
    if isinstance(version, str):
        return version
    if not remote:
        return None
    try:
        response = requests.get(CDRAGON_METADATA_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        version = response.json().get("version")
    except (requests.RequestException, ValueError, AttributeError) as exc:
        log.warning("CDragon build metadata unavailable: %s", exc)
        return None
    return version if isinstance(version, str) else None


def refresh_static_data(
    db_path: Path = DB_PATH,
    set_number: int = DEFAULT_SET_NUMBER,
    source_path: Path | None = None,
    patch: str | None = None,
    *,
    with_abilities: bool = False,
    ability_source_path: Path | None = None,
) -> StaticDataMetadata:
    """Replace the static catalog atomically while preserving harvested matches.

    Args:
        db_path: SQLite destination.
        set_number: Explicit set to select; no fallback to older releases.
        source_path: Saved CDragon JSON for repeatable, offline refreshes.
        patch: Optional verified TFT patch label; CDragon's build is separate.
        with_abilities: Include the reviewed supplemental ability reference.
        ability_source_path: Saved MetaTFT export; also enables ability enrichment.

    Returns:
        Provenance of the committed catalog.

    Raises:
        ValueError: A snapshot lacks the requested set or required catalog data.
        sqlite3.Error: The transaction failed; the previous catalog is retained.
    """
    data = (
        json.loads(source_path.read_text(encoding="utf-8")) if source_path else fetch_cdragon_data()
    )
    if not isinstance(data, dict) or not isinstance(data.get("setData"), list):
        raise ValueError("CDragon snapshot must contain a setData list")
    selected = find_set(data["setData"], set_number)
    champions = parse_champions(selected.get("champions") or [])
    if with_abilities or ability_source_path is not None:
        if f"TFTSet{set_number}" != METATFT_REVIEWED_SET or patch != METATFT_REVIEWED_PATCH:
            raise ValueError(
                f"Supplemental abilities require {METATFT_REVIEWED_SET} "
                f"and --patch {METATFT_REVIEWED_PATCH}"
            )
        details = load_ability_details(champions, ability_source_path, patch=patch)
        champions = [
            replace(
                champion,
                ability_detail=json.dumps(details.get(champion.api_name, {})),
                stats=json.dumps(
                    json.loads(champion.stats)
                    | details.get(champion.api_name, {}).get("stat_corrections", {})
                ),
            )
            for champion in champions
        ]
        log.info("Enriched %d/%d champions with sourced ability values", len(details), len(champions))
    traits = parse_traits(selected.get("traits") or [])
    if "items" not in selected or "augments" not in selected:
        raise ValueError("CDragon set is missing item/augment membership lists")
    items = parse_items(data.get("items") or [], selected["items"])
    augments = parse_augments(data.get("items") or [], selected["augments"])
    if not champions or not traits or not items:
        raise ValueError(
            "Refusing to replace the catalog with an empty champion, trait, or item list"
        )
    metadata = StaticDataMetadata(
        set_number=set_number,
        set_name=SET_DISPLAY_NAMES.get(set_number, selected.get("name") or f"Set {set_number}"),
        patch=patch,
        source_url=source_path.resolve().as_uri() if source_path else CDRAGON_URL,
        fetched_at=datetime.now(UTC).isoformat(),
        source_set_name=selected.get("name") or "",
        mutator=selected.get("mutator") or "",
        source_version=_source_version(data, remote=source_path is None),
    )
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            run_schema(conn, STATIC_SCHEMA_PATH)
            insert_rows(conn, "champions", champions, commit=False)
            insert_rows(conn, "traits", traits, commit=False)
            insert_rows(conn, "items", items, commit=False)
            insert_rows(conn, "augments", augments, commit=False)
            insert_rows(conn, "metadata", [metadata], commit=False)
    finally:
        conn.close()
    log.info(
        "Refreshed Set %d: %s (%d champions, %d traits, %d items, %d augments)",
        set_number,
        metadata.set_name,
        len(champions),
        len(traits),
        len(items),
        len(augments),
    )
    return metadata
