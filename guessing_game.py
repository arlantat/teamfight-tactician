import discord
import logging
from discord.ext import commands
import random

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix="$")
flag = False
number = -1
guesses_left = 20
rules = "I will think of a secret number from 1 to 1000000. Your mission is to guess it in 20 tries! Simple enough?\n"

@bot.command()
async def start(ctx):
    global flag, number
    flag = True
    number = random.randint(1, 10**6)
    await ctx.reply(f'{rules}Please type `$guess [number]` to start guessing!')

@bot.command()
async def guess(ctx, i=None):
    if i:
        i = int(i)
    global flag, guesses_left
    if not flag:
        await ctx.reply('There is no session')
    else:
        if guesses_left == 0:
            flag = False
            await ctx.reply(f"You LOST, it's {number}")
        if not i:
            await ctx.reply('You should provide at least a number')
        else:
            if i == number:
                flag = False
                await ctx.reply('You WIN')
            elif i < number:
                guesses_left -= 1
                await ctx.reply(f'{i} is SMALLER than my secret number')
            else:
                guesses_left -= 1
                await ctx.reply(f'{i} is BIGGER than my secret number')


bot.run('token')