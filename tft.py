import sqlite3
import logging
import requests
import os
import random
import time
from dotenv import load_dotenv
load_dotenv()

def main():
    con = sqlite3.connect("raw_matches.db")
    cur = con.cursor()
    server = 'na1'
    region = server_to_region(server)
    server_to_matches(cur, server, region)
    con.commit()
    check_db(cur)
    con.close()

logging.basicConfig(level=logging.INFO)
SERVERS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
VERSION = 'Version 13.17'
MAPPINGS = {  # this is not 100% true, for now I can only verify na1 and vn2
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
            augments = participant['augments']
            while len(augments) < 3:
                augments.append(None)
            cursor.execute("""
                INSERT INTO player_states (puuid, match_id, augment1, augment2, augment3, placement)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (participant['puuid'], match_id, augments[0], augments[1], augments[2], participant['placement'],))
            for unit in participant['units']:
                items = unit['itemNames']
                while len(items) < 3:
                    items.append(None)
                cursor.execute("""
                    INSERT INTO unit_states (character_id, puuid, match_id, tier, item1, item2, item3)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (unit['character_id'], participant['puuid'], match_id, unit['tier'], items[0], items[1], items[2],))
            for trait in participant['traits']:
                if trait['tier_current'] > 0:
                    cursor.execute("""
                        INSERT INTO trait_states (name, puuid, match_id, tier_current)
                        VALUES (?, ?, ?, ?)
                    """, (trait['name'], participant['puuid'], match_id, trait['tier_current'],))

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
    # grandmasters = get_league(cursor, server, region, 'grandmaster')
    # mastercnt = 2000 - len(challengers) - len(grandmasters)
    # masters = get_league(cursor, server, region, 'master', mastercnt)
    cnt = 0
    for name in challengers:
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        cnt += 1
        print(f"currently player {cnt}")
        for match in list_of_matches:
            insert_match(cursor, server, region, match)
    # for name in grandmasters:
    #     list_of_matches = summoner_to_matches(cursor, server, region, name)
    #     for match in list_of_matches:
    #         insert_match(cursor, server, region, match)
    # for name in masters:
    #     list_of_matches = summoner_to_matches(cursor, server, region, name)
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
        summonerNames = [x['summonerName'] for x in json['entries'] if x['leaguePoints'] > 100]
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
    print(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM player_states")
    print(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM unit_states")
    print(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM trait_states")
    print(cursor.fetchone()[0])

if __name__ == "__main__":
    main()
