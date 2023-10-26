from typing import Optional
import discord
from discord import app_commands
from discord.app_commands import Group
from discord.ext import commands, tasks
from discord.ext.commands import HybridGroup
from main import me, emojidict, logger, hyperlinkurlorip, guilds
import datetime
import traceback
import os
from enum import Enum
import tortoise
from tortoise import fields, Tortoise
from tortoise.models import Model
import mcstatus
import python_mcstatus
from aidenlib import makeembed_bot, makeembed
import asyncio


SNUGTOWN = 1122231942453141565
APATB = 1029151630215618600
APATB2 = 1078716884758831114
APATB3 = 1087156493746458674
APATB4 = 1134933747800735859
SBT = 1144078911039344640

testguilds = [APATB, APATB2, APATB3, APATB4, SBT]
myguilds = [SNUGTOWN]
guilds = testguilds + myguilds

class Base(Model):
    dbid = fields.IntField(pk=True)
    datelogged = fields.DatetimeField(auto_now_add=True)
    lastupdated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class CustomServer(Base):
    guildid = fields.BigIntField()
    serverip = fields.TextField()
    serverport = fields.IntField(null=True)
    name = fields.TextField()
    online = fields.BooleanField(default=False)
    numplayers = fields.IntField(null=True)
    lastonline = fields.DatetimeField(null=True)

class Snugtown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name='server',description='Server only commands for the bot owner.',
        hidden=True, fallback='info',guild_ids=guilds)
    @commands.is_owner()
    async def server(self, ctx: commands.Context, server: str):
        pass

    @server.command(name='status',description="See the server's current status.")
    @commands.is_owner()
    async def server_status(self, ctx: commands.Context, servernameorip: str):
        await ctx.defer()
        if (ip := (await CustomServer.get(servernameorip)).serverip) is not None:
            servernameorip = ip
        embs = await self.get_server_status(servernameorip)
        await ctx.reply(embeds=embs)
    
    @server.command(name='add',description="Add a server to the database.")
    @commands.is_owner()
    @commands.guild_only()
    async def server_add(self, ctx: commands.Context, server_name: str, serverip: str, serverport: Optional[int]=None):
        await ctx.defer()
        if await CustomServer.filter(servername=server_name).exists():
            await ctx.reply("A server with that name already exists.",ephemeral=True)
            return
        if await CustomServer.filter(serverip=serverip).exists():
            sname = await CustomServer.get(servername=server_name)
            await ctx.reply(f"A server with that IP already exists ({sname}).",ephemeral=True)
            return
        if serverport is None and serverip.find(':') != -1:
            serverport = int(serverip.split(':')[1])
            serverip = serverip.split(':')[0]
        await CustomServer.create(guildid=ctx.guild.id, serverip=serverip, serverport=serverport, name=server_name)
        await ctx.reply(f"Added server `{server_name}` with IP `{serverip}` and port `{serverport}`.",ephemeral=True)        


    async def get_server_status(self, serverip: str) -> list[discord.Embed]:
        if serverip is None:
            return [makeembed_bot(title="Error",description="Please provide a server IP or name.",color=discord.Colour.red())]
        try:
            server = mcstatus.JavaServer(serverip)
            stats = await server.async_status()
        except:
            stats = None
        color: discord.Colour = discord.utils.MISSING
        emoji = None
        emoji_msg = ""
        if stats is None:
            color = discord.Colour.brand_red()
            emoji = emojidict.get('x'),
            emoji_msg = "The server is offline!"
        elif stats.players.online > stats.players.max:
            color = discord.Colour.blue() 
            emoji = emojidict.get('blue')
            emoji_msg = "The server is over capacity!"
        elif stats.players.online == stats.players.max: 
            color = discord.Colour.dark_red()
            emoji = emojidict.get('red')
            emoji_msg = "The server is full!"
        elif stats.players.online >= stats.players.max*.8:
            color = discord.Colour.yellow()
            emoji = emojidict.get('yellow')
            emoji_msg = "The server is almost full!"
        elif stats.players.online > 0:
            color = discord.Colour.green()
            emoji = emojidict.get('green')
            emoji_msg = "The server is open!"
        elif stats.players.online >= 0:
            color = discord.Colour.greyple()
            emoji = emojidict.get('gray')
            emoji_msg = "The server is empty!"

        desc = f'''Server Info:
    `{server.address.host}` | Port `{server.address.port}`\n'''
        if stats is not None:
            desc += f'''Server Info:
    `{stats.raw.get('description').get('text')}`
    Version: `{stats.version.name}`, Protocol `{stats.version.protocol}`
    Latency: `{round(stats.latency,8)}`ms
    Enforces Secure Chat: {emojidict.get(bool(stats.raw.get('version').get('enforcesSecureChat')))}
    Players: {stats.players.online}/{stats.players.max}{' '+emoji+' ' if emoji else ""}{emoji_msg if emoji_msg else ''}\n'''
        else:
            desc += f'''The server is offline.'''
        emb2 = makeembed(title="Information",
        description="The information presented may not be completely up to date or completely accurate. Keep this in mind when viewing the above stats.",
        color=discord.Colour.red())
        
        
        players = []

        try:
            e = await (await mcstatus.JavaServer.async_lookup(serverip)).async_status()
            if e.players.sample is not None:
                for player in e.players.sample:
                    players.append((player.name, player.uuid))
            requestlist = []
            for _ in range(1,16):
                for __ in python_mcstatus.statusJava(serverip).players.list: 
                    requestlist.append((__.name_raw, __.uuid))
                await asyncio.sleep(.1)
            requestlist = list(set(sorted(requestlist, key=lambda x: x[0]))) # sort and remove dupes
            for player in requestlist:
                players.append(player)
            players = list(set(players))
        except:
            pass
        #print(len(players))
        #print(len(e.players.sample))
        #players.sort(key=lambda x: (get_priority(x)))
        players.sort(key=lambda x: x[0].lower())
        embs = [makeembed_bot(title="Server Info",description=desc,color=color if color is not discord.utils.MISSING else discord.Colour.blurple()),emb2]
        embs[0].set_footer(text="Made by @aidenpearce3066 | Last updated")
        return embs

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        kwargs = {
            'ephemeral': True,
            'delete_after': (10.0 if not ctx.interaction else None)
        }
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.NotOwner):
            return await ctx.reply(f"You aren't my father (well owner).",**kwargs)
        else:
            return await ctx.reply(f"{error}",**kwargs)