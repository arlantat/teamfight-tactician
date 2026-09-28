"""Download Riot's public TFT news HTML."""

import logging

import requests

from tft.config import NEWS_USER_AGENT, REQUEST_TIMEOUT_SECONDS
from tft.exceptions import NewsSourceError

log = logging.getLogger(__name__)


def fetch_html(url: str) -> str:
    """Return the HTML of one public news page.

    Args:
        url: Absolute Riot or YouTube URL. Only Riot HTML pages should be passed.

    Returns:
        Raw HTML text.

    Raises:
        NewsSourceError: The page could not be downloaded.
    """
    log.info("Fetching official TFT news from %s", url)
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": NEWS_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise NewsSourceError("Official TFT news could not be downloaded") from exc
    return response.text
