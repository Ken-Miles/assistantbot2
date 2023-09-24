import logging
from logging import Logger
import aiohttp
import discord
from discord import DMChannel, app_commands, Interaction, Embed, ui
from discord.ext import commands, tasks
from collections import deque
from discord.ext import commands
from aidenlib.main import getorfetch_channel, getorfetch_guild, getorfetch_user, makeembed, makeembed_bot
import datetime
import main
from main import formatter, emojidict
import traceback

memes_handler = logging.FileHandler(filename='memes.log', encoding='utf-8', mode='a+')
memes_handler.setFormatter(formatter)
logger_memes = logging.getLogger("memes")
logger_memes.addHandler(memes_handler)
logger_memes.setLevel(logging.INFO)

LUNENBURG = 867978433077080165
SNUG_BLOG = 922912081529954374


def is_me():
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.client, commands.Bot):
            return await interaction.client.is_owner(interaction.user)
        return False
    return app_commands.check(predicate)

class MemeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def getmeme(self) -> discord.Embed:
        try: 
            r = await main.request_get("https://meme-api.com/gimme",sessions=[aiohttp.ClientSession()])
            if r is None: return
        except: return
        data = r
        return makeembed_bot(title=data['title'], author=f"posted by u/{data['author']} in r/{data['subreddit']}", author_url=f"https://reddit.com/user/{data['author']}", url=data['postLink'], image=data['url'])

    @tasks.loop(seconds=60)
    async def checkmemes(self):
        if datetime.datetime.now().hour in [12,18,22] and datetime.datetime.now().minute == 0:
            channel = await getorfetch_channel(SNUG_BLOG, await getorfetch_guild(LUNENBURG)) # type: ignore
            #await channel.send("funny meme time")
            logger_memes.info("[auto] funny meme time")
            m = await channel.send(embed=await self.getmeme())
            logger_memes.info("[auto] meme posted")
            await m.add_reaction(emojidict.get('laughing'))
            await m.add_reaction(emojidict.get('notfunny'))
            await m.add_reaction(emojidict.get('skull'))
    
    @commands.command(name='postmeme')
    @is_me()
    async def postmeme(self, ctx: commands.Context, *, url: str=None):
        try:
            if url is None:
                await ctx.send(embed=await self.getmeme())
                logger_memes.info(f"[manual] meme posted by {ctx.author}")
            else:
                await ctx.send(embed=makeembed_bot(image=url))
                logger_memes.info(f"[manual] meme posted by {ctx.author}")
        except:
            traceback.print_exc()


async def setup(bot):
    c = MemeCog(bot)
    await bot.add_cog(c)
    c.checkmemes.start()