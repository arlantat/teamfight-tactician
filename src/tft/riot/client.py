"""Rate-limited Riot TFT client with validated source response boundaries."""

import logging
import time
from types import TracebackType
from typing import Any, cast
from urllib.parse import quote

import requests

from tft.config import (
    HARVESTER_MATCH_COUNT,
    REQUEST_TIMEOUT_SECONDS,
    RIOT_API_KEY,
    RIOT_BACKOFF_BASE_SECONDS,
    RIOT_BACKOFF_MAX_RETRIES,
    RIOT_MATCH_COUNT_MAX,
    RIOT_PLATFORM_BASE,
    RIOT_RATE_LONG_LIMIT,
    RIOT_RATE_LONG_WINDOW,
    RIOT_RATE_SHORT_LIMIT,
    RIOT_RATE_SHORT_WINDOW,
    RIOT_REGION_BASE,
)
from tft.exceptions import RiotApiError
from tft.riot.models import LeagueEntry, MatchPayload
from tft.riot.rate_limiter import RateLimiter

log = logging.getLogger(__name__)


class RiotClient:
    """Own an authenticated HTTP session for TFT platform and regional routes."""

    def __init__(
        self,
        api_key: str = "",
        platform_base: str = "",
        region_base: str = "",
        limiter: RateLimiter | None = None,
    ) -> None:
        """Configure routes and optionally share the key's request limiter."""
        api_key = api_key or RIOT_API_KEY
        if not api_key:
            raise RiotApiError("RIOT_API_KEY is not set. Export it or add it to your .env file.")
        self._platform_base = platform_base or RIOT_PLATFORM_BASE
        self._region_base = region_base or RIOT_REGION_BASE
        self._session = requests.Session()
        self._session.headers["X-Riot-Token"] = api_key
        self._limiter = limiter or RateLimiter(
            short_limit=RIOT_RATE_SHORT_LIMIT,
            short_window=RIOT_RATE_SHORT_WINDOW,
            long_limit=RIOT_RATE_LONG_LIMIT,
            long_window=RIOT_RATE_LONG_WINDOW,
        )

    def close(self) -> None:
        """Release the session and its connection pool."""
        self._session.close()

    def __enter__(self) -> "RiotClient":
        """Return this client for an explicitly bounded session lifetime."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the session, including when the caller raises."""
        self.close()

    def _get(self, url: str) -> Any:
        """Request JSON with bounded retries, without exposing auth headers."""
        for attempt in range(RIOT_BACKOFF_MAX_RETRIES):
            self._limiter.acquire()
            response: requests.Response | None = None
            try:
                response = self._session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
                try:
                    response.raise_for_status()
                except requests.HTTPError:
                    if response.status_code != 429:
                        raise
                    if attempt + 1 == RIOT_BACKOFF_MAX_RETRIES:
                        raise RiotApiError("Riot rate limit retries exhausted") from None
                    try:
                        delay = float(response.headers.get("Retry-After", ""))
                    except ValueError:
                        delay = RIOT_BACKOFF_BASE_SECONDS * 2 ** attempt
                    log.warning("Riot rate limit reached; retrying in %.1fs", delay)
                    time.sleep(max(0.0, delay))
                    continue
                return response.json()
            except requests.RequestException as exc:
                status = exc.response.status_code if exc.response is not None else "network"
                raise RiotApiError(f"Riot request failed ({status})") from None
            finally:
                if response is not None:
                    response.close()
        raise RiotApiError("Riot request retries exhausted")

    def get_league(self, tier: str) -> list[LeagueEntry]:
        """Read league entries containing PUUIDs directly from a ranked league."""
        tier = tier.lower()
        if tier not in {"challenger", "grandmaster", "master"}:
            raise ValueError("Unsupported league tier")
        payload = self._get(f"{self._platform_base}/tft/league/v1/{tier}")
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list) or any(
            not isinstance(entry, dict)
            or not isinstance(entry.get("puuid"), str)
            or not entry["puuid"]
            or not isinstance(entry.get("leaguePoints"), int)
            for entry in entries
        ):
            raise RiotApiError("League response is missing valid PUUID/LP entries")
        return cast(list[LeagueEntry], entries)

    def get_match_ids(self, puuid: str, count: int = HARVESTER_MATCH_COUNT) -> list[str]:
        """Read a bounded list of recent match IDs using regional routing."""
        if not 1 <= count <= RIOT_MATCH_COUNT_MAX:
            raise ValueError(f"Match count must be 1–{RIOT_MATCH_COUNT_MAX}")
        url = (
            f"{self._region_base}/tft/match/v1/matches/by-puuid/"
            f"{quote(puuid, safe='')}/ids?count={count}"
        )
        payload = self._get(url)
        if not isinstance(payload, list) or any(not isinstance(mid, str) for mid in payload):
            raise RiotApiError("Match history response must contain match ID strings")
        return payload

    def get_match(self, match_id: str) -> MatchPayload:
        """Read match JSON; the parser validates fields before persistence."""
        url = f"{self._region_base}/tft/match/v1/matches/{quote(match_id, safe='')}"
        payload = self._get(url)
        if not isinstance(payload, dict) or any(
            not isinstance(payload.get(key), dict) for key in ("metadata", "info")
        ):
            raise RiotApiError("Match response is missing metadata or info")
        return cast(MatchPayload, payload)
