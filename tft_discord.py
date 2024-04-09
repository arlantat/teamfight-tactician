import logging
import sqlite3

from discord.ext import commands
import os
import discord
from dotenv import load_dotenv

from tft import update_meta

load_dotenv()
RIOT_API = os.environ.get('RIOT_API')
MY_SERVER = os.environ.get('MY_SERVER')

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command('help')


@bot.command()
async def meta(ctx, fn=None):
    msg = await ctx.send("Processing, won't be long...")
    con = sqlite3.connect("tft_stats.db")
    cur = con.cursor()
    update_meta(cur, MY_SERVER, fn)
    con.close()
    await msg.delete()
    await ctx.send(file=discord.File('meta.txt'))


@bot.command()
async def about(ctx):
    embed = discord.Embed(title="About this Bot", color=0x55a7f7)
    embed.description = ("Con bot này là tâm sức của thaybuoi. Dữ liệu lấy từ các trận đấu gần nhất của tất cả người "
                         "chơi Thách đấu và Đại cao thủ.")
    await ctx.send(embed=embed)


@bot.command()
async def ta(ctx):
    picture_url = "https://cdn.7tv.app/emote/6200fd589454ca602315a4a3/4x.webp"  # replace with your picture URL
    await ctx.send(picture_url)


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Bot Commands", color=0x55a7f7)

    embed.add_field(name="!meta [fn]", value="fn can be left blank or 'check', 'best-items', 'traits', 'units', "
                                             "'3-star-units', 'items', 'augments', 'comps'.", inline=False)
    embed.add_field(name="!ta", value="tuh", inline=False)
    embed.add_field(name="!about", value="About the Bot", inline=False)
    embed.add_field(name="!help", value="Shows this help message.", inline=False)

    await ctx.send(embed=embed)


if __name__ == "__main__":
    bot.run(os.environ.get('DISCORD_BOT_TOKEN'))
    # guild = bot.get_guild(int(os.environ.get('DEVELOPMENT_SERVER_ID')))
    guild = bot.get_guild(int(os.environ.get('MY_SERVER_ID')))
