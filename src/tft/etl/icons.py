"""Resolve CommunityDragon texture paths and existing HTTPS image URLs."""

import re
from urllib.parse import urlsplit, urlunsplit

from tft.config import CDRAGON_ASSET_BASE


def icon_url(tex_path: str | None) -> str | None:
    """Convert a CDragon texture path into an HTTPS image URL.

    Args:
        tex_path: Internal asset path or an already resolved HTTP(S) URL.

    Returns:
        A PNG asset URL, or None for an empty or unsupported URI.
    """
    if not tex_path or tex_path.strip().lower() in {"", "none", "null"}:
        return None
    path = tex_path.strip().replace("\\", "/")
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"", "http", "https"} or not parsed.netloc:
            return None
        image_path = re.sub(r"\.(tex|dds)$", ".png", parsed.path, flags=re.IGNORECASE)
        return urlunsplit(("https", parsed.netloc, image_path, parsed.query, parsed.fragment))
    cleaned = re.sub(r"\.(tex|dds)$", ".png", parsed.path.lower().lstrip("/"))
    return f"{CDRAGON_ASSET_BASE}{cleaned}"
