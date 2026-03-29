# Teamfight Tactician — Agent Instructions

This document defines **all** rules that AI agents must follow when contributing
to this codebase. The owner reviews every change — readability, organisation,
and consistency are non-negotiable.

---

## 1. MANDATORY: Fetch Latest Game Data on Every New Conversation

At the **start of every new conversation**, you **MUST** use the **fetch MCP
tool** (`mcp_fetch_fetch`) to retrieve the latest TFT game data from
CommunityDragon and the Riot API documentation. **Do this before writing any
code or answering game-data-related questions.** The game updates frequently
with new patches, sets, champions, items, traits, and augments — stale
training data is unreliable.

### Step 1: Fetch CommunityDragon (CDragon) TFT Data

CDragon is the primary source for current set data (champions, traits, items,
augments). Fetch the **English US** locale JSON:

```
URL: https://raw.communitydragon.org/latest/cdragon/tft/en_us.json
```

This JSON contains the complete, structured data for the **current live set**:

- **Champions** — names, cost, stats, abilities, traits
- **Traits** — names, descriptions, breakpoints, effects
- **Items** — names, descriptions, component recipes, stats
- **Augments** — names, tiers, descriptions, effects

> **Note:** The `/latest/` path always points to the most recent patch deployed
> to live servers.

#### Additional Locales (fetch only if needed)

| Locale               | URL                                                               |
| -------------------- | ----------------------------------------------------------------- |
| Vietnamese           | `https://raw.communitydragon.org/latest/cdragon/tft/vi_vn.json`  |
| Korean               | `https://raw.communitydragon.org/latest/cdragon/tft/ko_kr.json`  |
| Japanese             | `https://raw.communitydragon.org/latest/cdragon/tft/ja_jp.json`  |
| Chinese (Simplified) | `https://raw.communitydragon.org/latest/cdragon/tft/zh_cn.json`  |
| Chinese (Traditional)| `https://raw.communitydragon.org/latest/cdragon/tft/zh_tw.json`  |
| Other                | See `https://raw.communitydragon.org/latest/cdragon/tft/`        |

#### Asset URL Mapping

Many fields in the JSON contain asset paths (icons, splash art). The project
has a helper `icon_url()` in `src/tft/etl/icons.py` that resolves them:

- Input: `ASSETS/Characters/Ahri/HUD/Icons2D/Ahri_Square.tex`
- Output: `https://raw.communitydragon.org/latest/game/assets/characters/ahri/hud/icons2d/ahri_square.png`
- Rule: lowercase the path, replace `.tex`/`.dds` → `.png`, prepend the CDN base.

### Step 2: Fetch Riot Developer API Documentation

The Riot API is the source for **live player data** (ranked stats, match
history, leaderboards). Fetch the API reference:

```
URL: https://developer.riotgames.com/apis
```

Key TFT API endpoints:

| API                | Endpoint Pattern                                               | Purpose                  |
| ------------------ | -------------------------------------------------------------- | ------------------------ |
| **ACCOUNT-V1**     | `/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}`    | Resolve Riot ID → PUUID  |
| **TFT-SUMMONER-V1**| `/tft/summoner/v1/summoners/by-puuid/{puuid}`                  | Get summoner info        |
| **TFT-MATCH-V1**   | `/tft/match/v1/matches/by-puuid/{puuid}/ids`                   | Get match ID list        |
| **TFT-MATCH-V1**   | `/tft/match/v1/matches/{matchId}`                              | Get match details        |
| **TFT-LEAGUE-V1**  | `/tft/league/v1/challenger`                                    | Challenger leaderboard   |
| **TFT-LEAGUE-V1**  | `/tft/league/v1/grandmaster`                                   | Grandmaster leaderboard  |
| **TFT-LEAGUE-V1**  | `/tft/league/v1/master`                                        | Master leaderboard       |
| **TFT-LEAGUE-V1**  | `/tft/league/v1/entries/{tier}/{division}`                      | Ranked entries by tier   |
| **TFT-LEAGUE-V1**  | `/tft/league/v1/entries/by-summoner/{summonerId}`               | Ranked entries by player |

> **Important:** Riot uses **PUUIDs** as the primary player identifier. Always
> resolve Riot IDs to PUUIDs via ACCOUNT-V1 first. Match endpoints use
> **regional routing** (`americas`, `europe`, `asia`, `sea`) rather than
> platform IDs.

### Step 3: Confirm Data Freshness

After fetching, briefly note:

1. The **current set name and number** (from the CDragon data)
2. The **current patch version** (visible in the CDragon response or URL)
3. Confirm that the data was fetched successfully

### Step 4: Verify Live API Response Shapes

> **⚠ Critical:** The Riot API evolves frequently — fields are added, renamed,
> and removed without deprecation notices.  **Never assume** endpoint response
> shapes based on training data or documentation alone.

Before writing or modifying any code that consumes a Riot API endpoint, **make
a live test call** and inspect the actual JSON keys:

```python
# Example: inspect a single entry from the challenger league endpoint
resp = requests.get(
    f"{PLATFORM_BASE}/tft/league/v1/challenger",
    headers={"X-Riot-Token": API_KEY},
)
entry = resp.json()["entries"][0]
print(entry.keys())  # Verify which fields actually exist
```

**Known breaking changes** (as of March 2026):
- League entries (`/tft/league/v1/{tier}`) now return `puuid` directly —
  the old `summonerId` and `summonerName` fields have been **removed**.
- The `TFT-SUMMONER-V1` lookup to convert summonerId → puuid is therefore
  **no longer needed** for the league → match-history pipeline.

---

## 2. General Project Context

**Teamfight Tactician** is a TFT (Teamfight Tactics) companion app/tool. This
project is **exclusively about TFT** — it has nothing to do with League of
Legends (the MOBA). Do not reference, fetch, or incorporate any League of
Legends-specific data (champions, items, runes, etc.). Only TFT game data is
relevant.

---

## 3. Project Structure

The project follows a **src-layout** Python package. All application code lives
under `src/tft/`. Scripts, tests, and config live at the project root.

```
teamfight-tactician/
│
├── src/
│   └── tft/                        # Main application package
│       ├── __init__.py
│       ├── config.py               # Settings, constants, env vars
│       │
│       ├── db/                     # Database access layer
│       │   ├── __init__.py
│       │   ├── connection.py       # SQLite connection helpers
│       │   ├── models.py           # Dataclasses for DB rows
│       │   └── schema.sql          # DDL — single source of truth for tables
│       │
│       ├── etl/                    # Data pipelines (extract-transform-load)
│       │   ├── __init__.py
│       │   ├── cdragon.py          # CDragon fetch + parse logic
│       │   └── icons.py            # Icon URL resolution helper
│       │
│       ├── riot/                   # Riot API client (future)
│       │   ├── __init__.py
│       │   └── client.py
│       │
│       └── utils/                  # Shared utilities
│           ├── __init__.py
│           └── logging.py          # Logging configuration
│
├── scripts/                        # CLI entry points
│   └── update_static_data.py       # Fetch & populate tft_data.db
│
├── tests/                          # pytest test suite
│   ├── conftest.py                 # Shared fixtures
│   └── test_*.py
│
├── .venv/                          # Virtual environment (git-ignored)
├── .gitignore
├── AGENTS.md                       # ← You are here
├── README.md
├── pyproject.toml                  # Project metadata + tool config
└── requirements.txt                # Pinned dependencies
```

### Rules for File Organisation

1. **One responsibility per file.** If a module grows beyond ~300 lines of
   logic, split it. Prefer many small, focused modules over monolithic ones.
2. **New features get their own sub-package.** If a feature spans multiple
   files (e.g. a new analytics engine), create a new directory under `src/tft/`.
3. **Scripts are thin wrappers.** Files in `scripts/` should only parse CLI
   args and call functions from `src/tft/`. No business logic in scripts.
4. **Scripts must bootstrap `sys.path`.** Every script **must** include the
   following preamble before any `tft.*` imports to work reliably with the
   src-layout (Python 3.14 `.pth` processing is unreliable):

   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
   ```

5. **SQL lives in `.sql` files.** DDL and complex queries go in dedicated SQL
   files, not embedded in Python strings (simple one-liner queries are okay
   inline).
6. **Never put application code in the project root.** Only config files,
   README, and standard project metadata belong at the top level.
7. **Tests mirror `src/` structure.** `src/tft/etl/cdragon.py` →
   `tests/test_etl_cdragon.py` (flat) or `tests/etl/test_cdragon.py` (nested).

---

## 4. Python Coding Standards

### 4.1 Language & Version

- Target **Python 3.14+**.
- Use the `.venv` virtual environment for all execution:
  `.venv/bin/python`, `.venv/bin/pip`.

### 4.2 Type Hints

- **Every** function signature must have full type annotations (params + return).
- Use modern syntax: `list[str]`, `dict[str, Any]`, `str | None` — not
  `List`, `Dict`, `Optional`.
- For complex types, define a `TypeAlias` or `TypedDict` at the top of the
  module.

```python
# ✅ Good
def fetch_champions(url: str, timeout: int = 30) -> list[dict[str, Any]]:
    ...

# ❌ Bad — no types
def fetch_champions(url, timeout=30):
    ...
```

### 4.3 Docstrings

- Use **Google-style** docstrings.
- Every public function, class, and module must have a docstring.
- Private helpers (`_prefixed`) should have at least a one-liner.

```python
def icon_url(tex_path: str | None) -> str | None:
    """Translate a CDragon .tex asset path to a raw PNG URL.

    Args:
        tex_path: Internal CDragon asset path (e.g. "ASSETS/Characters/...tex").

    Returns:
        Full HTTPS URL to the PNG, or None if tex_path is falsy.
    """
```

### 4.4 Naming Conventions

| Thing              | Convention        | Example                         |
| ------------------ | ----------------- | ------------------------------- |
| Modules / files    | `snake_case`      | `cdragon.py`, `icon_urls.py`    |
| Functions          | `snake_case`      | `parse_champions()`             |
| Classes            | `PascalCase`      | `CdragonClient`                 |
| Constants          | `UPPER_SNAKE`     | `CDRAGON_BASE_URL`              |
| Private members    | `_leading_under`  | `_parse_set_data()`             |
| Type aliases       | `PascalCase`      | `ChampionRow = TypedDict(...)` |
| Database tables    | `snake_case`      | `champions`, `match_history`    |
| Database columns   | `snake_case`      | `api_name`, `icon_url`          |

### 4.5 Imports

- Group imports in this order, separated by a blank line:
  1. Standard library
  2. Third-party packages
  3. Local (`from tft. ...`)
- Use absolute imports (`from tft.etl.icons import icon_url`), never relative.
- Never use wildcard imports (`from x import *`).

### 4.6 Error Handling

- Raise **specific** exceptions — never bare `raise Exception(...)`.
- Define project-level exceptions in `src/tft/exceptions.py` when needed.
- Use `requests.Response.raise_for_status()` after every HTTP call.
- Database operations must be wrapped in try/finally to guarantee
  `conn.close()`.

### 4.7 Logging

- Use the `logging` stdlib module — never `print()` for operational output.
- One logger per module: `log = logging.getLogger(__name__)`.
- Log at appropriate levels:
  - `INFO` — high-level progress (started, completed, counts)
  - `WARNING` — recoverable issues (missing optional field, retry)
  - `ERROR` — failures that stop a pipeline
  - `DEBUG` — detailed data for troubleshooting

### 4.8 Data Modelling

- Use **`dataclasses`** or **`TypedDict`** for structured data passed between
  layers. Avoid passing raw `dict` objects across module boundaries.
- Keep models in `src/tft/db/models.py` for DB-bound types.

### 4.9 Constants & Configuration

- All URLs, paths, magic numbers, and tuneable values go in `src/tft/config.py`.
- Secrets and environment-specific values (API keys, DB paths) use environment
  variables with sensible defaults.
- Never hardcode API keys, secrets, or user-specific paths.

---

## 5. Database Conventions

- **SQLite** is the default storage engine (local-first, zero-config).
- **Schema-as-code**: The canonical DDL lives in `src/tft/db/schema.sql`.
  Any schema change must update that file.
- **Column naming**: `snake_case`. Use `api_name` not `apiName` in the DB
  (Python-native style) even if the source JSON uses camelCase.
- **JSON columns**: Store complex nested data (traits list, effect breakpoints)
  as JSON TEXT columns. Document the expected shape in a comment.
- **Idempotent updates**: `DROP TABLE IF EXISTS` + `CREATE TABLE` for full
  refreshes. Use `INSERT OR REPLACE` for upserts.

---

## 6. Git & Commit Hygiene

- **Atomic commits**: One logical change per commit.
- **Conventional commit messages**: `feat:`, `fix:`, `refactor:`, `docs:`,
  `chore:`, `test:`.
- **Never commit**: `.venv/`, `__pycache__/`, `*.db`, `.env`, IDE config.
  These are already in `.gitignore`.

---

## 7. Testing

- Use **pytest** as the test runner.
- Minimum expectations:
  - All ETL parsing functions have unit tests with sample data.
  - Icon URL resolution is tested against known CDragon paths.
  - DB schema creation is tested (create tables, insert, query).
- Test files live in `tests/` and are prefixed with `test_`.
- Use fixtures in `conftest.py` for shared setup (DB connections, sample JSON).

---

## 8. Code Review Checklist (for the agent)

Before presenting code for review, verify:

- [ ] All functions have type annotations and docstrings
- [ ] No business logic in script entry points
- [ ] Constants extracted — no magic strings or numbers
- [ ] Logging instead of print statements
- [ ] Error handling with specific exceptions
- [ ] New files placed in the correct package
- [ ] Module stays under ~300 lines of logic
- [ ] Tests added or updated for new/changed logic
- [ ] Imports sorted: stdlib → third-party → local
- [ ] No hardcoded secrets or user-specific paths
