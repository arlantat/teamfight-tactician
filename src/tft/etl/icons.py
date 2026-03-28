"""Icon URL resolution for CommunityDragon asset paths."""

from tft.config import CDRAGON_ASSET_BASE


def icon_url(tex_path: str | None) -> str | None:
    """Translate a CDragon ``.tex`` asset path to a raw PNG URL.

    Rule:
        1. Convert the path to **lowercase**.
        2. Replace ``.tex`` / ``.dds`` → ``.png``.
        3. Prepend the CDragon game-asset CDN base URL.

    Args:
        tex_path: Internal CDragon asset path
            (e.g. ``"ASSETS/Characters/Ahri/HUD/Icons2D/Ahri_Square.tex"``).

    Returns:
        Full HTTPS URL to the PNG, or ``None`` if *tex_path* is falsy.

    Examples:
        >>> icon_url("ASSETS/Characters/Ahri/HUD/Icons2D/Ahri_Square.tex")
        'https://raw.communitydragon.org/latest/game/assets/characters/ahri/hud/icons2d/ahri_square.png'

        >>> icon_url(None) is None
        True
    """
    if not tex_path:
        return None
    cleaned = tex_path.lower().replace(".tex", ".png").replace(".dds", ".png")
    return f"{CDRAGON_ASSET_BASE}{cleaned}"
