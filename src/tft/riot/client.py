"""Riot API client for TFT league and match endpoints.

All requests flow through :class:`RiotClient`, which binds a
:class:`~tft.riot.rate_limiter.RateLimiter` and handles 429 back-off so
callers never need to worry about rate limits.

.. note::
    The Riot API evolves frequently.  League entries now include ``puuid``
    directly — the old ``summonerId`` / ``summonerName`` fields have been
    removed.  Always inspect a live API response when debugging field-level
    issues.
"""

import logging
import time
from typing import Any

import requests

from tft.config import (
    REQUEST_TIMEOUT_SECONDS,
    RIOT_API_KEY,
    RIOT_PLATFORM_BASE,
    RIOT_RATE_LONG_LIMIT,
    RIOT_RATE_LONG_WINDOW,
    RIOT_RATE_SHORT_LIMIT,
    RIOT_RATE_SHORT_WINDOW,
    RIOT_REGION_BASE,
)
from tft.riot.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

# Exponential back-off tunables for 429 retries.
_BACKOFF_BASE_SECONDS: float = 1.0
_BACKOFF_MAX_RETRIES: int = 5


class RiotApiError(Exception):
    """Raised when the Riot API returns an unexpected error."""


class RiotClient:
    """Thin wrapper around the Riot Games TFT API.

    Args:
        api_key: Riot API key.  Falls back to :data:`tft.config.RIOT_API_KEY`.
        platform_base: Base URL for platform-scoped endpoints.
        region_base: Base URL for regional-scoped endpoints.
    """

    def __init__(
        self,
        api_key: str = "",
        platform_base: str = "",
        region_base: str = "",
    ) -> None:
        self._api_key = api_key or RIOT_API_KEY
        if not self._api_key:
            raise RiotApiError(
                "RIOT_API_KEY is not set.  Export it or add it to your .env file."
            )

        self._platform_base = platform_base or RIOT_PLATFORM_BASE
        self._region_base = region_base or RIOT_REGION_BASE

        self._session = requests.Session()
        self._session.headers["X-Riot-Token"] = self._api_key

        self._limiter = RateLimiter(
            short_limit=RIOT_RATE_SHORT_LIMIT,
            short_window=RIOT_RATE_SHORT_WINDOW,
            long_limit=RIOT_RATE_LONG_LIMIT,
            long_window=RIOT_RATE_LONG_WINDOW,
        )

    # ------------------------------------------------------------------
    # Core HTTP
    # ------------------------------------------------------------------

    def _get(self, url: str) -> Any:
        """Rate-limited GET with exponential back-off on 429.

        Args:
            url: Fully-qualified API URL.

        Returns:
            Parsed JSON response body.

        Raises:
            RiotApiError: After exhausting retries on 429.
            requests.HTTPError: On non-429 HTTP errors.
        """
        for attempt in range(_BACKOFF_MAX_RETRIES):
            self._limiter.acquire()
            resp = self._session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)

            if resp.status_code != 429:
                resp.raise_for_status()
                return resp.json()

            # 429 — honour Retry-After header, else exponential back-off.
            retry_after = resp.headers.get("Retry-After")
            delay = (
                float(retry_after)
                if retry_after
                else _BACKOFF_BASE_SECONDS * (2 ** attempt)
            )
            log.warning(
                "429 rate-limited (attempt %d/%d), sleeping %.1fs …",
                attempt + 1,
                _BACKOFF_MAX_RETRIES,
                delay,
            )
            time.sleep(delay)

        raise RiotApiError(
            f"Exhausted {_BACKOFF_MAX_RETRIES} retries on 429 for {url}"
        )

    # ------------------------------------------------------------------
    # League endpoints (platform-scoped)
    # ------------------------------------------------------------------

    def get_league(self, tier: str) -> list[dict[str, Any]]:
        """Fetch the full league entries list for *tier*.

        As of 2026 the response entries contain ``puuid`` directly — the old
        ``summonerId`` and ``summonerName`` fields have been removed.

        Args:
            tier: ``"challenger"`` or ``"grandmaster"`` (case-insensitive).

        Returns:
            List of entry dicts, each containing at least ``puuid`` and
            ``leaguePoints``.
        """
        tier_lower = tier.lower()
        url = f"{self._platform_base}/tft/league/v1/{tier_lower}"
        data = self._get(url)
        entries: list[dict[str, Any]] = data.get("entries", [])
        log.info("Fetched %d %s entries.", len(entries), tier_lower)
        return entries

    # ------------------------------------------------------------------
    # Match endpoints (region-scoped)
    # ------------------------------------------------------------------

    def get_match_ids(self, puuid: str, count: int = 15) -> list[str]:
        """Fetch recent match IDs for a player.

        Args:
            puuid: Player UUID.
            count: Number of match IDs to retrieve (max 100).

        Returns:
            List of match ID strings (e.g. ``"NA1_12345"``).
        """
        url = (
            f"{self._region_base}/tft/match/v1/matches/by-puuid"
            f"/{puuid}/ids?count={count}"
        )
        return self._get(url)

    def get_match(self, match_id: str) -> dict[str, Any]:
        """Fetch the full match detail JSON.

        Args:
            match_id: A match ID string.

        Returns:
            Complete match data dict.
        """
        url = f"{self._region_base}/tft/match/v1/matches/{match_id}"
        return self._get(url)
