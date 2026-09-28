"""Parse Riot's public TFT news pages without copying article bodies."""

import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

from tft.exceptions import NewsSourceError
from tft.news.models import Heading, ListingCard

_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)
_PATCH_TITLE = re.compile(
    r"(?:teamfight tactics|tft)\s+patch\s+(\d+\.\d+)",
    re.IGNORECASE,
)
_MIDPATCH = re.compile(r"mid[\s-]?patch", re.IGNORECASE)
_MONTH_HEADING = re.compile(
    r"^(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d",
    re.IGNORECASE,
)
_RUNDOWN = re.compile(r"rundown", re.IGNORECASE)


class _HeadingParser(HTMLParser):
    """Collect visible h2–h4 text from official patch-note HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._tag: str | None = None
        self._chunks: list[str] = []
        self.headings: list[Heading] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h2", "h3", "h4"}:
            self._tag = tag
            self._chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag != self._tag:
            return
        text = re.sub(r"\s+", " ", unescape(" ".join(self._chunks))).strip()
        if text:
            self.headings.append({"level": int(tag[1]), "text": text})
        self._tag = None

    def handle_data(self, data: str) -> None:
        if self._tag is not None:
            self._chunks.append(data)


def extract_next_data(html: str) -> dict[str, object]:
    """Read the Next.js payload Riot embeds in public news HTML."""
    match = _NEXT_DATA.search(html)
    if not match:
        raise NewsSourceError("Riot news page is missing its structured payload")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise NewsSourceError("Riot news page payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise NewsSourceError("Riot news page payload must be an object")
    return payload


def strip_html(value: str) -> str:
    """Turn a CMS HTML excerpt into plain text."""
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def classify_kind(title: str, tags: list[str]) -> str:
    """Label official patch notes, video rundowns, and other game updates."""
    names = {tag.lower() for tag in tags}
    if _RUNDOWN.search(title) and "patch_notes" not in names:
        return "rundown"
    if "patch_notes" in names or _PATCH_TITLE.search(title):
        return "patch_notes"
    return "other"


def patch_label(title: str) -> str | None:
    """Read a TFT patch number from an official title when present."""
    match = _PATCH_TITLE.search(title)
    return match.group(1) if match else None


def heading_outline(body: str) -> list[Heading]:
    """Keep section titles only; the copyrighted article body is discarded."""
    parser = _HeadingParser()
    parser.feed(body)
    parser.close()
    return parser.headings


def mid_patch_labels(headings: list[Heading]) -> list[str]:
    """Return official mid-patch headings, including dated hotfix sections."""
    labels: list[str] = []
    seen: set[str] = set()
    for heading in headings:
        text = heading["text"]
        if not (_MIDPATCH.search(text) or _MONTH_HEADING.search(text)):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        labels.append(text)
    return labels


def parse_listing(html: str, origin: str) -> list[ListingCard]:
    """Read TFT game-update cards from the public listing page."""
    page = _page_object(extract_next_data(html))
    items = _listing_items(page)
    cards: list[ListingCard] = []
    seen: set[str] = set()
    for item in items:
        card = _listing_card(item, origin)
        if card is None or card["content_id"] in seen:
            continue
        seen.add(card["content_id"])
        cards.append(card)
    if not cards:
        raise NewsSourceError("Riot news listing contained no articles")
    return cards


def parse_article(html: str) -> tuple[str, list[Heading]]:
    """Return the article revision and heading outline from a patch-notes page."""
    page = _page_object(extract_next_data(html))
    analytics = page.get("analytics")
    revision = ""
    if isinstance(analytics, dict) and isinstance(analytics.get("rev"), str):
        revision = analytics["rev"]
    body = _patch_notes_body(page)
    return revision, heading_outline(body) if body else []


def _page_object(payload: dict[str, object]) -> dict[str, object]:
    props = payload.get("props")
    if not isinstance(props, dict):
        raise NewsSourceError("Riot news payload is missing page props")
    page_props = props.get("pageProps")
    if not isinstance(page_props, dict):
        raise NewsSourceError("Riot news payload is missing page props")
    page = page_props.get("page")
    if not isinstance(page, dict):
        raise NewsSourceError("Riot news payload is missing page content")
    return page


def _listing_items(page: dict[str, object]) -> list[dict[str, object]]:
    blades = page.get("blades")
    if not isinstance(blades, list):
        raise NewsSourceError("Riot news listing is missing its article grid")
    for blade in blades:
        if not isinstance(blade, dict) or blade.get("type") != "articleCardGrid":
            continue
        items = blade.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    raise NewsSourceError("Riot news listing is missing its article grid")


def _listing_card(item: dict[str, object], origin: str) -> ListingCard | None:
    title = item.get("title")
    published = item.get("publishedAt")
    analytics = item.get("analytics")
    action = item.get("action")
    if not isinstance(title, str) or not title:
        return None
    if not isinstance(published, str) or not published:
        return None
    if not isinstance(analytics, dict):
        return None
    content_id = analytics.get("contentId")
    revision = analytics.get("rev")
    if not isinstance(content_id, str) or not content_id:
        return None
    if not isinstance(revision, str) or not revision:
        return None
    path = _action_url(action)
    if not path:
        return None
    description = ""
    raw_description = item.get("description")
    if isinstance(raw_description, dict) and isinstance(raw_description.get("body"), str):
        description = strip_html(raw_description["body"])
    tags = _tag_names(item.get("tags"))
    image = _image_url(item.get("media"))
    return {
        "content_id": content_id,
        "url": urljoin(origin.rstrip("/") + "/", path.lstrip("/")),
        "title": title.strip(),
        "description": description,
        "published_at": published,
        "revision": revision,
        "kind": classify_kind(title, tags),
        "image_url": image,
    }


def _action_url(action: object) -> str | None:
    if not isinstance(action, dict):
        return None
    payload = action.get("payload")
    if not isinstance(payload, dict):
        return None
    url = payload.get("url")
    return url if isinstance(url, str) and url else None


def _tag_names(tags: object) -> list[str]:
    if not isinstance(tags, list):
        return []
    names: list[str] = []
    for tag in tags:
        if isinstance(tag, dict) and isinstance(tag.get("machineName"), str):
            names.append(tag["machineName"])
    return names


def _image_url(media: object) -> str | None:
    if isinstance(media, dict) and isinstance(media.get("url"), str) and media["url"]:
        return media["url"]
    return None


def _patch_notes_body(page: dict[str, object]) -> str:
    blades = page.get("blades")
    if not isinstance(blades, list):
        return ""
    for blade in blades:
        if not isinstance(blade, dict) or blade.get("type") != "patchNotesRichText":
            continue
        rich = blade.get("richText")
        if isinstance(rich, dict) and isinstance(rich.get("body"), str):
            return rich["body"]
    return ""
