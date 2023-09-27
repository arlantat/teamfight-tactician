import sqlite3
import os
import requests
from tft import server_to_region
from dotenv import load_dotenv
import re
load_dotenv()

# UNITS1 = ['TFT9_Graves','TFT9_Orianna','TFT9_Illaoi','TFT9_Renekton','TFT9_Irelia','TFT9_Samira','TFT9_Milio','TFT9_Cassiopeia','TFT9_Poppy','TFT9_Kayle','TFT9_ChoGath','TFT9_Malzahar','TFT9_Jhin',]
# UNITS2 = ['TFT9_Vi','TFT9_Naafiri','TFT9_Taliyah','TFT9_Swain','TFT9_Warwick','TFT9_Soraka','TFT9_Qiyana','TFT9_Galio','TFT9_TwistedFate','TFT9_Sett','TFT9_Ashe','TFT9_Jinx','TFT9_Kassadin',]
# UNITS3 = ['TFT9_Jayce','TFT9_Ekko','TFT9_Nautilus','TFT9_MissFortune','TFT9_Taric','TFT9_Neeko','TFT9_Katarina','TFT9_Quinn','TFT9_Darius','tft9_reksai','TFT9_Karma','TFT9_Sona','TFT9_VelKoz',]
# UNITS4 = ['TFT9_Nilah','TFT9_Silco','TFT9_JarvanIV','TFT9_Azir','TFT9_Nasus','TFT9_Fiora','TFT9_KaiSa','TFT9_Sejuani','TFT9_Mordekaiser','TFT9_Xayah','TFT9_Shen','TFT9_Aphelios',]
# UNITS5 = ['TFT9_KSante','TFT9b_Aatrox','TFT9_Heimerdinger','TFT9_Sion','TFT9_Gangplank','TFT9_Ahri','TFT9_BelVeth','TFT9_RyzeTargon','TFT9_RyzeShurima','TFT9_RyzePiltover','TFT9_RyzeIonia','TFT9_RyzeBandleCity','TFT9_RyzeDemacia','TFT9_RyzeFreljord','TFT9_RyzeNoxus','TFT9_RyzeShadowIsles','TFT9_RyzeZaun','TFT9_RyzeBilgewater','TFT9_RyzeIxtal']
# armorclad = juggernaut, marksman = gunner, preserver = invoker
# TRAITS = ['Set9_Armorclad','Set9_Bruiser','Set9_Marksman','Set9_Piltover','Set9_Rogue','Set9_Sorcerer','Set9_Zaun','Set9b_Bilgewater','Set9b_Vanquisher','Set9_Bastion','Set9_Demacia','Set9_Shurima','Set9_Strategist','Set9_Challenger','Set9_Multicaster','Set9_Noxus','Set9_Slayer','Set9b_Darkin','Set9_Preserver','Set9_Targon','Set9_Technogenius','Set9_Ionia','Set9_Void','Set9_Ixtal','Set9_Freljord','Set9_Wanderer','Set9_ReaverKing','Set9_Empress',]

IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
EXCEPTIONITEMS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
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
            name TEXT PRIMARY KEY,
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
        sample_matches = ["KR_6699363465","KR_6699331498","KR_6699306560","KR_6699280913","KR_6699266683","OC1_585314895","OC1_585315221","OC1_585309892","OC1_585310292","OC1_585305572","OC1_585300927","OC1_585300609","KR_6699383920","KR_6699352607","KR_6699330790","KR_6699314296","KR_6699294617"]
        init_per_set(sample_matches)
        return
    con = sqlite3.connect("raw_matches.db")
    con.isolation_level = None
    cur = con.cursor()
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM player_states")
    cur.execute("DELETE FROM unit_states")
    cur.execute("DELETE FROM trait_states")
    cur.execute("DELETE FROM augments")
    cur.execute("UPDATE units SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    cur.execute("UPDATE units_3 SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    cur.execute("UPDATE traits SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    cur.execute("UPDATE items SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    con.close()

def init_per_set(sample_matches):
    con = sqlite3.connect("raw_matches.db")
    con.isolation_level = None
    cur = con.cursor()
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
    con.close()

# try first to be sure then commit
def manual_per_set():
    con = sqlite3.connect("raw_matches.db")
    # con.isolation_level = None
    cur = con.cursor()

    # manual units
    character_ids = ['TFT9_RyzeNoxus','TFT9_RyzeShadowIsles','TFT9_RyzeZaun','TFT9_RyzeBilgewater','TFT9_RyzeIxtal']
    for character_id in character_ids:
        cur.execute("SELECT * FROM units WHERE character_id = ?", (character_id,))
        if cur.fetchone() is not None:
            continue
        cur.execute("""
            INSERT INTO units (character_id, rarity)
            VALUES (?, ?)
        """, (character_id, 6))

    # manual items
    cur.execute('SELECT item1, item2, item3 FROM unit_states')
    items = set()
    for row in cur.fetchall():
        for item in row:
            if item is not None:
                items.add(item)
    li = list(items)
    ornn1 = [s for s in li if re.search(r'.*Shimmerscale.+$', s)]
    ornn2 = [s for s in li if re.search(r'.*Ornn.+$', s)]
    radiant = [s for s in li if s.endswith('Radiant')]
    emblem = [s for s in li if s.endswith('Emblem')]
    others = [s for s in li if s not in ornn1+ornn2+radiant+emblem+IGNOREDITEMS]
    for item in li:
        if item in IGNOREDITEMS:
            continue
        elif item in EXCEPTIONITEMS:
            cur.execute('INSERT INTO items (name, class) VALUES (?, ?)', (item, 'normal'))
        elif item in ornn1 or item in ornn2:
            cur.execute('INSERT INTO items (name, class) VALUES (?, ?)', (item, 'ornn'))
        elif item in radiant:
            cur.execute('INSERT INTO items (name, class) VALUES (?, ?)', (item, 'radiant'))
        elif item in emblem:
            cur.execute('INSERT INTO items (name, class) VALUES (?, ?)', (item, 'emblem'))
        else:
            cur.execute('INSERT INTO items (name, class) VALUES (?, ?)', (item, 'normal'))
    cur.execute('SELECT name, class from items')
    print(cur.fetchall())
    
    
    
    
    
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

