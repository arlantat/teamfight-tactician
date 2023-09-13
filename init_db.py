import sqlite3
import os
import requests
from tft import server_to_region
from dotenv import load_dotenv
load_dotenv()

UNITS1 = ['TFT9_Graves','TFT9_Orianna','TFT9_Illaoi','TFT9_Renekton','TFT9_Irelia','TFT9_Samira','TFT9_Milio','TFT9_Cassiopeia','TFT9_Poppy','TFT9_Kayle','TFT9_ChoGath','TFT9_Malzahar','TFT9_Jhin',]
UNITS2 = ['TFT9_Vi','TFT9_Naafiri','TFT9_Taliyah','TFT9_Swain','TFT9_Warwick','TFT9_Soraka','TFT9_Qiyana','TFT9_Galio','TFT9_TwistedFate','TFT9_Sett','TFT9_Ashe','TFT9_Jinx','TFT9_Kassadin',]
UNITS3 = ['TFT9_Jayce','TFT9_Ekko','TFT9_Nautilus','TFT9_MissFortune','TFT9_Taric','TFT9_Neeko','TFT9_Katarina','TFT9_Quinn','TFT9_Darius','tft9_reksai','TFT9_Karma','TFT9_Sona','TFT9_VelKoz',]
UNITS4 = ['TFT9_Nilah','TFT9_Silco','TFT9_JarvanIV','TFT9_Azir','TFT9_Nasus','TFT9_Fiora','TFT9_KaiSa','TFT9_Sejuani','TFT9_Mordekaiser','TFT9_Xayah','TFT9_Shen','TFT9_Aphelios',]
# miss ryze noxus, shadowisles, zaun, will confirm all ryzes
UNITS5 = ['TFT9_KSante','TFT9b_Aatrox','TFT9_Heimerdinger','TFT9_Sion','TFT9_Gangplank','TFT9_Ahri','TFT9_BelVeth','TFT9_RyzeTargon','TFT9_RyzeShurima','TFT9_RyzePiltover','TFT9_RyzeIonia','TFT9_RyzeBandleCity','TFT9_RyzeDemacia','TFT9_RyzeFreljord','TFT9_RyzeNoxus','TFT9_RyzeShadowIsles','TFT9_RyzeZaun',]
# armorclad = juggernaut, marksman = gunner, preserver = invoker
TRAITS = ['Set9_Armorclad','Set9_Bruiser','Set9_Marksman','Set9_Piltover','Set9_Rogue','Set9_Sorcerer','Set9_Zaun','Set9b_Bilgewater','Set9b_Vanquisher','Set9_Bastion','Set9_Demacia','Set9_Shurima','Set9_Strategist','Set9_Challenger','Set9_Multicaster','Set9_Noxus','Set9_Slayer','Set9b_Darkin','Set9_Preserver','Set9_Targon','Set9_Technogenius','Set9_Ionia','Set9_Void','Set9_Ixtal','Set9_Freljord','Set9_Wanderer','Set9_ReaverKing','Set9_Empress',]
RIOT_API = os.environ.get('RIOT_API')

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
    con.isolation_level = None
    cur = con.cursor()
    sample_matches = ["KR_6699363465","KR_6699331498","KR_6699306560","KR_6699280913","KR_6699266683","OC1_585314895","OC1_585315221","OC1_585309892","OC1_585310292","OC1_585305572","OC1_585300927","OC1_585300609","KR_6699383920","KR_6699352607","KR_6699330790","KR_6699314296","KR_6699294617"]
    cnt = 1
    for match in sample_matches:
        print(f"match number {cnt}, currently {match}")
        cnt += 1
        server = ''
        for c in match:
            if c == '_':
                break
            server += c.lower()
        region = server_to_region(server)
        url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match}"
        headers = {'X-Riot-Token': RIOT_API}
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            print(res.status_code)
            return
        json = res.json()
        for participant in json['info']['participants']:
            for trait in participant['traits']:
                cur.execute("SELECT * FROM traits WHERE name = ?", (trait['name'],))
                if cur.fetchone() is not None:  # skip stored traits
                    continue
                cur.execute("""
                    INSERT INTO traits (name, tier_total)
                    VALUES (?, ?)
                """, (trait['name'], trait['tier_total']))
            for unit in participant['units']:
                cur.execute("SELECT * FROM units WHERE character_id = ?", (unit['character_id'],))
                if cur.fetchone() is not None:
                    continue
                cur.execute("""
                    INSERT INTO units (character_id, rarity)
                    VALUES (?, ?)
                """, (unit['character_id'], unit['rarity']))
    con.close()

def manual_per_set():
    ...

# reset_db()
# init_per_set()
# print(len(UNITS1))
# print(len(UNITS2))
# print(len(UNITS3))
# print(len(UNITS4))
# print(len(UNITS5))
# print(len(TRAITS))

