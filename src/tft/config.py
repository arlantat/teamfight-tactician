"""Global configuration, constants, and environment helpers."""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DB_PATH = Path(os.environ.get("TFT_DB_PATH", str(PROJECT_ROOT / "tft_data.db"))).expanduser()

# ---------------------------------------------------------------------------
# CommunityDragon
# ---------------------------------------------------------------------------
CDRAGON_URL = "https://raw.communitydragon.org/latest/cdragon/tft/en_us.json"
CDRAGON_ASSET_BASE = "https://raw.communitydragon.org/latest/game/"

# Reviewed supplemental ability export. Its PBE source label is preserved.
METATFT_ABILITY_URL = "https://data.metatft.com/lookups/TFTSet18_latest_en_us.json"
METATFT_REVIEWED_CORE_HASH = "ccee3f1e362438afba5c6be67f4a8104b248e960"
METATFT_REVIEWED_PATCH = "18.2"
METATFT_REVIEWED_SET = "TFTSet18"
RIOT_ABILITY_PATCH_NOTES_URL = (
    "https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/"
    "teamfight-tactics-patch-18-2/"
)
NEWS_SITE_ORIGIN = "https://teamfighttactics.leagueoflegends.com"
NEWS_LISTING_URL = f"{NEWS_SITE_ORIGIN}/en-us/news/game-updates/"
NEWS_CACHE_TTL_SECONDS = 30 * 60
NEWS_FEED_LIMIT = 12
NEWS_PATCH_ARTICLE_LIMIT = 2
NEWS_USER_AGENT = (
    "Mozilla/5.0 (compatible; TeamfightTactician/0.2; "
    "+https://github.com/arlantat/teamfight-tactician)"
)
NEWS_SCHEMA_PATH = Path(__file__).resolve().parent / "db" / "news_schema.sql"

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
RIOT_RATE_SHORT_LIMIT: int = 20  # requests per short window
RIOT_RATE_SHORT_WINDOW: float = 1.0  # seconds
RIOT_RATE_LONG_LIMIT: int = 100  # requests per long window
RIOT_RATE_LONG_WINDOW: float = 120.0  # seconds

# ---------------------------------------------------------------------------
# Available TFT servers
# ---------------------------------------------------------------------------
# Each entry maps a short label to (platform_id, region).
# Platform = league/summoner endpoints;  Region = match endpoints.
TFT_SERVERS: dict[str, tuple[str, str]] = {
    "NA": ("na1", "americas"),
    "EUW": ("euw1", "europe"),
    "EUNE": ("eun1", "europe"),
    "KR": ("kr", "asia"),
    "JP": ("jp1", "asia"),
    "OCE": ("oc1", "sea"),
    "BR": ("br1", "americas"),
    "LAN": ("la1", "americas"),
    "LAS": ("la2", "americas"),
    "TR": ("tr1", "europe"),
    "PH": ("ph2", "sea"),
    "SG": ("sg2", "sea"),
    "TH": ("th2", "sea"),
    "TW": ("tw2", "sea"),
    "VN": ("vn2", "sea"),
}

# ---------------------------------------------------------------------------
# Harvester tunables
# ---------------------------------------------------------------------------
HARVESTER_TOP_CHALLENGERS: int = 3
HARVESTER_TOP_GRANDMASTERS: int = 3
HARVESTER_MATCH_COUNT: int = 2

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 15

# Local web application.
WEB_STATIC_PATH = Path(__file__).resolve().parent / "web" / "static"
WEB_HOST = os.environ.get("TFT_HOST", "127.0.0.1")
WEB_PORT = int(os.environ.get("TFT_PORT", "8000"))

# Analytics defaults (historical match-data heuristics).
# Historical Riot rarity fallback; current champion costs come from CDragon.
RARITY_TO_COST: dict[int, int] = {0: 1, 1: 2, 2: 3, 4: 4, 6: 5, 7: 6, 9: 11}

# Star level → pool copies consumed.
STAR_TO_COPIES: dict[int, int] = {1: 1, 2: 3, 3: 9}

# CDragon roles split by archetype.
DAMAGE_ROLES: frozenset[str] = frozenset(
    {
        "ADCarry",
        "ADCaster",
        "ADCasterFormSwapper",
        "ADFighter",
        "ADReaper",
        "ADSpecialist",
        "APCarry",
        "APCaster",
        "APFighter",
        "APReaper",
        "APSpecialist",
        "HFighter",
    }
)
DEFENSIVE_ROLES: frozenset[str] = frozenset({"ADTank", "APTank"})

# Base components (excluded from "completed item" count).
ANALYSIS_COMPONENT_ITEMS: frozenset[str] = frozenset(
    {
        "TFT_Item_BFSword",
        "TFT_Item_ChainVest",
        "TFT_Item_GiantsBelt",
        "TFT_Item_NeedlesslyLargeRod",
        "TFT_Item_NegatronCloak",
        "TFT_Item_RecurveBow",
        "TFT_Item_SparringGloves",
        "TFT_Item_Spatula",
        "TFT_Item_TearOfTheGoddess",
        "TFT_Item_FryingPan",
    }
)

# Resistance-reduction (shred/sunder) item keywords (matched case-insensitive).
ANALYSIS_SHRED_KEYWORDS: frozenset[str] = frozenset(
    {
        "ionicspark",
        "statikkshiv",
        "spectralgauntlet",
        "lastwhisper",
    }
)

# Anti-heal (Grievous Wounds) item keywords.
ANALYSIS_ANTIHEAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "redbuff",
        "morellonomicon",
        "rapidfirecannon",
    }
)

# Summoned units — not real champions.
ANALYSIS_SUMMON_KEYWORDS: frozenset[str] = frozenset(
    {
        "Tibbers",
        "Voidling",
        "Soldier",
        "Prop",
        "Chest",
        "ArmoryKey",
        "FreljordProp",
    }
)

# Unique passives — not real team synergies.
ANALYSIS_UNIQUE_TRAIT_KEYWORDS: frozenset[str] = frozenset(
    {
        "Unique",
        "Teamup",
        "TheBoss",
        "DarkChild",
        "RuneMage",
        "Soulbound",
        "HexMech",
        "Caretaker",
        "Emperor",
    }
)

# Dynamic threshold bounds.
ANALYSIS_THRESHOLD_DIVISOR: int = 50
ANALYSIS_THRESHOLD_FLOOR: int = 10
ANALYSIS_THRESHOLD_CAP: int = 75

# Default report output path (relative to project root).
ANALYSIS_REPORT_PATH: Path = PROJECT_ROOT / "delta_report.md"

ANALYSIS_QUERY_PATH = Path(__file__).resolve().parent / "analysis" / "participants.sql"
ANALYSIS_LEGACY_QUERY_PATH = Path(__file__).resolve().parent / "analysis" / "legacy_participants.sql"
ANALYSIS_MIN_ITEMS = 2
ANALYSIS_STAR_WEIGHT = 10
ANALYSIS_TOP_COMPOSITIONS = 20
ANALYSIS_TIERS = ("CHALLENGER", "GRANDMASTER")

# Static catalog refresh. CDragon build versions differ from TFT patch numbers.
DEFAULT_SET_NUMBER = 18
SET_DISPLAY_NAMES: dict[int, str] = {18: "Enchanted Wilds"}
STATIC_SCHEMA_PATH = Path(__file__).resolve().parent / "db" / "schema.sql"
CDRAGON_METADATA_URL = "https://raw.communitydragon.org/latest/content-metadata.json"
SQLITE_BUSY_TIMEOUT_SECONDS = 30
# FNV-1a lowercase hash of the source tag "TFT_Support".
CDRAGON_SUPPORT_ITEM_TAG = "{27557a09}"

# Ranked harvest uses source set/queue fields; game_version may be unknown.
RIOT_API_URL_TEMPLATE = "https://{routing}.api.riotgames.com"
RIOT_RANKED_QUEUE_ID = 1100
RIOT_MATCH_COUNT_MAX = 100
RIOT_BACKOFF_BASE_SECONDS = 1.0
RIOT_BACKOFF_MAX_RETRIES = 5
MATCH_SCHEMA_PATH = Path(__file__).resolve().parent / "db" / "match_schema.sql"
MATCH_UPSERT_PATH = Path(__file__).resolve().parent / "db" / "match_upsert.sql"
COMPLETED_MATCHES_PATH = Path(__file__).resolve().parent / "db" / "completed_matches.sql"

# Match explorer. Limits bound request size; placements follow the ranked lobby.
EXPLORER_MAX_FILTERS = 24
EXPLORER_MAX_ALTERNATIVES = 8
EXPLORER_MAX_UNIT_ITEMS = 3
EXPLORER_MAX_QUERY_CHARS = 8000
EXPLORER_MAX_STAR = 3
EXPLORER_MAX_LEVEL = 10
EXPLORER_MAX_TRAIT_TIER = 10
EXPLORER_MAX_ITEM_COPIES = 10
EXPLORER_LOBBY_SIZE = 8
EXPLORER_TOP_PLACEMENT = 4
EXPLORER_UNTRACKED_RANK = "UNTRACKED"
