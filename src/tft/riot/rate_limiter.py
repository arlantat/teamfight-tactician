"""Strict dual-window rate limiter for the Riot Games API.

Riot enforces two concurrent rate limits on development keys:

    - **Short window**: 20 requests per 1 second
    - **Long window**: 100 requests per 2 minutes

This module provides a :class:`RateLimiter` that tracks request timestamps in
two sliding windows and sleeps preemptively to guarantee neither limit is ever
exceeded.
"""

import logging
import time
from collections import deque

log = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window rate limiter with dual short/long windows.

    Args:
        short_limit: Max requests allowed in the short window.
        short_window: Duration of the short window in seconds.
        long_limit: Max requests allowed in the long window.
        long_window: Duration of the long window in seconds.
    """

    def __init__(
        self,
        short_limit: int = 20,
        short_window: float = 1.0,
        long_limit: int = 100,
        long_window: float = 120.0,
    ) -> None:
        self._short_limit = short_limit
        self._short_window = short_window
        self._long_limit = long_limit
        self._long_window = long_window

        self._short_timestamps: deque[float] = deque()
        self._long_timestamps: deque[float] = deque()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Block until a request slot is available in both windows.

        Call this **before** every outbound HTTP request.  It will sleep
        for the minimum time necessary to stay within both rate limits.
        """
        while True:
            now = time.monotonic()
            self._purge(now)

            short_delay = self._delay_for(
                self._short_timestamps, self._short_limit, self._short_window, now,
            )
            long_delay = self._delay_for(
                self._long_timestamps, self._long_limit, self._long_window, now,
            )
            delay = max(short_delay, long_delay)

            if delay <= 0:
                break

            window = "short" if short_delay >= long_delay else "long"
            limit = self._short_limit if window == "short" else self._long_limit
            used = (
                len(self._short_timestamps) if window == "short"
                else len(self._long_timestamps)
            )
            log.info(
                "Rate limiter: %d/%d calls used (%s window), "
                "sleeping %.1fs…",
                used, limit, window, delay,
            )
            time.sleep(delay)

        now = time.monotonic()
        self._short_timestamps.append(now)
        self._long_timestamps.append(now)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _purge(self, now: float) -> None:
        """Remove timestamps older than each window's duration."""
        short_cutoff = now - self._short_window
        while self._short_timestamps and self._short_timestamps[0] < short_cutoff:
            self._short_timestamps.popleft()

        long_cutoff = now - self._long_window
        while self._long_timestamps and self._long_timestamps[0] < long_cutoff:
            self._long_timestamps.popleft()

    @staticmethod
    def _delay_for(
        timestamps: deque[float],
        limit: int,
        window: float,
        now: float,
    ) -> float:
        """Return seconds to sleep before the next request is allowed.

        Args:
            timestamps: Deque of request timestamps within the window.
            limit: Maximum allowed requests in the window.
            window: Window duration in seconds.
            now: Current monotonic time.

        Returns:
            Seconds to wait (0.0 if a slot is available immediately).
        """
        if len(timestamps) < limit:
            return 0.0
        # The oldest request in a full window determines when a slot opens.
        oldest = timestamps[0]
        return (oldest + window) - now
