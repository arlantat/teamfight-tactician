"""Global configuration, constants, and environment helpers."""

import os
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
# Riot API
# ---------------------------------------------------------------------------
# Key is expected as an environment variable — never hard-coded.
RIOT_API_KEY: str = os.environ.get("RIOT_API_KEY", "")

# Default platform / region (used when no server is explicitly selected).
RIOT_PLATFORM: str = os.environ.get("RIOT_PLATFORM", "na1")
RIOT_REGION: str = os.environ.get("RIOT_REGION", "americas")

RIOT_PLATFORM_BASE: str = f"https://{RIOT_PLATFORM}.api.riotgames.com"
RIOT_REGION_BASE: str = f"https://{RIOT_REGION}.api.riotgames.com"

# Rate limits (Riot development key defaults)
RIOT_RATE_SHORT_LIMIT: int = 20       # requests per short window
RIOT_RATE_SHORT_WINDOW: float = 1.0   # seconds
RIOT_RATE_LONG_LIMIT: int = 100       # requests per long window
RIOT_RATE_LONG_WINDOW: float = 120.0  # seconds

# ---------------------------------------------------------------------------
# Available TFT servers
# ---------------------------------------------------------------------------
# Each entry maps a short label to (platform_id, region).
# Platform = league/summoner endpoints;  Region = match endpoints.
TFT_SERVERS: dict[str, tuple[str, str]] = {
    "NA":   ("na1",  "americas"),
    "EUW":  ("euw1", "europe"),
    "EUNE": ("eun1", "europe"),
    "KR":   ("kr",   "asia"),
    "JP":   ("jp1",  "asia"),
    "OCE":  ("oc1",  "sea"),
    "BR":   ("br1",  "americas"),
    "LAN":  ("la1",  "americas"),
    "LAS":  ("la2",  "americas"),
    "TR":   ("tr1",  "europe"),
    "PH":   ("ph2",  "sea"),
    "SG":   ("sg2",  "sea"),
    "TH":   ("th2",  "sea"),
    "TW":   ("tw2",  "sea"),
    "VN":   ("vn2",  "sea"),
}

# ---------------------------------------------------------------------------
# Harvester tunables
# ---------------------------------------------------------------------------
HARVESTER_TOP_CHALLENGERS: int = 100
HARVESTER_TOP_GRANDMASTERS: int = 150
HARVESTER_MATCH_COUNT: int = 15

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 15
