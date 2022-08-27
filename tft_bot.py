import logging
from discord.ext import commands
from urllib import request
import requests
from raw_tft import RIOT_API, DISCORD_API

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix="$")

@bot.command()
async def matches(ctx, summonerName, queue='normal'):
    summoner = requests.get(f'https://oc1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}?api_key={RIOT_API}').json()
    if "puuid" not in summoner:
        await ctx.reply(f"{summonerName} does not exist")
        return
    puuid = summoner["puuid"]
    matches = requests.get(f'https://sea.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?api_key={RIOT_API}').json()

    if queue == 'ranked':
        matches = list(filter(
            lambda match: requests.get(f'https://sea.api.riotgames.com/tft/match/v1/matches/{match}?api_key={RIOT_API}').json()['info']['queue_id'] == 1100, matches))
        
    await ctx.reply(f"{summonerName}'s {queue} matches: {len(matches)}")

@bot.command()
async def help(ctx):

bot.run(DISCORD_API)
