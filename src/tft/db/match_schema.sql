-- match_schema.sql
-- ================
-- DDL for match-harvesting tables.  Uses IF NOT EXISTS so re-runs are
-- purely additive — no data is dropped.

CREATE TABLE IF NOT EXISTS players (
    puuid         TEXT PRIMARY KEY,
    tier          TEXT NOT NULL          -- 'CHALLENGER' or 'GRANDMASTER'
);

CREATE TABLE IF NOT EXISTS matches (
    match_id      TEXT PRIMARY KEY,
    game_version  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS match_participants (
    match_id        TEXT NOT NULL,
    puuid           TEXT NOT NULL,
    placement       INTEGER NOT NULL,
    level           INTEGER NOT NULL,
    gold_left       INTEGER NOT NULL,
    time_eliminated REAL NOT NULL,
    traits_json     TEXT NOT NULL,       -- JSON array of trait objects
    units_json      TEXT NOT NULL,       -- JSON array of unit objects
    augments_json   TEXT NOT NULL,       -- JSON array of augment strings
    PRIMARY KEY (match_id, puuid),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (puuid) REFERENCES players(puuid)
);
