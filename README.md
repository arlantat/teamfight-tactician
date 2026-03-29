# Teamfight Tactician

A TFT (Teamfight Tactics) analytics companion app. Static game data is sourced from [CommunityDragon](https://communitydragon.org/) and live match data from the [Riot Games API](https://developer.riotgames.com/).

## Quick Start

```bash
# 1. Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install the package (editable) + dev tools
pip install -e ".[dev]"

# 3. Fetch the latest set data
python scripts/update_static_data.py

# 4. Harvest ranked match data (requires Riot API key)
cp .env.example .env       # then add your RIOT_API_KEY
python scripts/match_harvester.py

# 5. Run tests
pytest
```

This creates a local `tft_data.db` SQLite database with six tables — **champions**, **traits**, and **items** for static set data, plus **players**, **matches**, and **match_participants** for ranked match data.

## 🔄 Updating Data for a New Set

> **Every time a new TFT set or mid-set update goes live, re-run the data script to refresh your local database.**

```bash
python scripts/update_static_data.py
```

The script automatically detects the latest set from CommunityDragon — no code changes needed. It will:

1. Fetch the full TFT JSON from CDragon (`/latest/` always points to the live patch)
2. Identify the active set by highest set number
3. Drop and recreate all tables with fresh data
4. Log how many champions, traits, and items were inserted

### When to re-run

| Event                                    | Action                                |
| ---------------------------------------- | ------------------------------------- |
| **New set launches** (e.g. Set 17)       | Run `python scripts/update_static_data.py` |
| **Mid-set update** (e.g. Set 16.5)       | Run `python scripts/update_static_data.py` |
| **B-patch with champion/item changes**   | Run `python scripts/update_static_data.py` |
| **Regular patch** (balance only)         | Optional — descriptions may change    |

## 🎮 Harvesting Ranked Match Data

The match harvester scrapes end-game data for top Challenger and Grandmaster players via the Riot Games API.

### Prerequisites

1. **Riot API key** — obtain from [developer.riotgames.com](https://developer.riotgames.com/)
2. **Environment file** — copy the template and add your key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
RIOT_PLATFORM=na1        # na1, euw1, kr, etc.
RIOT_REGION=americas     # americas, europe, asia, sea
```

### Running the harvester

```bash
python scripts/match_harvester.py
```

The script will:

1. Fetch the **Challenger** and **Grandmaster** leaderboards
2. Sort by LP and select the top 50 Challengers + top 200 Grandmasters
3. Resolve each player's summoner ID → PUUID
4. Fetch the last 15 match IDs per player
5. Download full match details, filtered to the **current game version** only
6. Upsert all data into `tft_data.db`

### Rate limiting

The harvester enforces Riot's development-key rate limits **strictly**:

| Window     | Limit              |
| ---------- | ------------------ |
| Short      | 20 requests / 1s   |
| Long       | 100 requests / 2m  |

A dual sliding-window rate limiter sleeps preemptively before every request. If a `429 Too Many Requests` response is somehow received, exponential backoff with `Retry-After` header support kicks in.

### Configurable tunables

These defaults are set in `src/tft/config.py` and can be adjusted:

| Constant                     | Default | Description                      |
| ---------------------------- | ------- | -------------------------------- |
| `HARVESTER_TOP_CHALLENGERS`  | 50      | Number of top Challengers        |
| `HARVESTER_TOP_GRANDMASTERS` | 200     | Number of top Grandmasters       |
| `HARVESTER_MATCH_COUNT`      | 15      | Recent matches to fetch per player |

## Database Schema

### `champions`

| Column     | Type        | Description                              |
| ---------- | ----------- | ---------------------------------------- |
| `api_name` | TEXT (PK)   | Internal identifier (e.g. `TFT16_Ahri`)  |
| `name`     | TEXT        | Display name                             |
| `cost`     | INTEGER     | Gold cost (1–5)                          |
| `traits`   | TEXT        | JSON array of trait names                |
| `icon_url` | TEXT        | CDragon CDN URL for the champion splash  |

### `traits`

| Column     | Type        | Description                                              |
| ---------- | ----------- | -------------------------------------------------------- |
| `api_name` | TEXT (PK)   | Internal identifier                                      |
| `name`     | TEXT        | Display name                                             |
| `effects`  | TEXT        | JSON array of breakpoint objects (`minUnits`, `variables`) |
| `icon_url` | TEXT        | CDragon CDN URL for the trait icon                       |

### `items`

| Column        | Type        | Description                              |
| ------------- | ----------- | ---------------------------------------- |
| `api_name`    | TEXT (PK)   | Internal identifier                      |
| `name`        | TEXT        | Display name                             |
| `description` | TEXT        | Item description with effect placeholders |
| `icon_url`    | TEXT        | CDragon CDN URL for the item icon        |

### `players`

| Column          | Type        | Description                                 |
| --------------- | ----------- | ------------------------------------------- |
| `puuid`         | TEXT (PK)   | Riot PUUID                                  |
| `summoner_name` | TEXT        | Display name at time of harvest             |
| `tier`          | TEXT        | `CHALLENGER` or `GRANDMASTER`               |

### `matches`

| Column         | Type        | Description                                  |
| -------------- | ----------- | -------------------------------------------- |
| `match_id`     | TEXT (PK)   | Riot match ID (e.g. `NA1_12345`)             |
| `game_version` | TEXT        | Patch version string                         |

### `match_participants`

| Column           | Type        | Description                                |
| ---------------- | ----------- | ------------------------------------------ |
| `match_id`       | TEXT (PK)   | FK → `matches.match_id`                    |
| `puuid`          | TEXT (PK)   | FK → `players.puuid`                       |
| `placement`      | INTEGER     | Final placement (1–8)                      |
| `level`          | INTEGER     | Player level at game end                   |
| `gold_left`      | INTEGER     | Gold remaining                             |
| `time_eliminated`| REAL        | Seconds survived                           |
| `traits_json`    | TEXT        | JSON array of active trait objects          |
| `units_json`     | TEXT        | JSON array of unit objects (items, tier…)   |
| `augments_json`  | TEXT        | JSON array of augment API names            |

## Project Structure

```text
teamfight-tactician/
├── src/
│   └── tft/                        # Main application package
│       ├── config.py               # Settings, constants, env vars
│       ├── db/                     # Database layer
│       │   ├── connection.py       # SQLite connection helpers
│       │   ├── models.py           # Dataclasses for DB rows
│       │   ├── schema.sql          # DDL for static data tables
│       │   └── match_schema.sql    # DDL for match harvester tables
│       ├── etl/                    # Data pipelines
│       │   ├── cdragon.py          # CDragon fetch + parse
│       │   ├── icons.py            # Icon URL resolution
│       │   └── match_parser.py     # Riot match JSON → DB rows
│       ├── riot/                   # Riot API client
│       │   ├── client.py           # Typed API wrapper
│       │   └── rate_limiter.py     # Dual-window rate limiter
│       └── utils/                  # Shared utilities
│           └── logging.py          # Logging configuration
├── scripts/
│   ├── update_static_data.py       # Fetch static set data
│   └── match_harvester.py          # Harvest ranked match data
├── tests/                          # pytest test suite
├── .env.example                    # Environment variable template
├── pyproject.toml                  # Packaging + tool config
├── requirements.txt                # Pinned dependencies
├── AGENTS.md                       # AI agent coding standards
└── README.md
```

## Data Sources

- **[CommunityDragon](https://raw.communitydragon.org/latest/cdragon/tft/en_us.json)** — Champions, traits, items, icons for the current set
- **[Riot Developer API](https://developer.riotgames.com/apis)** — Challenger/Grandmaster leaderboards, summoner data, match history
