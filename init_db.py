import sqlite3
import os

UNITS = []
TRAITS = []

def init_db():
    con = sqlite3.connect("raw_matches.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE matches(match_id TEXT PRIMARY KEY)")
    cur.execute("""
        CREATE TABLE player_states (
            puuid TEXT,
            match_id TEXT,
            augment1 TEXT,
            augment2 TEXT,
            augment3 TEXT,
            placement INTEGER,
            PRIMARY KEY (puuid, match_id)
        )
    """)
    # per set
    cur.execute("""
        CREATE TABLE units (
            character_id TEXT PRIMARY KEY,
            rarity INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE unit_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT,
            puuid TEXT,
            match_id TEXT,
            tier INTEGER,
            item1 TEXT,
            item2 TEXT,
            item3 TEXT
        )
    """)
    # per set
    cur.execute("""
        CREATE TABLE traits (
            name TEXT PRIMARY KEY,
            tier_total INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE trait_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            puuid TEXT,
            match_id TEXT,
            tier_current INTEGER
        )
    """)
    con.close()

def reset_db():
    db_file_path = "raw_matches.db"
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    init_db()

def init_per_set():
    con = sqlite3.connect("raw_matches.db")
    cur = con.cursor()
    ...
    # cur.execute("""
    #     INSERT INTO trait_states (name, puuid, match_id, tier_current)
    #     VALUES (?, ?, ?, ?)
    # """, (trait['name'], participant['puuid'], match_id, trait['tier_current']))
    con.close()

# reset_db()
# init_per_set()
