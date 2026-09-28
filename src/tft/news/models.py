"""Typed records for Riot's public TFT news listing and patch-note pages."""

from dataclasses import dataclass
from typing import Any, TypedDict


class Heading(TypedDict):
    """A heading taken from official patch notes, not the article body."""

    level: int
    text: str


class ListingCard(TypedDict):
    """One news card from the TFT game-updates listing."""

    content_id: str
    url: str
    title: str
    description: str
    published_at: str
    revision: str
    kind: str
    image_url: str | None


class NewsPayload(TypedDict):
    """JSON returned to the browser for the patch-notes view."""

    source_url: str
    fetched_at: str
    stale: bool
    articles: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class NewsArticleRow:
    """Cached official article metadata that survives catalog refreshes."""

    content_id: str
    url: str
    title: str
    description: str
    published_at: str
    revision: str
    listing_revision: str
    kind: str
    image_url: str | None
    headings: str
    fetched_at: str
