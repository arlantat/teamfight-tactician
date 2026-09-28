"""Specific errors raised by data sources and validation boundaries."""


class RiotApiError(RuntimeError):
    """A Riot request failed or returned an unexpected response shape."""


class MatchDataError(ValueError):
    """A match cannot be stored safely because required data is malformed."""


class NewsSourceError(RuntimeError):
    """Riot's public TFT news page could not be read or had an unexpected shape."""


class ExplorerQueryError(ValueError):
    """An explorer filter request is malformed or exceeds the supported limits."""
