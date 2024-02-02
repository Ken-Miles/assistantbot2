from __future__ import annotations

from typing import Optional

import datetime
import logging
import traceback

import discord
from discord.ext import commands, tasks

from utils import CogU, ContextU, emojidict, makeembed_bot, formatter

memes_handler = logging.FileHandler(filename='memes.log', encoding='utf-8', mode='a+')
memes_handler.setFormatter(formatter)
logger_memes = logging.getLogger("memes")
logger_memes.addHandler(memes_handler)
logger_memes.setLevel(logging.INFO)

LUNENBURG = 867978433077080165
SNUG_BLOG = 922912081529954374
SNUG_MEMES = 1162813785346686976

REGULAR_MEMES = 867990633791508490
MC_SERVER_INFO = 1149198803258322984

class MemeCog(CogU, name="Memes"):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def getmeme(self) -> discord.Embed:
        try: 
            r = await self._get("https://meme-api.com/gimme")
            if r is None: return
        except: return
        data = r
        return makeembed_bot(title=data['title'], author=f"posted by u/{data['author']} in r/{data['subreddit']}", author_url=f"https://reddit.com/user/{data['author']}", url=data['postLink'], image=data['url'])

    @tasks.loop(seconds=60)
    async def checkmemes(self):
        try:
            if datetime.datetime.now().hour in [12,18,22] and datetime.datetime.now().minute == 0:
                channel = await self.bot.getorfetch_channel(SNUG_MEMES, await self.bot.getorfetch_guild(LUNENBURG,self.bot)) # type: ignore
                #await channel.send("funny meme time")
                logger_memes.info("[auto] funny meme time")
                m = await channel.send(embed=await self.getmeme())
                logger_memes.info("[auto] meme posted")
                await m.add_reaction(emojidict.get('laughing'))
                await m.add_reaction(emojidict.get('notfunny'))
                await m.add_reaction(emojidict.get('skull'))
        except:
            logger_memes.error(traceback.format_exc())
    
    @commands.command(name='postmeme')
    @commands.is_owner()
    async def postmeme(self, ctx: ContextU, *, url: Optional[str]=None):
        try:
            if url is None:
                await ctx.send(embed=await self.getmeme())
                logger_memes.info(f"[manual] meme posted by {ctx.author}")
            else:
                await ctx.send(embed=makeembed_bot(image=url))
                logger_memes.info(f"[manual] meme posted by {ctx.author}")
        except:
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author == self.bot.user:
            return
        
        if msg.guild is None:
            return
        
        if msg.guild.id == LUNENBURG:
            if msg.channel.id == SNUG_MEMES:
                if not self.bot.is_owner(msg.author):
                    ch = msg.channel
                    author = msg.author
                    await msg.delete()
                    await ch.send(f"Hey {author.mention}: You can't post messages/memes here. Please post memes elsewhere, such as in <#{REGULAR_MEMES}>.",delete_after=10)
                    logger_memes.info(f"[auto] deleted message from {author} in {ch}")
                    return
            elif msg.channel.id == MC_SERVER_INFO:
                if not self.bot.is_owner(msg.author):
                    author = msg.author
                    ch = msg.channel
                    await msg.delete()
                    await ch.send(f"Hey {author.mention}: You can't post messages here. This is to keep this chat clear for easy visibility of the server information. If you wish to make an annoucement here, contact Snug.",delete_after=15)
                    logger_memes.info(f"[auto] deleted message from {author} in {ch}")
                    return

async def setup(bot):
    c = MemeCog(bot)
    await bot.add_cog(c)
    c.checkmemes.start()