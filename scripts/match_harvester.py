#!/usr/bin/env python3
"""Harvest end-game match data for top Challenger and Grandmaster TFT players.

Connects to the Riot Games API, fetches league standings, and downloads
recent match details for the current game version.
Results are upserted into ``tft_data.db``.

**Multi-server support:** Before fetching, the script prompts the user to
select one or more servers (NA, EUW, KR, etc.).  Each server runs its own
harvest pass; all data is stored in the same database.

**Optimisation:** Instead of fetching match details per-player, the script
collects all match IDs first, deduplicates them, removes matches already in
the database, and then fetches only the unique, unseen match details.

Usage:
    .venv/bin/python scripts/match_harvester.py
"""

import logging
import sys
from pathlib import Path

# Ensure src/ is on sys.path for src-layout imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402 — must precede tft.config

load_dotenv()  # Load .env BEFORE tft.config reads os.environ.

from tft.config import (
    DB_PATH,
    HARVESTER_MATCH_COUNT,
    HARVESTER_TOP_CHALLENGERS,
    HARVESTER_TOP_GRANDMASTERS,
    TFT_SERVERS,
)
from tft.db.connection import get_connection, insert_rows, run_schema
from tft.etl.match_parser import (
    extract_version_prefix,
    is_current_version,
    parse_match_metadata,
    parse_match_participants,
)
from tft.riot.client import RiotClient
from tft.utils.logging import setup_logging

log = logging.getLogger(__name__)

MATCH_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "src" / "tft" / "db" / "match_schema.sql"
)


# ---------------------------------------------------------------------------
# Server selection
# ---------------------------------------------------------------------------

def _prompt_servers() -> list[str]:
    """Prompt the user to select which server(s) to harvest.

    Returns:
        List of server keys (e.g. ``["NA", "EUW"]``).
    """
    labels = list(TFT_SERVERS.keys())

    print("\n╔══════════════════════════════════════════╗")
    print("║     TFT Match Harvester — Server Select  ║")
    print("╠══════════════════════════════════════════╣")
    for i, label in enumerate(labels, start=1):
        platform, region = TFT_SERVERS[label]
        print(f"║  {i:2d}. {label:5s}  ({platform} / {region})")
    print("╠══════════════════════════════════════════╣")
    print("║   0. ALL servers                         ║")
    print("╚══════════════════════════════════════════╝")

    raw = input(
        "\nEnter server number(s) separated by commas "
        "(e.g. 1,2,4) or 0 for all: "
    ).strip()

    if raw == "0":
        log.info("Selected ALL %d servers.", len(labels))
        return labels

    selected: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(labels):
                selected.append(labels[idx])
            else:
                log.warning("Invalid index %s — skipping.", token)
        elif token.upper() in TFT_SERVERS:
            selected.append(token.upper())
        else:
            log.warning("Unknown server '%s' — skipping.", token)

    if not selected:
        log.warning("No valid servers selected — defaulting to NA.")
        selected = ["NA"]

    log.info("Selected servers: %s", ", ".join(selected))
    return selected


# ---------------------------------------------------------------------------
# Phase 1: Collect players & match IDs
# ---------------------------------------------------------------------------

def _fetch_top_entries(
    client: RiotClient,
    tier: str,
    top_n: int,
) -> list[dict]:
    """Fetch league entries, sort by LP descending, and return top *n*.

    Args:
        client: Authenticated Riot API client.
        tier: ``"challenger"`` or ``"grandmaster"``.
        top_n: Number of top players to keep.

    Returns:
        Sorted slice of league entry dicts.
    """
    entries = client.get_league(tier)
    entries.sort(key=lambda e: e.get("leaguePoints", 0), reverse=True)
    return entries[:top_n]


def _collect_match_ids(
    client: RiotClient,
    players: list[tuple[str, str]],
) -> set[str]:
    """Fetch match IDs for all players and return the unique set.

    Args:
        client: Authenticated Riot API client.
        players: List of ``(puuid, tier)`` tuples.

    Returns:
        Deduplicated set of match ID strings.
    """
    all_ids: set[str] = set()
    for idx, (puuid, _tier) in enumerate(players, start=1):
        log.info(
            "[%d/%d] Fetching match IDs for %s…",
            idx, len(players), puuid[:12],
        )
        try:
            ids = client.get_match_ids(puuid, count=HARVESTER_MATCH_COUNT)
            all_ids.update(ids)
        except Exception:
            log.warning("Failed to fetch match IDs for %s…, skipping.", puuid[:12])

    return all_ids


# ---------------------------------------------------------------------------
# Phase 2: Detect current version & fetch matches
# ---------------------------------------------------------------------------

_VERSION_SAMPLE_SIZE: int = 10
"""How many matches to sample for version detection."""


def _detect_current_version(
    client: RiotClient,
    match_ids: list[str],
) -> tuple[str, list[tuple[str, dict]]]:
    """Sample a few matches and pick the latest game version.

    Instead of trusting the first match (which might be from an old patch),
    this fetches up to ``_VERSION_SAMPLE_SIZE`` matches and selects the
    highest version prefix.

    Args:
        client: Authenticated Riot API client.
        match_ids: Full list of match IDs (we sample from the front).

    Returns:
        Tuple of (version_prefix, fetched_samples) where fetched_samples
        is a list of (match_id, match_json) already downloaded so we don't
        re-fetch them.
    """
    from collections import Counter

    sample_size = min(_VERSION_SAMPLE_SIZE, len(match_ids))
    fetched: list[tuple[str, dict]] = []
    versions: Counter[str] = Counter()

    log.info("Sampling %d matches for version detection…", sample_size)
    for mid in match_ids[:sample_size]:
        try:
            mj = client.get_match(mid)
            fetched.append((mid, mj))
            raw = mj.get("info", {}).get("game_version", "")
            vp = extract_version_prefix(raw)
            versions[vp] += 1
        except Exception:
            log.warning("Failed to fetch %s during sampling, skipping.", mid)

    if not versions:
        log.warning("Could not detect version from any sample match.")
        return "", fetched

    # Pick the highest version (lexicographic works for "X Version NN.MM").
    best = max(versions.keys())
    log.info(
        "Version detection: %s  (from %d samples: %s)",
        best, len(fetched), dict(versions),
    )
    return best, fetched


def _fetch_and_store_matches(
    client: RiotClient,
    conn,
    match_ids: list[str],
) -> tuple[int, int]:
    """Download match details and upsert into the database.

    The current game version is auto-detected by sampling multiple matches
    and selecting the latest.  Older-version matches are skipped.

    Args:
        client: Authenticated Riot API client.
        conn: Open SQLite connection.
        match_ids: List of match IDs to fetch (already deduplicated).

    Returns:
        Tuple of (matches_saved, participants_saved).
    """
    # Detect version from a sample.
    version_prefix, pre_fetched = _detect_current_version(client, match_ids)
    if not version_prefix:
        log.error("Cannot determine game version — aborting fetch.")
        return 0, 0

    matches_saved = 0
    participants_saved = 0

    # IDs already fetched during sampling — process them first.
    pre_fetched_ids = {mid for mid, _ in pre_fetched}
    for mid, match_json in pre_fetched:
        if is_current_version(match_json, version_prefix):
            match_row = parse_match_metadata(match_json)
            participant_rows = parse_match_participants(match_json)
            insert_rows(conn, "matches", [match_row])
            n = insert_rows(conn, "match_participants", participant_rows)
            matches_saved += 1
            participants_saved += n

    # Fetch remaining matches.
    remaining = [mid for mid in match_ids if mid not in pre_fetched_ids]
    for idx, mid in enumerate(remaining, start=1):
        if idx % 25 == 1 or idx == len(remaining):
            log.info(
                "Fetching match details [%d/%d] …", idx, len(remaining),
            )

        try:
            match_json = client.get_match(mid)
        except Exception:
            log.warning("Failed to fetch match %s, skipping.", mid)
            continue

        if not is_current_version(match_json, version_prefix):
            continue

        match_row = parse_match_metadata(match_json)
        participant_rows = parse_match_participants(match_json)

        insert_rows(conn, "matches", [match_row])
        n = insert_rows(conn, "match_participants", participant_rows)

        matches_saved += 1
        participants_saved += n

    return matches_saved, participants_saved


# ---------------------------------------------------------------------------
# Harvest a single server
# ---------------------------------------------------------------------------

def _harvest_server(
    server_label: str,
    conn,
) -> None:
    """Run the full harvest pipeline for one server.

    Args:
        server_label: Server key from ``TFT_SERVERS`` (e.g. ``"NA"``).
        conn: Open SQLite connection (shared across servers).
    """
    platform_id, region = TFT_SERVERS[server_label]
    platform_base = f"https://{platform_id}.api.riotgames.com"
    region_base = f"https://{region}.api.riotgames.com"

    log.info("─" * 60)
    log.info(
        "Harvesting %s  (platform=%s, region=%s)",
        server_label, platform_id, region,
    )
    log.info("─" * 60)

    client = RiotClient(platform_base=platform_base, region_base=region_base)

    # ── Phase 1a: Fetch league entries ───────────────────────────────
    chall_entries = _fetch_top_entries(
        client, "challenger", HARVESTER_TOP_CHALLENGERS,
    )
    gm_entries = _fetch_top_entries(
        client, "grandmaster", HARVESTER_TOP_GRANDMASTERS,
    )

    players: list[tuple[str, str]] = [
        (e["puuid"], "CHALLENGER") for e in chall_entries if e.get("puuid")
    ] + [
        (e["puuid"], "GRANDMASTER") for e in gm_entries if e.get("puuid")
    ]

    log.info(
        "[%s] Collected %d Challengers + %d Grandmasters = %d players.",
        server_label, len(chall_entries), len(gm_entries), len(players),
    )

    # Upsert all players.
    insert_rows(conn, "players", [
        {"puuid": puuid, "tier": tier} for puuid, tier in players
    ])

    # ── Phase 1b: Collect & deduplicate match IDs ────────────────────
    raw_ids = _collect_match_ids(client, players)
    log.info(
        "[%s] Collected %d unique match IDs from %d players.",
        server_label, len(raw_ids), len(players),
    )

    # Remove matches already in the database.
    existing = {
        row[0]
        for row in conn.execute("SELECT match_id FROM matches").fetchall()
    }
    new_ids = sorted(raw_ids - existing)
    log.info(
        "[%s] After removing %d already-stored → %d new matches to fetch.",
        server_label, len(existing), len(new_ids),
    )

    if not new_ids:
        log.info("[%s] Nothing new to fetch — all matches already stored.", server_label)
    else:
        # ── Phase 2: Fetch & store ───────────────────────────────────
        m, p = _fetch_and_store_matches(client, conn, new_ids)
        log.info(
            "[%s] Stored %d matches, %d participant rows.",
            server_label, m, p,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _purge_old_matches(conn, current_version: str) -> None:
    """Delete matches and participants from older game versions.

    Keeps only data matching *current_version* so the analysis isn't
    polluted by stale meta from previous patches.

    Args:
        conn: Open SQLite connection.
        current_version: Version prefix to keep (e.g. ``"Linux Version 16.6"``).
    """
    if not current_version:
        log.warning("No version provided — skipping purge.")
        return

    cur = conn.execute(
        "SELECT COUNT(*) FROM matches WHERE game_version NOT LIKE ?",
        (f"{current_version}%",),
    )
    old_count = cur.fetchone()[0]

    if old_count == 0:
        log.info("No old-patch matches to purge.")
        return

    log.info(
        "Purging %d matches from older patches (keeping %s*)…",
        old_count, current_version,
    )

    # Delete participants first (FK constraint), then matches.
    conn.execute(
        "DELETE FROM match_participants WHERE match_id IN "
        "(SELECT match_id FROM matches WHERE game_version NOT LIKE ?)",
        (f"{current_version}%",),
    )
    conn.execute(
        "DELETE FROM matches WHERE game_version NOT LIKE ?",
        (f"{current_version}%",),
    )
    conn.commit()
    log.info("Purge complete — removed %d old-patch matches.", old_count)


def _detect_latest_version_in_db(conn) -> str:
    """Find the latest game version prefix already stored in the DB.

    Returns:
        The highest version prefix, or empty string if no matches exist.
    """
    rows = conn.execute(
        "SELECT DISTINCT game_version FROM matches",
    ).fetchall()
    if not rows:
        return ""

    prefixes = {extract_version_prefix(r[0]) for r in rows}
    return max(prefixes) if prefixes else ""


def main() -> None:
    """Entry point — prompt for servers and harvest match data."""
    setup_logging()

    servers = _prompt_servers()

    log.info("═" * 60)
    log.info("TFT Match Harvester — starting (%d server(s))", len(servers))
    log.info(
        "  %d Challengers + %d Grandmasters per server",
        HARVESTER_TOP_CHALLENGERS, HARVESTER_TOP_GRANDMASTERS,
    )
    log.info("═" * 60)

    conn = get_connection(DB_PATH)

    try:
        run_schema(conn, MATCH_SCHEMA_PATH)

        for server_label in servers:
            _harvest_server(server_label, conn)

        # Purge old-patch data after all servers are processed.
        latest = _detect_latest_version_in_db(conn)
        if latest:
            log.info("Latest game version in DB: %s", latest)

            # Count per-version breakdown.
            ver_rows = conn.execute(
                "SELECT game_version, COUNT(*) FROM matches GROUP BY game_version",
            ).fetchall()
            for ver, cnt in ver_rows:
                prefix = extract_version_prefix(ver)
                status = "✓ current" if prefix == latest else "✗ OLD"
                log.info("  %s  (%d matches)  [%s]", prefix, cnt, status)

            _purge_old_matches(conn, latest)
        else:
            log.warning("No matches in DB — nothing to purge.")

        log.info("═" * 60)
        log.info("Harvest complete ✓  (%d server(s) processed)", len(servers))
        log.info("═" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
