-- schema.sql
-- ==========
-- Canonical DDL for tft_data.db.  All schema changes go through this file.
-- Executed via ``tft.db.connection.run_schema()``.

DROP TABLE IF EXISTS champions;
DROP TABLE IF EXISTS traits;
DROP TABLE IF EXISTS items;

CREATE TABLE champions (
    api_name   TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    cost       INTEGER NOT NULL,
    role       TEXT,                 -- CDragon role tag  e.g. 'APCaster', 'ADTank'
    traits     TEXT NOT NULL,        -- JSON array of trait names  e.g. '["Slayer","Noxus"]'
    icon_url   TEXT
);

CREATE TABLE traits (
    api_name   TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    effects    TEXT NOT NULL,        -- JSON array of breakpoint objects
    icon_url   TEXT
);

CREATE TABLE items (
    api_name    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    icon_url    TEXT
);
