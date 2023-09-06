import logging
import requests
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
REGIONS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
RIOT_API = os.environ.get('RIOT_API')

def matches(summonerName, queue='normal'):
    summoner = requests.get(
        f'https://oc1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}?api_key={RIOT_API}').json()
    if "puuid" not in summoner:
        print(f"{summonerName} does not exist")
        return
    puuid = summoner["puuid"]
    matches = requests.get(f'https://sea.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?api_key={RIOT_API}').json()

    if queue == 'ranked':
        matches = list(filter(
            lambda match: requests.get(
                f'https://sea.api.riotgames.com/tft/match/v1/matches/{match}?api_key={RIOT_API}')
                .json()['info']['queue_id'] == 1100, matches))
        
    print(f"{summonerName}'s {queue} matches: {len(matches)}")
    return

def get_league(region, league):
    '''league: master, grandmaster, master'''
    url = f"https://{region}.api.riotgames.com/tft/league/v1/{league}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
    json = res.json()
    cnt = 0
    rank_vals = set()
    for entry in json['entries']:
        rank_vals.add(entry['rank'])
        cnt += 1
        if entry['summonerName'] == 'C9 k3soju':
            print('Oh bet! It\'s lil bro!')
            print(entry)
    print(rank_vals)
    print(f'{league}s count in {region}: {cnt}')

get_league('na1', 'master')
get_league('na1', 'grandmaster')
get_league('na1', 'challenger')
