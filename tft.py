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
    con.isolation_level = None
    cur = con.cursor()
    server = 'na1'
    region = server_to_region(server) 
    # players = ['ID Tiêu Daoo', 'HNZ boi tháng 8', 'Hiu Jc', 'TFA SukiReiichi', 'H E N I S S', 'NG Yugi', 'choicogiaitri', 'Forget The Past', 'Hôm Nay Tí Buồn', 'DNR Cu Chỉ Ngược', 'htd2006', 'p1va', 'HNZ MIDFEEDD', 'Sự Tĩnh Lặng', 'Cold snap', 'Onlive TrungVla', 'VN YBY1', 'KND Finn', 'Perfaketo', 'y Tiger1']
    # for player in players:
    #     list_of_matches = summoner_to_matches(cur, server, region, player)
    #     print('found summoner!')
    #     for match in list_of_matches:
    #         insert_match(cur, server, region, match)
    # server_to_matches(cur, server, region)
    
    update_best_items(cur)

    avg(cur, 'traits')
    avg(cur, 'units')
    avg(cur, 'units', 'maxed')
    avg(cur, 'items')
    avg(cur, 'augments')

    check_db(cur)
    con.close()

logging.basicConfig(level=logging.INFO)
SERVERS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
VERSION = 'Version 13.18'
# items and units not making sense to be included
IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
IGNOREDUNITS = ["TFT9_HeimerdingerTurret", "TFT9_THex"]
# imposter items
EXCEPTIONITEMS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
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


# will add find each unit if have the chance
def update_best_items(cursor):
    cursor.execute('SELECT character_id FROM units')
    rows = cursor.fetchall()
    for row in rows:  # for each unit, get the best 3 items
        unit = row[0]
        cursor.execute('''SELECT us.item1, us.item2, us.item3, ps.placement 
                    FROM unit_states us INNER JOIN player_states ps
                    ON us.match_id = ps.match_id AND us.puuid = ps.puuid
                    WHERE us.character_id = ?
            ''', (unit,))
        rs = cursor.fetchall()
        avg_map = {}  # dictionary of item: [sum, cnt]
        for r in rs:
            items = r[:3]
            placement = r[3]
            for item in items:
                if item is not None:
                    if item not in avg_map:
                        avg_map[item] = [placement, 1]
                    else:
                        avg_map[item][0] += placement
                        avg_map[item][1] += 1
        li = []
        for item, val in avg_map.items():
            avrg = val[0]/val[1]
            li.append((val[1], avrg, item))

        # first sort by matches
        li.sort(key=lambda s: s[0], reverse=True)
        ornn1 = [s for s in li if (re.search(r'.*Shimmerscale.+$', s[2]) and s[2] not in EXCEPTIONITEMS)]
        ornn2 = [s for s in li if (re.search(r'.*Ornn.+$', s[2]) and s[2] not in EXCEPTIONITEMS)]
        ornn = ornn1 + ornn2
        radiant = [s for s in li if (s[2].endswith('Radiant') and s[2] not in EXCEPTIONITEMS)]
        emblem = [s for s in li if (s[2].endswith('Emblem') and s[2] not in EXCEPTIONITEMS)]
        all_nonnormals = [s[2] for s in (ornn+radiant+emblem)] + IGNOREDITEMS
        normal = [s for s in li if s[2] not in all_nonnormals]

        # now sort by avrg
        best_normals = sorted(normal[:10], key=lambda x: x[1])
        best_radiants = sorted(radiant[:5], key=lambda x: x[1])
        best_emblems = sorted(emblem[:3], key=lambda x: x[1])
        best_ornns = sorted(ornn[:3], key=lambda x: x[1])
        with open('meta.txt', 'a') as file:
            file.write('---------BEST ITEMS---------\n')
            file.write(f"best normals for {unit} are {[s[2] for s in best_normals]}\n")
            file.write(f"best radiants for {unit} are {[s[2] for s in best_radiants]}\n")
            file.write(f"best emblems for {unit} are {[s[2] for s in best_emblems]}\n")
            file.write(f"best ornns for {unit} are {[s[2] for s in best_ornns]}\n")


def avg(cursor, table, arg=None):
    '''table = traits, units, items, augments.
    if 'units' is passed, arg can be 'maxed'.
    if 'items' is passed, arg can be 'normal', 'radiant', 'ornn', 'emblem'.
    '''
    head = 'SELECT CAST(sum_placement AS REAL) / num_placement AS avg'
    if table == 'traits':
        cursor.execute(f"{head}, name, tier_current FROM {table}")
    elif table == 'items':
        if arg is None:
            avg(cursor, table, arg='normal')
            avg(cursor, table, arg='radiant')
            avg(cursor, table, arg='ornn')
            avg(cursor, table, arg='emblem')
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
        avrg, col1, col2 = row[0], row[1], None
        if len(row) == 3:
            col2 = row[2]
        if avrg is not None:
            li.append((avrg, col1, col2))
    li.sort(key=lambda x: x[0])
    with open('meta.txt', 'a') as file:
        if arg in ['normal', 'radiant', 'ornn', 'emblem']:
            file.write(f"---------{arg.upper()} ITEMS----------\n")
        elif arg == 'maxed':
            file.write(f"---------3 STAR UNITS----------\n")
        else:
            file.write(f"--------------{table.upper()}---------------\n")
        for row in li:
            if table == 'traits':
                file.write(f"average placement of tier {row[2]} {row[1]} is {row[0]:.2f}\n")
            else:
                file.write(f"average placement of {row[1]} is {row[0]:.2f}\n")

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
                cursor.execute('SELECT name FROM augments WHERE name = ?', (name,))
                if cursor.fetchone() is None:
                    cursor.execute('''INSERT INTO augments (name, sum_placement, num_placement) VALUES (?, ?, ?)
                                ''', (name, participant['placement'], 1))
                else:
                    cursor.execute('''UPDATE augments SET sum_placement = sum_placement + ?, num_placement = num_placement + 1
                                WHERE name = ?''', (participant['placement'], name))
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
                    for item in items:
                        if item not in IGNOREDITEMS:
                            cursor.execute('SELECT sum_placement FROM items WHERE name = ?', (item,))
                            r = cursor.fetchone()
                            if not r:
                                cursor.execute("INSERT INTO items (name, sum_placement, num_placement) VALUES (?, ?, 1)"
                                    , (item, participant['placement']))
                            elif r[0] is None:
                                cursor.execute('UPDATE items SET sum_placement = ?, num_placement = 1 WHERE name = ?', (participant['placement'], item))
                            else:
                                cursor.execute('UPDATE items SET sum_placement = sum_placement + ?, num_placement = num_placement + 1 WHERE name = ?', (participant['placement'], item))
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
                        cursor.execute('UPDATE units SET sum_placement = ?, num_placement = 1 WHERE character_id = ?', (participant['placement'], unit['character_id']))
                    else:
                        cursor.execute("""
                            UPDATE units SET sum_placement = sum_placement + ?, num_placement = num_placement + 1 WHERE character_id = ?
                        """, (participant['placement'], unit['character_id']))
                    # update units_3 avg
                    if unit['tier'] == 3 and (unit['rarity'] in [0, 1, 2]):  # 3 star units for tier 3 and below
                        cursor.execute('SELECT sum_placement FROM units_3 WHERE character_id = ?', (unit['character_id'],))
                        r = cursor.fetchone()[0]
                        if r is None:
                            cursor.execute('UPDATE units_3 SET sum_placement = ?, num_placement = 1 WHERE character_id = ?', (participant['placement'], unit['character_id']))
                        else:
                            cursor.execute("""
                                UPDATE units_3 SET sum_placement = sum_placement + ?, num_placement = num_placement + 1 WHERE character_id = ?
                            """, (participant['placement'], unit['character_id']))
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
                        cursor.execute("INSERT INTO traits (name, tier_current, sum_placement, num_placement) VALUES (?, ?, ?, 1)"
                                    , (trait['name'],trait['tier_current'],participant['placement']))
                    elif r[2] is None:
                        cursor.execute("UPDATE traits SET sum_placement = ?, num_placement = 1 WHERE name = ? AND tier_current = ?"
                                    , (participant['placement'], trait['name'], trait['tier_current']))
                    else:
                        cursor.execute("""
                            UPDATE traits SET sum_placement = sum_placement + ?, num_placement = num_placement + 1 
                            WHERE name = ? AND tier_current = ?
                        """, (participant['placement'], trait['name'], trait['tier_current']))

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
        for now only challengers (~500ish) as rate limit is not feeling good.
    '''

    challengers = get_league(cursor, server, region, 'challenger')
    grandmasters = get_league(cursor, server, region, 'grandmaster')
    mastercnt = 1000 - len(challengers) - len(grandmasters)
    masters = get_league(cursor, server, region, 'master', mastercnt)
    for i, name in enumerate(challengers):
        print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        for match in list_of_matches:
            insert_match(cursor, server, region, match)
    for i, name in enumerate(grandmasters):
        print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        for match in list_of_matches:
            insert_match(cursor, server, region, match)
    # for i, name in enumerate(masters):
        # print(f"player {i}")
        # list_of_matches = summoner_to_matches(cursor, server, region, name)
        # for match in list_of_matches:
        #     insert_match(cursor, server, region, match)

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
