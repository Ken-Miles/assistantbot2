from re import U
import discord
from discord import app_commands
from discord.app_commands import Group
from discord.ext import commands, tasks
from discord.ext.commands import HybridGroup
from main import me, emojidict, logger, logger_mcserver, hyperlinkurlorip, getorfetch_channel, getorfetch_guild, guilds
from aidenlib.main import makeembed_bot, makeembed, dctimestamp
import datetime
import traceback
import os
import asqlite
from enum import Enum
import mcstatus
import python_mcstatus
import asyncio
import tortoise
from tortoise import Model, Tortoise, fields
from tortoise.exceptions import IntegrityError

class Base(Model):
    dbid = fields.BigIntField(pk=True,unique=True,generated=True)
    datelogged = fields.DatetimeField(auto_now_add=True)
    lastupdated = fields.DatetimeField(auto_now=True)

class Playerlog(Base):
    lastseen = fields.DatetimeField()
    serverip = fields.TextField(null=False)
    mcusername = fields.CharField(max_length=16)
    mcuuid = fields.UUIDField(unique=False,null=True) # multiple players can be on multiple servers
    
    class Meta:
        table = "Playerlogs"

class UniquePlayer(Base):
    mcusername = fields.TextField(max_length=16)
    mcuuid = fields.UUIDField(unique=True,null=True)
    mcuuid_clean = fields.TextField(max_length=36,unique=True,null=True)

    class Meta:
        table = "Players"

class Server(Base):
    serverip = fields.TextField(null=False)
    serverport = fields.IntField(null=False,default=25565)
    serverversion = fields.TextField(null=True)
    serverprotocol = fields.IntField(null=True)

    class Meta:
        table = "Servers"

class ServerSubscription(Base):
    userid = fields.BigIntField(null=False)
    guildid = fields.BigIntField(null=False)
    channelid = fields.BigIntField(null=False)
    messageid = fields.BigIntField(null=False)
    serverip = fields.TextField(null=False)
    serverport = fields.IntField(null=False,default=25565)
    servername = fields.TextField(null=True)


class MinecraftChecker(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot
    
    @tasks.loop(seconds=10)
    async def infloop2(self):
        try:
            a = datetime.datetime.now()
            for serverip in ["TheClick.mcserver.us","132.145.29.252"]:
                try:
                    if self.ch is None: 
                        self.ch = await (await self.bot.fetch_guild(1135603095385153696)).fetch_channel(1133245103306186865)
                    if self.ch2 is None:
                        self.ch2 = await (await self.bot.fetch_guild(1029151630215618600)).fetch_channel(1153205238992490526)
                    server = mcstatus.JavaServer(serverip)
                    #query = await server.async_query()

                    stats = await server.async_status()
                    color: discord.Colour = discord.utils.MISSING
                    emoji = None
                    emoji_msg = ""
                    if serverip == "TheClick.mcserver.us":
                        if stats.players.online > 30:
                            color = discord.Colour.blue() 
                            emoji = emojidict.get('blue')
                            emoji_msg = "The server is over capacity!"
                        elif stats.players.online == 30: 
                            color = discord.Colour.red()
                            emoji = emojidict.get('red')
                            emoji_msg = "The server is full!"
                        elif stats.players.online >= 28: 
                            color = discord.Colour.yellow()
                            emoji = emojidict.get('yellow')
                            emoji_msg = "The server is almost full!"
                        else: 
                            color = discord.Colour.green()
                            emoji = emojidict.get('green')
                            emoji_msg = "The server is open!"

                    desc = f'''Server Info:
                `{server.address.host} | Port {server.address.port}`
                `{stats.raw.get('description').get('text')}`
                Version: `{stats.version.name}`, Protocol `{stats.version.protocol}`
                Latency: `{round(stats.latency,8)}`ms
                Enforces Secure Chat: {emojidict.get(bool(stats.raw.get('version').get('enforcesSecureChat')))}
                Players: {stats.players.online}/{stats.players.max}{' '+emoji+' ' if emoji else ""}{emoji_msg if emoji_msg else ''}\n'''
                    emb2 = makeembed(title="Information",description="The information presented may not be completely up to date or completely accurate. Keep this in mind when viewing the above stats.",color=discord.Colour.red())
                    players = []
                    e = mcstatus.JavaServer.lookup(serverip).status()

                    for player in e.players.sample:
                        players.append((player.name, player.uuid))
                    
                    requestlist = []
                    for _ in range(1,16):
                        for __ in python_mcstatus.statusJava(serverip).players.list: 
                            requestlist.append((__.name_raw, __.uuid))
                        await asyncio.sleep(.1)
                    requestlist.sort(key=lambda x: x[0])
                    requestlist = list(set(requestlist))
                    for player in requestlist:
                        players.append(player)
                    players = list(set(players))
                    #print(len(players))
                    #print(len(e.players.sample))
                    #players.sort(key=lambda x: (get_priority(x)))
                    players.sort(key=lambda x: x[0].lower())
                    if serverip == "TheClick.mcserver.us":
                        async with asqlite.connect('users.db') as conn:
                            async with conn.cursor() as cursor:
                                for player in players:
                                    if player[0] in jr_mods:
                                        player = (f"[Jr Mod] {player[0]}", player[1])
                                    elif player[0] in mods:
                                        player = (f"[Mod] {player[0]}", player[1])
                                    elif player[0] in head_mods:
                                        player = (f"[Head Mod] {player[0]}", player[1])
                                    elif player[0] in admins:
                                        player = (f"[Admin] {player[0]}", player[1])
                                    desc += f"\n`{player[0]}`"
                                    await cursor.execute("SELECT * FROM Players WHERE mcuuid=?",(player[1],))
                                    ran = False
                                    for _ in await cursor.fetchall():
                                        await cursor.execute("UPDATE Players SET lastupdated=? WHERE mcuuid=?",(int(datetime.datetime.now().timestamp()),player[1]))
                                        break
                                    if not ran:
                                        await cursor.execute("INSERT INTO Players (datelogged, lastupdated, mcusername, mcuuid) VALUES (?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),player[0],player[1]))

                        with open("players.json","a+") as f:
                            f.write(f'''{int(datetime.datetime.now().timestamp())}: {stats.players.online},\n''')
                    #print(players)
                    embs = [makeembed(title="Server Info",description=desc,color=discord.Colour.blurple(),timestamp=datetime.datetime.now()),emb2]
                    embs[0].set_footer(text="Made by @aidenpearce3066 | Last updated")
                    if embmsg_2 is None:
                        async for msg in self.ch.history(limit=5):
                            if msg.author == self.bot.user: 
                                embmsg_2 = msg
                                await embmsg_2.edit(embeds=embs)
                        if embmsg_2 is None:
                            embmsg_2 = await self.ch.send(embeds=embs)
                    elif serverip == "TheClick.mcserver.us":
                        await embmsg_2.edit(embeds=embs)
                    if embmsg_3 is None:
                        async for msg in self.ch2.history(limit=5):
                            if msg.author == self.bot.user: 
                                embmsg_3 = msg
                                await embmsg_3.edit(embeds=embs)
                        if embmsg_3 is None:
                            embmsg_3 = await self.ch2.send(embeds=embs)
                    elif serverip == "132.145.29.252":
                        await embmsg_2.edit(embeds=embs)
                    b = datetime.datetime.now()
                    logger_mcserver.info(f"Updated server info in {b.timestamp()-a.timestamp()} seconds.")
                except Exception as e:
                    raise e
        except:
            logger.error(f"Error in infloop2: {traceback.format_exc()}")
    
    @tasks.loop(seconds=10)
    async def update_server_info():
       servers = await ServerSubscription.all()
       # list of 
       for server in servers:
            players = []
            server_1 = await mcstatus.JavaServer.async_lookup(server.get('serverip'),timeout=3)
            stats_1 = await server_1.async_status()
            if server_1.players.online <= 0: pass

            server_2 = python_mcstatus.statusJava(server.get('serverip'))

            desc = f'''Server Info:
`{server_1.address.host} | Port {server_1.address.port}`
`{dict(stats_1.raw).get('description').get('text')}`
Version: `{stats_1.version.name}`, Protocol `{stats_1.version.protocol}`
Latency: `{round(stats_1.latency,8)}`ms
Enforces Secure Chat: {emojidict.get(bool(stats_1.raw.get('version').get('enforcesSecureChat')))}
Players: {stats_1.players.online}/{stats_1.players.max}\n'''
            emb2 = makeembed(title="Information",description="The information presented may not be completely up to date or completely accurate. Keep this in mind when viewing the above stats.",color=discord.Colour.red())
            players = []

            if stats_1.players.sample is not None:
                for s in stats_1.players.sample:
                    players.append((s.name, s.uuid, s.id))

            server_2 = python_mcstatus.statusJava(server.get('serverip'))
            if server_2.players is not None:
                for s in server_2.players.list: players.append((s.name_raw, s.uuid, None))
            
            players = sorted(list(set(players)),key=lambda x: x[0].lower())

            for player in players:
                try:
                    await UniquePlayer.create(mcusername=player[0],mcuuid=player[1],mcuuid_clean=player[2] if player[2] is not None else player[1].replace('-',''))
                except IntegrityError: pass
                try:
                    await Playerlog.create(servername=server.get('address'),serverip=server_1.address,mcusername=player[0],mcuuid=player[1])
                except IntegrityError: 
                    await (await Playerlog.filter(serverip=server_1.address,mcusername=player[0]))[0].update_from_dict(dict()lastseen=datetime.datetime.now(datetime.timezone.utc))


            

                


        
        # servers = [(ip,port)]


