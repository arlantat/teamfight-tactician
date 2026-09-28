-- Official Riot TFT news cache. Additive: catalog refreshes must not drop it.
CREATE TABLE IF NOT EXISTS news_articles (
    content_id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    published_at TEXT NOT NULL,
    revision TEXT NOT NULL,
    listing_revision TEXT NOT NULL,
    kind TEXT NOT NULL,
    image_url TEXT,
    headings TEXT NOT NULL,            -- JSON array of {level, text}
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    listing_fetched_at TEXT NOT NULL,
    source_url TEXT NOT NULL
);
