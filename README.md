# Teamfight Tactician

A TFT (Teamfight Tactics) analytics companion app. Data is sourced directly from [CommunityDragon](https://communitydragon.org/) to stay current with every patch.

## Quick Start

```bash
# 1. Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install the package (editable) + dev tools
pip install -e ".[dev]"

# 3. Fetch the latest set data
python scripts/update_static_data.py

# 4. Run tests
pytest
```

This creates a local `tft_data.db` SQLite database with three tables: **champions**, **traits**, and **items** for the currently active TFT set.

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

## Project Structure

```
teamfight-tactician/
├── src/
│   └── tft/                        # Main application package
│       ├── config.py               # Settings, constants, env vars
│       ├── db/                     # Database layer
│       │   ├── connection.py       # SQLite connection helpers
│       │   ├── models.py           # Dataclasses for DB rows
│       │   └── schema.sql          # DDL — single source of truth
│       ├── etl/                    # Data pipelines
│       │   ├── cdragon.py          # CDragon fetch + parse
│       │   └── icons.py            # Icon URL resolution
│       ├── riot/                   # Riot API client (future)
│       └── utils/                  # Shared utilities
│           └── logging.py          # Logging configuration
├── scripts/
│   └── update_static_data.py       # CLI entry point
├── tests/                          # pytest test suite
├── pyproject.toml                  # Packaging + tool config
├── requirements.txt                # Pinned dependencies
├── AGENTS.md                       # AI agent coding standards
└── README.md
```

## Data Sources

- **[CommunityDragon](https://raw.communitydragon.org/latest/cdragon/tft/en_us.json)** — Champions, traits, items, icons for the current set
- **[Riot Developer API](https://developer.riotgames.com/apis)** — Live player data, match history, leaderboards (future integration)
