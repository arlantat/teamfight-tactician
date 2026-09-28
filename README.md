# Teamfight Tactician

A local TFT companion for **Set 18 — Enchanted Wilds**. Explore champions,
traits, equipment, and augments with Riot artwork, then plan a board with live
trait counts. Inspect locally harvested ranked matches in Insights or generate
an analysis report with the Python CLI.

## Run locally

Requires **Python 3.14+**. No Node.js or frontend build is required.

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/update_static_data.py --set 18 --patch 18.2 --with-abilities
.venv/bin/python scripts/serve.py
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)**. The catalog and team builder do not require a
Riot API key. Downloaded data is stored in a local, git-ignored SQLite database;
team plans are saved in your browser on the same origin.

## Explore and plan

- **Overview:** an illustrated set landing page, the latest official patch notes,
  and quick access to the catalog.
- **Patch notes:** Riot's public titles, teasers, and section outlines, including
  mid-patch updates. Full notes stay on [Riot's site](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/).
- **Champions:** searchable roster, cost and trait filters, artwork, abilities,
  star-level values, alternate forms, and base stats. The roster includes
  playable Riftbeasts and Lux forms.
- **Traits:** descriptions, breakpoints, and matching champions.
- **Items:** equipment categories, stats, recipes, and component artwork.
- **Augments:** searchable active-set entries with icons and tier filters.
- **Team builder:** place and move units on a four-row hex board, inspect trait
  progress, and save or restore a team locally.
- **Insights:** view composition popularity, outcome comparisons, and
  three-star four- and five-cost boards from locally harvested ranked data.

The app presents source data, a planning board, and observed match statistics.
It does not simulate combat or infer optimal compositions from sparse samples.

## Refresh game data

```sh
# Refresh Set 18 with the reviewed ability reference and Riot 18.2 corrections.
.venv/bin/python scripts/update_static_data.py --set 18 --patch 18.2 --with-abilities

# CommunityDragon-only catalog; omits supplemental numeric ability values.
.venv/bin/python scripts/update_static_data.py --set 18

# Import an already downloaded CommunityDragon JSON file.
.venv/bin/python scripts/update_static_data.py --source /path/to/en_us.json --set 18

# Reproduce a reviewed import from saved source files.
.venv/bin/python scripts/update_static_data.py --source /path/to/en_us.json --set 18 --patch 18.2 --abilities-source /path/to/TFTSet18_latest_en_us.json

# Use another database or port.
.venv/bin/python scripts/serve.py --db /path/to/tft.db --port 8001
```

Set 18 and TFT patch **18.2** were verified on **September 14, 2026** against
[Riot's patch notes](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-18-2/)
and [CommunityDragon's live TFT JSON](https://raw.communitydragon.org/latest/cdragon/tft/en_us.json).
That source identifies the canonical roster as `TFTSet18`, but incorrectly
labels its name `Set10`. The app uses the verified display name and retains
the original name in metadata. CDragon's client build (`16.18…` at verification)
is recorded separately from the TFT patch; an unspecified patch stays unknown.

Refreshes use the selected set's item and augment membership lists instead of
assuming a prefix: Set 18 includes `DA_…` identifiers and reused content.
Neutral encounters and props are excluded from the playable roster. Internal
item rewards remain available in the Special category. Missing source values
are not invented; some ability calculations are only available as symbolic
expressions. Source-provided augment entries do not guarantee an augment can
be offered in every mode or situation.

### Numeric champion abilities

CommunityDragon currently omits numeric variables for most Set 18 abilities.
The optional supplement uses [MetaTFT's Set 18 export](https://data.metatft.com/lookups/TFTSet18_latest_en_us.json)
to cover all **74 roster entries and 79 ability forms**, including the five
AD/AP alternatives. The reviewed export was generated September 11, 2026 and
is explicitly marked **PBE**. Its source label, generation time, and
verification limits are shown in each champion's ability panel.

The main 18.2 numerical ability changes were cross-checked against Riot's notes.
The supplement applies the September 14 corrections for Camille, LeBlanc,
Teemo, Brambleback, and Ashe, plus Maokai's mana change. Brambleback's flat
armor-ignore change is applied as a constant across stars; that interpretation
and Ashe's ambiguous falloff wording are called out in the affected panels.
Other live-client values have not been independently verified.

Star selectors use the source's step curves. Health-dependent abilities retain
their formulas, AP/AD scaling is explicit, and unresolved combat-dependent
values remain labeled as variable. These are tooltip coefficients, not a combat
damage simulator. Lux origins are joined by exact trait sets instead of names.

The importer accepts only the reviewed source fingerprint and target patch.
If MetaTFT changes its export, enrichment fails before writing the database;
review the new source and patch corrections before updating the allowlist.
Refreshing without `--with-abilities` or `--abilities-source` replaces the
supplement with the CommunityDragon-only catalog. Ability numbers are **not**
updated automatically when Riot publishes a patch or mid-patch note.

All static tables and metadata refresh in one transaction. A failed refresh
leaves the previous catalog intact and never replaces match tables. Reload
the browser after refreshing. The UI gives setup instructions for missing or
older databases. Champion and icon images load from CommunityDragon and need
network access; the set artwork is bundled locally.

## Ranked data and analytics

Use a development key from the [Riot Developer Portal](https://developer.riotgames.com/)
to collect a bounded sample. Add `RIOT_API_KEY` to your private `.env` file or
export it in your shell; `.env.example` contains no credentials.

```sh
# For initial setup only, if .env does not already exist:
cp -n .env.example .env
# Add RIOT_API_KEY to .env using your editor, then run:
.venv/bin/python scripts/match_harvester.py --servers NA --challengers 3 --grandmasters 3 --matches 2 --set 18
.venv/bin/python scripts/delta_engine.py --db tft_data.db --output artifacts/delta_report.md
```

Live league, match-history, and match-detail response shapes were verified with
a private development key. The verification harvest stored **11 Set 18 ranked
matches and 88 participant boards**. League entries provide PUUIDs directly;
match details reported `TFT Unreal Version ?.?.?.?` as their game version and
omitted augments. The parser retains that unknown version and stores an empty
augment array instead of inventing source values.

The typed harvester validates set, ranked queue, and complete participant
rosters before saving each match atomically. Repeated runs skip complete
matches and retry incomplete ones. Additive migrations preserve stored history.

Insights and the report CLI share the same analysis service. With catalog
metadata present, analysis includes only verified ranked matches from that
catalog's set; old or unverified rows cannot enter the current sample.
Databases without catalog set metadata retain historical analysis behavior.
Use `--game-version` to restrict the report to one exact source version when
available. An unknown version cannot establish patch compatibility.

Reports describe observed associations, distinguish top-four rate from wins,
and handle empty datasets. Composition comparisons require sufficient samples
in both tracked tiers. Legacy rarity fallbacks are historical heuristics;
source champion costs take precedence.

## Configuration

Environment variables are loaded from `.env` without overriding exported values.

| Variable | Default | Purpose |
| --- | --- | --- |
| `TFT_DB_PATH` | `tft_data.db` in the project | SQLite catalog and match data |
| `TFT_HOST` | `127.0.0.1` | Local web server interface |
| `TFT_PORT` | `8000` | Web server port |
| `RIOT_API_KEY` | empty | Required only for match harvesting |
| `RIOT_PLATFORM` | `na1` | Riot platform routing |
| `RIOT_REGION` | `americas` | Riot regional routing |

## Development

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts

# Optional JavaScript regression tests; requires Node.js.
node --test tests/frontend/*.mjs
```

```text
src/tft/
  config.py        Environment configuration and shared constants
  db/              Typed rows, SQLite helpers, canonical SQL schemas
  etl/             Set selection, parsing, asset resolution, atomic refresh
  abilities/       Reviewed numeric reference, exact form joins, patch corrections
  riot/            Typed Riot client, rate limiting, bounded harvest, atomic storage
  analysis/        Focused analytics modules and SQL
  web/             Read-only catalog/analysis API and modular browser interface
scripts/           CLI entry points
tests/             Parsing, persistence, API, analytics, and frontend regression tests
```

The web API exposes `GET /api/health`, `GET /api/catalog`, `GET /api/analysis`
with an optional `game_version` query parameter, and `GET /api/news`. Analysis
reads local match data without contacting Riot. News reads Riot's public TFT
site (no API key), caches titles and heading outlines locally, and does not
store article bodies. Static catalog reads use a
single read-only transaction. UI source is served from
`src/tft/web/static`; no generated JavaScript bundle is necessary.

## Attribution

TFT artwork, champions, icons, and other game assets belong to Riot Games.
Static data and game icons are provided by
[CommunityDragon](https://www.communitydragon.org/); set artwork comes from
[Riot's Enchanted Wilds overview](https://teamfighttactics.leagueoflegends.com/en-us/set-overview/tft-set-18-enchanted-wilds/).
Supplemental ability curves and calculations come from
[MetaTFT](https://www.metatft.com/), with corrections from Riot's patch notes.
Teamfight Tactician is an independent fan project and is not endorsed by Riot Games.
