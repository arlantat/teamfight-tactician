import sqlite3
import logging
import requests
import os
import random
import time
import re
from dotenv import load_dotenv
load_dotenv()

def main():
    con = sqlite3.connect("raw_matches.db")
    # con.isolation_level = None
    cur = con.cursor()
    server = 'vn2'
    region = server_to_region(server) 
    # players = ['ID Tiêu Daoo', 'HNZ boi tháng 8', 'Hiu Jc', 'TFA SukiReiichi', 'H E N I S S', 'NG Yugi', 'choicogiaitri', 'Forget The Past', 'Hôm Nay Tí Buồn', 'DNR Cu Chỉ Ngược', 'htd2006', 'p1va', 'HNZ MIDFEEDD', 'Sự Tĩnh Lặng', 'Cold snap', 'Onlive TrungVla', 'VN YBY1', 'KND Finn', 'Perfaketo', 'y Tiger1']
    # for player in players:
    #     list_of_matches = summoner_to_matches(cur, server, region, player)
    #     print('found summoner!')
    #     for match in list_of_matches:
    #         insert_match(cur, server, region, match)
    # server_to_matches(cur, server, region)
    update_meta(cur)

    check_db(cur)
    con.close()

logging.basicConfig(level=logging.INFO)
SERVERS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
VERSION = 'Version 13.22'
# items, units and augments not making sense to be included
IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
IGNOREDUNITS = ["TFT9_HeimerdingerTurret", "TFT9_THex"]
IGNOREDAUGMENTS = []
# imposter items
EXCEPTIONITEMS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
# exclude radiants for demacia
DEMACIA = {
    'TFT9_Kayle': 'TFT5_Item_GiantSlayerRadiant',
    'TFT9_Poppy': 'TFT5_Item_FrozenHeartRadiant',
    'TFT9_Galio': 'TFT5_Item_RedemptionRadiant',
    'TFT9_Sona': 'TFT5_Item_SpearOfShojinRadiant',
    'TFT9_Quinn': 'TFT5_Item_DeathbladeRadiant',
    'TFT9_Fiora': 'TFT5_Item_SteraksGageRadiant',
    'TFT9_JarvanIV': 'TFT5_Item_WarmogsArmorRadiant'
}
MAPPINGS = {  # na1, vn2, kr confirmed
    SERVERS[0]: REGIONS[0],
    SERVERS[1]: REGIONS[2],
    SERVERS[2]: REGIONS[2],
    SERVERS[3]: REGIONS[1],
    SERVERS[4]: REGIONS[1],
    SERVERS[5]: REGIONS[0],
    SERVERS[6]: REGIONS[0],
    SERVERS[7]: REGIONS[0],
    SERVERS[8]: REGIONS[3],
    SERVERS[9]: REGIONS[1],
    SERVERS[10]: REGIONS[2],
    SERVERS[11]: REGIONS[1],
    SERVERS[12]: REGIONS[1],
    SERVERS[13]: REGIONS[2],
    SERVERS[14]: REGIONS[1],
    SERVERS[15]: REGIONS[3]
    }
RIOT_API = os.environ.get('RIOT_API')


def update_meta(cursor):
    with open('meta.txt', 'w') as file:
        update_best_items(file, cursor)
        avg(file, cursor, 'traits')
        avg(file, cursor, 'units')
        avg(file, cursor, 'units', 'maxed')
        avg(file, cursor, 'items')
        avg(file, cursor, 'augments')


# added find best units for each item here, but still want to separate it in a different module
def update_best_items(file, cursor):
    cursor.execute('''SELECT us.item1, us.item2, us.item3, ps.placement, us.tier, us.character_id 
                FROM unit_states us INNER JOIN player_states ps
                ON us.match_id = ps.match_id AND us.puuid = ps.puuid
        ''')
    rs = cursor.fetchall()
    unit_map = {} # dictionary of unit: item_map
    for r in rs:
        items = r[:3]
        placement = r[3]
        tier = r[4]
        unit = r[5]
        if unit not in unit_map:
            unit_map[unit] = {} # dictionary of item: [sum, cnt]
        for item in items:
            if item is not None:
                if item not in unit_map[unit]:
                    unit_map[unit][item] = [placement, 1]
                else:
                    unit_map[unit][item][0] += placement
                    unit_map[unit][item][1] += 1
    best_units = {}  # item: [cnt, avrg, unit]
    for unit, item_map in unit_map.items():
        li = []
        for item, val in item_map.items():
            avrg = val[0]/val[1]
            li.append((val[1], avrg, item))
            if item in EXCEPTIONITEMS or item in IGNOREDITEMS:
                continue
            if item not in best_units:
                best_units[item] = []
            best_units[item].append([val[1], avrg, unit])
        # first sort by matches
        li.sort(key=lambda s: s[0], reverse=True)

        ornn1 = [s for s in li if (re.search(r'.*Shimmerscale.+$', s[2]) and s[2] not in EXCEPTIONITEMS)]
        ornn2 = [s for s in li if (re.search(r'.*Ornn.+$', s[2]) and s[2] not in EXCEPTIONITEMS)]
        ornn = sorted((ornn1 + ornn2), key=lambda s: s[0], reverse=True)
        radiant = [s for s in li if (s[2].endswith('Radiant') and s[2] not in EXCEPTIONITEMS)]
        emblem = [s for s in li if (s[2].endswith('Emblem') and s[2] not in EXCEPTIONITEMS)]
        all_nonnormals = [s[2] for s in (ornn+radiant+emblem)] + IGNOREDITEMS
        normal = [s for s in li if s[2] not in all_nonnormals]

        # now sort by avrg
        best_normals = sorted(normal[:15], key=lambda x: x[1])
        best_radiants = sorted(radiant[:5], key=lambda x: x[1])
        best_emblems = sorted(emblem[:3], key=lambda x: x[1])
        best_ornns = sorted(ornn[:3], key=lambda x: x[1])
        file.write('---------BEST ITEMS---------\n')
        file.write(f"best normals for {unit} are {[(s[2], round(s[1], 2)) for s in best_normals]}\n")
        file.write(f"best radiants for {unit} are {[(s[2], round(s[1], 2)) for s in best_radiants]}\n")
        file.write(f"best emblems for {unit} are {[(s[2], round(s[1], 2)) for s in best_emblems]}\n")
        file.write(f"best ornns for {unit} are {[(s[2], round(s[1], 2)) for s in best_ornns]}\n")
    
    # best units for each item, same process
    file.write('---------BEST UNITS---------\n')
    for item in best_units:
        best_units[item].sort(key=lambda s: s[0], reverse=True)
        # if item in normal: unimplemented
        li = sorted(best_units[item][:7], key=lambda x: x[1])
        file.write(f"best units for {item} are {[(s[2], round(s[1], 2)) for s in li]}\n")


def avg(file, cursor, table, arg=None):
    '''table = traits, units, items, augments.
    if 'units' is passed, arg can be 'maxed'.
    if 'items' is passed, arg can be 'normal', 'radiant', 'ornn', 'emblem'.
    '''
    head = 'SELECT CAST(sum_placement AS REAL) / num_placement AS avg, CAST(top4 AS REAL) / num_placement AS top4_rate'
    if table == 'traits':
        cursor.execute(f"{head}, name, tier_current FROM {table}")
    elif table == 'items':
        if arg is None:
            avg(file, cursor, table, arg='normal')
            avg(file, cursor, table, arg='radiant')
            avg(file, cursor, table, arg='ornn')
            avg(file, cursor, table, arg='emblem')
            return
        else:
            cursor.execute(f"{head}, name FROM {table} WHERE class = ?", (arg,))
    elif table == 'augments':
        cursor.execute(f"{head}, name FROM {table}")
    elif table == 'units':
        if arg == 'maxed':
            table = 'units_3'
        cursor.execute(f"{head}, character_id FROM {table}")
    rows = cursor.fetchall()
    li = []
    for row in rows:
        avrg, top4_rate, col1, col2 = row[0], row[1], row[2], None
        if len(row) == 4:
            col2 = row[3]
        if avrg is not None:
            li.append((avrg, top4_rate, col1, col2))
    li.sort(key=lambda x: x[0])
    if arg in ['normal', 'radiant', 'ornn', 'emblem']:
        file.write(f"---------{arg.upper()} ITEMS----------\n")
    elif arg == 'maxed':
        file.write(f"---------3 STAR UNITS----------\n")
    else:
        file.write(f"--------------{table.upper()}---------------\n")
    for row in li:
        if table == 'traits':
            file.write(f"average placement of tier {row[3]} {row[2]} is {row[0]:.2f}, top 4 rate {row[1]*100:.2f}\n")
        else:
            if table == 'augments' and row[2].endswith(('Trait', 'Trait2', 'Emblem', 'Emblem2')):
                file.write(f"average placement of {row[2]} is {row[0]:.2f}, top 4 rate {(row[1]*100):.2f} EMBLEM OR TRAIT\n")
                continue
            file.write(f"average placement of {row[2]} is {row[0]:.2f}, top 4 rate {(row[1]*100):.2f}\n")

def insert_match(cursor, server, region, match_id):
    # save unnecessary get requests
    cursor.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,))
    if cursor.fetchone() is not None:
        return
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        # wait and retry if rate limit exceeded
        if res.status_code == 429:
            time.sleep(25)
            insert_match(cursor, server, region, match_id)
        return
    json = res.json()
    info = json['info']
    if info['game_version'].startswith(VERSION) and info['queue_id'] == 1100:
        cursor.execute("INSERT INTO matches (match_id) VALUES (?)", (match_id,))
        for participant in info['participants']:
            # update augments avg
            augments = participant['augments']
            for name in augments:
                cursor.execute('SELECT sum_placement FROM augments WHERE name = ?', (name,))
                r = cursor.fetchone()
                if not r:
                    cursor.execute('''INSERT INTO augments (name, sum_placement, num_placement, top4) VALUES (?, ?, ?, ?)
                                ''', (name, participant['placement'], 1, (1 if participant['placement']<=4 else 0)))
                elif r[0] is None:
                    cursor.execute('''UPDATE augments SET sum_placement = ?, num_placement = 1, top4 = ? WHERE name = ?'''
                                    , (participant['placement'], (1 if participant['placement']<=4 else 0), name))
                else:
                    cursor.execute('''UPDATE augments SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                                WHERE name = ?''', (participant['placement'], (1 if participant['placement']<=4 else 0), name))
            while len(augments) < 3:
                augments.append(None)
            cursor.execute("""
                INSERT INTO player_states (puuid, match_id, augment1, augment2, augment3, placement)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (participant['puuid'], match_id, augments[0], augments[1], augments[2], participant['placement'],))
            for unit in participant['units']:
                if unit['character_id'] not in IGNOREDUNITS:
                    # update items avg
                    items = unit['itemNames']
                    # ignore the radiant item for demacia units
                    if unit['character_id'] in DEMACIA and DEMACIA[unit['character_id']] in items:
                        items[items.index(DEMACIA[unit['character_id']])] = None
                    for item in items:
                        if item is not None or item not in IGNOREDITEMS:
                            cursor.execute('SELECT sum_placement FROM items WHERE name = ?', (item,))
                            r = cursor.fetchone()
                            if not r:
                                cursor.execute("INSERT INTO items (name, sum_placement, num_placement, top4) VALUES (?, ?, 1, ?)"
                                    , (item, participant['placement'], (1 if participant['placement']<=4 else 0)))
                            elif r[0] is None:
                                cursor.execute('''UPDATE items SET sum_placement = ?, num_placement = 1, top4 = ? WHERE name = ?'''
                                            , (participant['placement'], (1 if participant['placement']<=4 else 0), item))
                            else:
                                cursor.execute('''UPDATE items SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? WHERE name = ?'''
                                            , (participant['placement'], (1 if participant['placement']<=4 else 0), item))
                    while len(items) < 3:
                        items.append(None)
                    cursor.execute("""
                        INSERT INTO unit_states (character_id, puuid, match_id, tier, item1, item2, item3)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (unit['character_id'], participant['puuid'], match_id, unit['tier'], items[0], items[1], items[2]))
                    # update units avg
                    cursor.execute('SELECT sum_placement FROM units WHERE character_id = ?', (unit['character_id'],))
                    r = cursor.fetchone()[0]
                    if r is None:
                        cursor.execute('''UPDATE units SET sum_placement = ?, num_placement = 1, top4 = ? WHERE character_id = ?'''
                                    , (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
                    else:
                        cursor.execute("""
                            UPDATE units SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? WHERE character_id = ?
                        """, (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
                    # update units_3 avg
                    if unit['tier'] == 3 and (unit['rarity'] in [0, 1, 2]):  # 3 star units for tier 3 and below
                        cursor.execute('SELECT sum_placement FROM units_3 WHERE character_id = ?', (unit['character_id'],))
                        r = cursor.fetchone()[0]
                        if r is None:
                            cursor.execute('''UPDATE units_3 SET sum_placement = ?, num_placement = 1, top4 = ? WHERE character_id = ?'''
                                        , (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
                        else:
                            cursor.execute("""
                                UPDATE units_3 SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? WHERE character_id = ?
                            """, (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
            for trait in participant['traits']:
                if trait['tier_current'] > 0:
                    cursor.execute("""
                        INSERT INTO trait_states (name, puuid, match_id, tier_current)
                        VALUES (?, ?, ?, ?)
                    """, (trait['name'], participant['puuid'], match_id, trait['tier_current'],))
                    # update traits avg
                    cursor.execute("SELECT name, tier_current, sum_placement FROM traits WHERE name = ? AND tier_current = ?", (trait['name'],trait['tier_current']))
                    r = cursor.fetchone()
                    if not r:
                        cursor.execute("INSERT INTO traits (name, tier_current, sum_placement, num_placement, top4) VALUES (?, ?, ?, 1, ?)"
                                    , (trait['name'],trait['tier_current'],participant['placement'],(1 if participant['placement']<=4 else 0)))
                    elif r[2] is None:
                        cursor.execute("UPDATE traits SET sum_placement = ?, num_placement = 1, top4 = ? WHERE name = ? AND tier_current = ?"
                                    , (participant['placement'], (1 if participant['placement']<=4 else 0), trait['name'], trait['tier_current']))
                    else:
                        cursor.execute("""
                            UPDATE traits SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                            WHERE name = ? AND tier_current = ?
                        """, (participant['placement'], (1 if participant['placement']<=4 else 0), trait['name'], trait['tier_current']))

def summoner_to_matches(cursor, server, region, summonerName, count=10) -> list:
    '''return list_of_matches'''
    puuid = name_to_puuid(server, server_to_region(server), summonerName)
    if puuid is None:
        return
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return []
    list_of_matches = res.json()
    return list_of_matches

def server_to_matches(cursor, server, region):
    '''
        from a given server, insert 10 closest matches from each of 2000 players to the database.
        for now only challengers and gms (~1000ish) with current rate limit.
    '''

    challengers = get_league(cursor, server, region, 'challenger')
    grandmasters = get_league(cursor, server, region, 'grandmaster')
    # mastercnt = 2000 - len(challengers) - len(grandmasters)
    # masters = get_league(cursor, server, region, 'master', mastercnt)
    for i, name in enumerate(challengers):
        print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        if list_of_matches:
            for match in list_of_matches:
                insert_match(cursor, server, region, match)
    for i, name in enumerate(grandmasters):
        print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        if list_of_matches:
            for match in list_of_matches:
                insert_match(cursor, server, region, match)
    # for i, name in enumerate(masters):
        # print(f"player {i}")
        # list_of_matches = summoner_to_matches(cursor, server, region, name)
        # if list_of_matches:
        #     for match in list_of_matches:
        #         insert_match(cursor, server, region, match)

def get_league(cursor, server, region, league, mastercnt=0) -> list:
    '''league: master, grandmaster, master'''
    '''return list of summonerName'''

    url = f"https://{server}.api.riotgames.com/tft/league/v1/{league}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return []
    json = res.json()

    if league == 'master':
        summonerNames = [x['summonerName'] for x in json['entries'] if x['leaguePoints'] > 0]
        print(f'{league}s count in {server}: {len(json["entries"])}')
        if len(summonerNames) <= mastercnt:
            return summonerNames
        return random.sample(summonerNames, mastercnt)
    print(f'{league}s count in {server}: {len(json["entries"])}')
    return [x['summonerName'] for x in json['entries']]

def server_to_region(server):
    return MAPPINGS[server]

def name_to_puuid(server, region, summonerName):
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    json = res.json()
    return json['puuid']

def check_db(cursor):
    cursor.execute("SELECT COUNT(*) FROM matches")
    print(f"matches: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM player_states")
    print(f"player_states: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM unit_states")
    print(f"unit_states: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM trait_states")
    print(f"trait_states: {cursor.fetchone()[0]}")

if __name__ == "__main__":
    main()
