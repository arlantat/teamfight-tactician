-- Additive match storage; historical records remain intact during migration.
CREATE TABLE IF NOT EXISTS players (
    puuid         TEXT PRIMARY KEY,
    tier          TEXT NOT NULL          -- Observed league tier or 'UNKNOWN'
);

CREATE TABLE IF NOT EXISTS matches (
    match_id          TEXT PRIMARY KEY,
    game_version      TEXT NOT NULL,     -- Original source string, possibly unknown
    set_number        INTEGER,           -- NULL for unverified historical rows
    game_datetime     INTEGER,           -- Source Unix timestamp in milliseconds
    queue_id          INTEGER,
    participant_count INTEGER            -- Verified complete source roster size
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
    augments_json   TEXT NOT NULL,       -- JSON array; [] when source omits field
    PRIMARY KEY (match_id, puuid),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (puuid) REFERENCES players(puuid)
);
