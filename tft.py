import sqlite3
import logging
import requests
import os
from dotenv import load_dotenv
load_dotenv()

def main():
    con = sqlite3.connect("raw_matches.db")
    cur = con.cursor()

    # will double check this again
    # insert_match(cur, 'na1', 'NA1_4761820603')
    # cur.execute('SELECT * FROM matches')
    # print(len(cur.fetchall()))
    # cur.execute('SELECT * FROM player_states')
    # print(len(cur.fetchall()))
    # cur.execute('SELECT * FROM unit_states')
    # print(len(cur.fetchall()))
    # cur.execute('SELECT * FROM trait_states')
    # print(len(cur.fetchall()))
    con.close()

logging.basicConfig(level=logging.INFO)
SERVERS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
VERSION = 'Version 13.17'
MAPPINGS = {
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
    SERVERS[15]: REGIONS[1]
    }
RIOT_API = os.environ.get('RIOT_API')

# 92 traits for 1 match alone is quite a problem. That's because even inactive traits are stored.
def insert_match(cursor, server, match_id):
    region = server_to_region(server)
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    json = res.json()
    info = json['info']
    if info['game_version'].startswith(VERSION) and info['queue_id'] == 1100:
        cursor.execute("INSERT OR IGNORE INTO matches (match_id) VALUES (?)", (match_id,))
        if cursor.rowcount == 0:  # duplicate match
            print('wtf2')
            return
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
                cursor.execute("""
                    INSERT INTO trait_states (name, puuid, match_id, tier_current)
                    VALUES (?, ?, ?, ?)
                """, (trait['name'], participant['puuid'], match_id, trait['tier_current'],))

def get_puuid(server, summonerName):
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    json = res.json()
    region = server_to_region(server)
    return json['puuid'], region


def matches(server, summonerName, count=20):
    '''return list_of_matches and region'''
    puuid, region = get_puuid(server, summonerName)
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    list_of_matches = res.json()
    return list_of_matches, region

def get_league(server, league):
    '''league: master, grandmaster, master'''

    url = f"https://{server}.api.riotgames.com/tft/league/v1/{league}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    json = res.json()
    cnt = 0
    for entry in json['entries']:
        cnt += 1
        if entry['summonerName'] == 'C9 k3soju':
            print('Oh bet! It\'s lil bro!')
            print(entry)
    print(f'{league}s count in {server}: {cnt}')

def server_to_region(server):
    return MAPPINGS[server]

if __name__ == "__main__":
    main()
