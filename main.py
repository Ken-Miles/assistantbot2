from __future__ import annotations

import asyncio
import datetime
import logging
import time

import aiohttp
import discord
from discord.ext import commands
import yaml

from cogs import EXTENSIONS
from utils import BotU, MentionableTree, formatter, Help

with open('client.yml', 'r') as f: 
    config = dict(yaml.safe_load(f))
    TOKEN = config.get('token')
    DISCORD_CLIENT_ID = config.get('client_id')
    DISCORD_CLIENT_SECRET = config.get('client_secret')
    DISCORD_REDIRECT_URI = "https://scr.aidenpearce.space/discord/oauth"

currentdate_epoch = int(time.time())
currentdate = datetime.datetime.fromtimestamp(currentdate_epoch)

if __name__ == "__main__": 
    print(f"""Started running:
{currentdate}
{currentdate_epoch}""")

intents = discord.Intents.all()
bot = BotU(command_prefix=commands.when_mentioned_or('?'),
tree_cls = MentionableTree, intents=intents,activity=discord.Activity(type=discord.ActivityType.playing,name='with the API'), 
status = discord.Status.online, help_command=Help())
tree = bot.tree

logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger_ = logging.getLogger("commands")
logger_.addHandler(handler)
logger_.setLevel(logging.INFO)

discord_auth_logger = logging.getLogger("discord_authorization")
discord_auth_logger.setLevel(logging.INFO)
discord_auth_handler = logging.FileHandler(filename='discord_authorization.log', encoding='utf-8', mode='w')
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
discord_auth_handler.setFormatter(formatter)
discord_auth_logger.addHandler(discord_auth_handler)

@bot.event
async def on_ready():
    date = datetime.datetime.fromtimestamp(int(time.time()))
    print(f"{date}: Ready!")

async def main():
    async with aiohttp.ClientSession() as session:
        async with aiohttp.ClientSession() as session2:
            async with aiohttp.ClientSession() as session3:
                bot.session = session
                bot.session2 = session2
                bot.session3 = session3
                discord.utils.setup_logging(handler=handler)
                for file in EXTENSIONS:
                    if not file.startswith('_') and not file == "main":
                        try:
                            await bot.load_extension(file)
                        except Exception as e:
                            print(f"Failed to load extension {file}: {e}")
                await bot.load_extension("jishaku")
                await bot.start(TOKEN)

if __name__ == '__main__': asyncio.run(main())
