"""Bounded ranked TFT harvesting with set filtering and resumable storage."""

import logging
import sqlite3
from pathlib import Path

from tft.config import DB_PATH, RIOT_API_URL_TEMPLATE, RIOT_RANKED_QUEUE_ID, TFT_SERVERS
from tft.db.connection import get_connection
from tft.db.models import PlayerRow
from tft.etl.match_parser import parse_match_metadata, parse_match_participants
from tft.exceptions import MatchDataError, RiotApiError
from tft.riot.client import RiotClient
from tft.riot.models import HarvestOptions, HarvestResult
from tft.riot.rate_limiter import RateLimiter
from tft.riot.storage import complete_match_ids, migrate_match_schema, store_match, store_players

log = logging.getLogger(__name__)


def _ranked_players(client: RiotClient, options: HarvestOptions) -> list[PlayerRow]:
    """Collect top players by LP, retaining verified tiers and unique PUUIDs."""
    players: dict[str, PlayerRow] = {}
    for tier, count in (("challenger", options.challengers), ("grandmaster", options.grandmasters)):
        if count == 0:
            continue
        entries = sorted(client.get_league(tier), key=lambda entry: entry["leaguePoints"], reverse=True)
        for entry in entries[:count]:
            players.setdefault(entry["puuid"], PlayerRow(entry["puuid"], tier.upper()))
    return list(players.values())


def harvest_server(
    client: RiotClient,
    conn: sqlite3.Connection,
    options: HarvestOptions,
    result: HarvestResult,
) -> None:
    """Collect one server's recent matches; continue after individual failures.

    League discovery failures propagate because an expired or invalid key must
    not be reported as a successful empty harvest. Unknown game versions are
    accepted when the actual set and ranked queue match the requested scope.
    """
    players = _ranked_players(client, options)
    store_players(conn, players)
    result.players += len(players)
    match_ids: set[str] = set()
    for player in players:
        try:
            match_ids.update(client.get_match_ids(player.puuid, options.matches_per_player))
        except RiotApiError as exc:
            result.request_failures += 1
            log.warning("Unable to fetch one player's match history: %s", exc)
    complete = complete_match_ids(conn, options.set_number, RIOT_RANKED_QUEUE_ID)
    result.matches_skipped += len(match_ids & complete)
    for match_id in sorted(match_ids - complete):
        try:
            payload = client.get_match(match_id)
            match = parse_match_metadata(payload)
            if match.match_id != match_id:
                raise MatchDataError("Response match ID differs from requested match")
            if match.set_number != options.set_number or match.queue_id != RIOT_RANKED_QUEUE_ID:
                result.matches_skipped += 1
                continue
            participants = parse_match_participants(payload)
            count = store_match(conn, match, participants)
        except (RiotApiError, MatchDataError) as exc:
            result.request_failures += 1
            log.warning("Skipped match %s: %s", match_id, exc)
            continue
        result.matches_saved += 1
        result.participants_saved += count


def harvest_matches(options: HarvestOptions, db_path: Path = DB_PATH) -> HarvestResult:
    """Harvest explicitly selected servers while owning connections and sessions.

    Returns:
        Sample counts and recoverable request failures. Existing matches from
        other sets and patches are preserved.
    """
    result = HarvestResult()
    limiter = RateLimiter()
    conn = get_connection(db_path)
    try:
        migrate_match_schema(conn)
        for server in dict.fromkeys(options.servers):
            platform, region = TFT_SERVERS[server]
            log.info("Harvesting %s ranked Set %d matches", server, options.set_number)
            with RiotClient(
                platform_base=RIOT_API_URL_TEMPLATE.format(routing=platform),
                region_base=RIOT_API_URL_TEMPLATE.format(routing=region),
                limiter=limiter,
            ) as client:
                harvest_server(client, conn, options, result)
    finally:
        conn.close()
    log.info(
        "Harvest complete: %d players, %d matches, %d participants, %d skipped, %d failures",
        result.players, result.matches_saved, result.participants_saved,
        result.matches_skipped, result.request_failures,
    )
    return result
