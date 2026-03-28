"""Global configuration, constants, and environment helpers."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "tft_data.db"

# ---------------------------------------------------------------------------
# CommunityDragon
# ---------------------------------------------------------------------------
CDRAGON_URL = "https://raw.communitydragon.org/latest/cdragon/tft/en_us.json"
CDRAGON_ASSET_BASE = "https://raw.communitydragon.org/latest/game/"

# ---------------------------------------------------------------------------
# Riot API (future)
# ---------------------------------------------------------------------------
# RIOT_API_KEY is expected as an environment variable — never hard-coded.
# import os
# RIOT_API_KEY: str = os.environ.get("RIOT_API_KEY", "")

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 60
