from urllib import request
import requests

from secrets import RIOT_API

APIKEY = "RGAPI-1d2ac64d-61ab-44bb-8cb0-0602a895a9b9"
RIOT_API = "RGAPI-1d2ac64d-61ab-44bb-8cb0-0602a895a9b9"
DISCORD_API = 'MTAwNjc5ODE3ODY4ODk3MDc3Mg.Geajnt.zIIUDQgIqpRqqIC6qlvwhmoCCzlV3UEusijye8'

if __name__ == '__main__':
    summonerName = input("Input summoner's name: ")

def last20_matches(queue='normal'):
    summoner = requests.get(f'https://oc1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}?api_key={APIKEY}').json()
    print(summoner)
    puuid = summoner["puuid"]
    matches = requests.get(f'https://sea.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?api_key={APIKEY}').json()
    
    if queue == 'ranked':
        return len(list(filter(
            lambda match: requests.get(f'https://sea.api.riotgames.com/tft/match/v1/matches/{match}?api_key={APIKEY}').json()['info']['queue_id'] == 1100, matches)))

    return len(matches)

if __name__ == '__main__':
    total = last20_matches()
    ranked = last20_matches('ranked')
    print(f"{summonerName}'s Total matches: {total}")
    print(f"{summonerName}'s Ranked matches: {ranked}")
