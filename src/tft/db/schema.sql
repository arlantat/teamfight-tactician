-- Canonical static catalog DDL. Apply inside the refresh transaction.
-- Match-history tables deliberately survive a static catalog refresh.
DROP TABLE IF EXISTS champions;
DROP TABLE IF EXISTS traits;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS augments;
DROP TABLE IF EXISTS metadata;

CREATE TABLE champions (
    api_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cost INTEGER NOT NULL CHECK (cost > 0),
    role TEXT,
    traits TEXT NOT NULL,              -- JSON array of trait names
    icon_url TEXT,
    square_icon_url TEXT,
    ability_name TEXT NOT NULL,
    ability_description TEXT NOT NULL,
    ability_icon_url TEXT,
    ability_variables TEXT NOT NULL,   -- JSON array of named star-level values
    stats TEXT NOT NULL,               -- JSON object of combat stats
    ability_detail TEXT NOT NULL DEFAULT '{}' -- JSON supplemental forms and provenance
);

CREATE TABLE traits (
    api_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    effects TEXT NOT NULL,             -- JSON array of breakpoint objects
    icon_url TEXT,
    description TEXT NOT NULL
);

CREATE TABLE items (
    api_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    icon_url TEXT,
    composition TEXT NOT NULL,         -- JSON array of component api_names
    effects TEXT NOT NULL,             -- JSON object of effect values
    category TEXT NOT NULL
);

CREATE TABLE augments (
    api_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    icon_url TEXT,
    effects TEXT NOT NULL,             -- JSON object of effect values
    tier TEXT NOT NULL
);

CREATE TABLE metadata (
    set_number INTEGER PRIMARY KEY,
    set_name TEXT NOT NULL,
    patch TEXT,                        -- TFT patch supplied from a verified source
    source_url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    source_set_name TEXT NOT NULL,
    mutator TEXT NOT NULL,
    source_version TEXT                -- CDragon build version, not a TFT patch
);
