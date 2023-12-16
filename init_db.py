import sqlite3
import os
import requests
import time
from tft import server_to_region
from dotenv import load_dotenv
import re
from tft import summoner_to_matches, insert_match, CRAFTABLES, RADIANTS, SUPPORTS, EMBLEMS, ARTIFACTS, IGNOREDITEMS
load_dotenv()

RIOT_API = os.environ.get('RIOT_API')

def init_db():
    con = sqlite3.connect("raw_matches.db")
    con.isolation_level = None
    cur = con.cursor()
    cur.execute("CREATE TABLE matches(match_id TEXT PRIMARY KEY)")
    cur.execute("""
        CREATE TABLE player_states (
            puuid TEXT,
            match_id TEXT,
            augment1 TEXT,
            augment2 TEXT,
            augment3 TEXT,
            comp_encoded TEXT,
            placement INTEGER,
            PRIMARY KEY (puuid, match_id)
        )
    """)
    # per set
    cur.execute("""
        CREATE TABLE units (
            character_id TEXT PRIMARY KEY,
            rarity INTEGER,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE units_3 (
            character_id TEXT PRIMARY KEY,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
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
            name TEXT,
            tier_current INTEGER,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER,
            PRIMARY KEY (name, tier_current)
        )
    """)
    cur.execute("""
        CREATE TABLE trait_states (
            name TEXT,
            puuid TEXT,
            match_id TEXT,
            tier_current INTEGER,
            PRIMARY KEY (name, puuid, match_id)
        )
    """)
    cur.execute("""
        CREATE TABLE items (
            name TEXT PRIMARY KEY,
            class TEXT,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE augments (
            name TEXT,
            stage INTEGER,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER,
            PRIMARY KEY (name, stage)
        )
    """)
    cur.execute("""
        CREATE TABLE comps (
            encoded TEXT PRIMARY KEY,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    con.close()

def reset_db(per_set=False):
    '''if per_set is set to True, wipes the entire db'''
    if per_set:
        db_file_path = "raw_matches.db"
        if os.path.exists(db_file_path):
            os.remove(db_file_path)
        init_db()
        init_per_set()
        return
    con = sqlite3.connect("raw_matches.db")
    con.isolation_level = None
    cur = con.cursor()
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM player_states")
    cur.execute("DELETE FROM unit_states")
    cur.execute("DELETE FROM trait_states")
    cur.execute("DELETE FROM augments")
    cur.execute("DELETE FROM comps")
    cur.execute("UPDATE units SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    cur.execute("UPDATE units_3 SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    cur.execute("UPDATE traits SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    cur.execute("UPDATE items SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    con.close()

def init_per_set():
    con = sqlite3.connect("raw_matches.db")
    con.isolation_level = None
    cur = con.cursor()
    cnt = 1
    server = 'vn2'
    region = server_to_region(server) 
    players = ['KhanhTri1810','adversary','St3Mura','Noob Guy','HNZ MIDFEEDD','xayah nilah','KND Finn','H E N I S S','RoT T2','PRX f0rs4keN','TVQ 1','PRX someth1ng','KND iCynS','GGx Lemonss','temppploutmmlggs','DB HighRoll','LLAETUM','paranoise','JayDee 333','KND k1an', 'Đình Tuấn1', 'M1nhbeso', 'Nâng cúp 4 lần', 'Just Dante', 'Dòng Máu Họ Đỗ', 'Marry Shaco', 'GD Shaw1', 'Dizzyland', 'Yasuo Không Q', 'CFNP Mèo Hor1', 'Onlive TrungVla', 'y Tiger1','Cloudyyyyyyyy','INF Kiss Kiss', 'Setsuko','1atsA','Twinkling Whales','TSK Milfhunter','me from nowhere','severthaidinh','Won Joon Soo']
    for player in players:
        list_of_matches = summoner_to_matches(cur, server, region, player, count=30)
        if not list_of_matches:
            continue
        for match in list_of_matches:
            # insert_match(cur, server, region, match)
            print(f"match number {cnt}, currently {match}")
            cnt += 1
            url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match}"
            headers = {'X-Riot-Token': RIOT_API}
            res = requests.get(url, headers=headers)
            if res.status_code != 200:
                print(res.status_code)
                time.sleep(25)
                continue
            json = res.json()
            if not json['info']['game_version'].startswith('Version 13.23'):
                continue
            for participant in json['info']['participants']:
                # init traits
                for trait in participant['traits']:
                    cur.execute("SELECT * FROM traits WHERE name = ?", (trait['name'],))
                    if cur.fetchone() is not None:  # skip stored traits
                        continue
                    for i in range(1, trait['tier_total']+1):
                        cur.execute("""
                            INSERT INTO traits (name, tier_current)
                            VALUES (?, ?)
                        """, (trait['name'], i))
                # init units
                for unit in participant['units']:
                    cur.execute("SELECT * FROM units WHERE character_id = ?", (unit['character_id'],))
                    if cur.fetchone() is not None:
                        continue
                    cur.execute("""
                        INSERT INTO units (character_id, rarity)
                        VALUES (?, ?)
                    """, (unit['character_id'], unit['rarity']))
                    if unit['rarity'] in [0, 1, 2]:
                        cur.execute("""
                            INSERT INTO units_3 (character_id)
                            VALUES (?)
                        """, (unit['character_id'],))
    itemss = [(CRAFTABLES, 'craftable'), (RADIANTS, 'radiant'), (SUPPORTS, 'support'), (EMBLEMS, 'emblem'), (ARTIFACTS,'artifact')]
    for items, c in itemss:
        for item in items:
            cur.execute("INSERT INTO items (name, class) VALUES (?, ?)", (item, c,))
    cur.execute("SELECT name, class from items")
    con.close()


# try first to be sure then commit
def manual_per_set():
    con = sqlite3.connect("raw_matches.db")
    # con.isolation_level = None
    cur = con.cursor()

    # manual units
    # character_ids = ['TFT9_RyzeNoxus','TFT9_RyzeShadowIsles','TFT9_RyzeZaun','TFT9_RyzeBilgewater','TFT9_RyzeIxtal']
    # for character_id in character_ids:
    #     cur.execute("SELECT * FROM units WHERE character_id = ?", (character_id,))
    #     if cur.fetchone() is not None:
    #         continue
    #     cur.execute("""
    #         INSERT INTO units (character_id, rarity)
    #         VALUES (?, ?)
    #     """, (character_id, 6))

    # manual items
    # cur.execute('SELECT item1, item2, item3 FROM unit_states')
    # items = set()
    # for row in cur.fetchall():
    #     for item in row:
    #         if item is not None:
    #             items.add(item)
    # li = list(items)
    print(type(CRAFTABLES))
    # craftable = [s for s in li if s in CRAFTABLES]
    # radiant = [s for s in li if s in RADIANTS]
    # emblem = [s for s in li if s in EMBLEMS]
    # support = [s for s in li if s in SUPPORTS]
    # artifact = [s for s in li if s in ARTIFACTS]
    # ignored = [s for s in li if s in IGNOREDITEMS]
    
    
    
    
    
    con.close()

reset_db()
# init_per_set()
# manual_per_set()
# print(len(UNITS1))
# print(len(UNITS2))
# print(len(UNITS3))
# print(len(UNITS4))
# print(len(UNITS5))
# print(len(TRAITS))

