import sqlite3
import logging
import requests
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
SERVERS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
VERSION = 'VERSION 13.17'
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

def match_info(region, match):
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    info = res.json()['info']
    if info['game_version'].startswith(VERSION):
        con = sqlite3.connect("matches.db")
        cur = con.cursor()
        for participant in info['participants']:
            ...



def get_puuid(server, summonerName):
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    json = res.json()
    region = MAPPINGS[server]
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

print(matches('na1', 'C9 k3soju', count=5))
