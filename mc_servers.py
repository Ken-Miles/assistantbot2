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

def get_priority(value):
    category_priority = {
        "admins": 0,
        "head_mods": 1,
        "mods": 2,
        "jr_mods": 3
    }
    value = value[0].lower()
    for key, priority in category_priority.items():
        if value in players_dict.get(key):
            return priority
    return 4

embmsg_2: discord.Message = None
embmsg_3: discord.Message = None

admins = ["Tryphara","Catinbetween"]
head_mods = ["theGod_17"]
mods = ["SirAlcatraz7879","ToySoldierMC","BrayBog1","Trademarc21","NightOrchid"]
jr_mods = []

players_dict = {
    "admins": admins,
    "head_mods": head_mods,
    "mods": mods,
    "jr_mods": jr_mods,
}

staff = admins + head_mods + mods + jr_mods

guilds_ = guilds + [1148154753306603581]

class MinecraftServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    # @HybridGroup(name='ip',description="Commands to get the IP of the server.")
    # async def ip(self, *args): pass

    @commands.hybrid_group(name='ip',)#description="Commands to get the IP of the server.")#,guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds_)
    async def ip_group(self, ctx: commands.Context, *args): 
        await ctx.defer()
        if ctx.guild.id != 1148154753306603581:
            await ctx.send("This command can only be used in the Radiant server.")
            return
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=4")
                for row in await cursor.fetchall():
                    await ctx.reply(f"The IP of the server is `{dict(row).get('ip')}` (last updated {dctimestamp(datetime.datetime.fromtimestamp(dict(row).get('lastupdated')),'R')})")
                    break

    @ip_group.command(name='steph',description="Shows the current IP of the steph server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(867978433077080165)
    async def getip_steph(self, interaction: commands.Context):
        if interaction.guild.id != 867978433077080165:
            await interaction.reply("This command can only be used in the Steph server.")
            return
        try:
            await interaction.defer()
            if interaction.channel.category.id != 1149197939357536286 and interaction.author.id not in me:
                await interaction.reply("This command can only be used in the StephMC channels.")
                return
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=4")
                    for row in await cursor.fetchall():
                        await interaction.reply(f"The IP of the server is `{dict(row).get('ip')}` (last updated {dctimestamp(int(dict(row).get('lastupdated')),'R')})")
                        break
        except:
            logger.error(traceback.print_exc())
    
    @ip_group.command(name='survival',description="Shows the current IP of the survival server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def getip_survival(self, interaction: commands.Context):
        try:
            await interaction.defer()
            if interaction.author.get_role(1133584084770242721) is None:
                await interaction.reply("You do not have the SnugMC role. Pick up this role in <id:customize> and answer Yes on the SnugMC question.")
                return
            if interaction.channel.category.id != 1133473132418699366 and interaction.author.id not in me:
                await interaction.reply("This command can only be used in the SnugMC channels.")
                return
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=3")
                    for row in await cursor.fetchall():
                        await interaction.reply(f"The IP of the server is `{dict(row).get('ip')}` (last updated {dctimestamp(int(dict(row).get('lastupdated')),'R')})")
                        break
        except:
            traceback.print_exc()

    @ip_group.command(name='creative',description="Shows the current IP of the creative server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def getip_creative(self, interaction: commands.Context):
        try:
            await interaction.defer()
            if interaction.author.get_role(1133584084770242721) is None:
                await interaction.reply("You do not have the SnugMC role. Pick up this role in <#1133738320560656404> or go in <id:customize> and answer Yes on the SnugMC question.")
                return
            if interaction.channel.category.id != 1133473132418699366 and interaction.author.id not in me:
                await interaction.reply("This command can only be used in the SnugMC channels.")
                return
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=1")
                    for row in await cursor.fetchall():
                        await interaction.reply(f"The IP of the server is `{dict(row).get('ip')}` (last updated {dctimestamp(datetime.datetime.fromtimestamp(dict(row).get('lastupdated')),'R')})")
                        break
        except:
            traceback.print_exc()

    @ip_group.command(name='click',description="Shows the current IP of the click server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def getip_click(self, interaction: commands.Context):
        try:
            await interaction.defer()
            if interaction.author.get_role(1135603650295767171) is None:
                await interaction.reply("You do not have the ClickMC role. Pick up this role in <#1133738320560656404> or go in <id:customize> and answer Yes on the ClickMC question.")
                return
            if interaction.channel.category.id != 1135603095385153696 and interaction.author.id not in me:
                await interaction.reply("This command can only be used in the ClickMC channels.")
                return
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=2")
                    for row in await cursor.fetchall():
                        await interaction.reply(f"The IP of the server is `{dict(row).get('ip')}` (last updated {dctimestamp(datetime.datetime.fromtimestamp(dict(row).get('lastupdated')),'R')})")
                        break
        except:
            traceback.print_exc()
    

    @commands.hybrid_group(name='setip',description="Commands to set the IP of the server.",)#guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def setip_group(self, *args): pass    

    @setip_group.command(name='steph',description="Sets the current IP of the steph server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(867978433077080165)
    async def setip_steph(self, interaction: commands.Context, ip: str=None):
        if interaction.author.id not in me:
            await interaction.reply("This command is not for you.")
            return
        await interaction.defer(ephemeral=True)
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=3")
                ran = False
                for _ in await cursor.fetchall():
                    ran = True
                    await cursor.execute("UPDATE ServerInfo SET ip=?, lastupdated=? WHERE dbid=4",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                    await interaction.reply(f"Set the IP of the server to {ip}.",ephemeral=True)
                    break
                if not ran:
                    await cursor.execute("INSERT INTO ServerInfo(datelogged, lastupdated, ip, port) VALUES (?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else "",25565))
                    await interaction.reply(f"Set the IP of the server to {ip} (first time).",ephemeral=True)

    @setip_group.command(name='survival',description="Sets the current IP of the survival server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def survival2(self, interaction: commands.Context, ip: str=None):
        if interaction.author.id not in me:
            await interaction.reply("This command is not for you.")
            return
        await interaction.defer(ephemeral=True)
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=3")
                ran = False
                for _ in await cursor.fetchall():
                    ran = True
                    await cursor.execute("UPDATE ServerInfo SET ip=?, lastupdated=? WHERE dbid=3",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                    await interaction.reply(f"Set the IP of the server to {ip}.",ephemeral=True)
                    break
                if not ran:
                    await cursor.execute("INSERT INTO ServerInfo(datelogged, lastupdated, ip, port) VALUES (?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else "",25565))
                    await interaction.reply(f"Set the IP of the server to {ip} (first time).",ephemeral=True) 

    @setip_group.command(name='creative',description="Sets the current IP of the creative server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def setip_creative(self, interaction: commands.Context, ip: str=None):
        if interaction.author.id not in me:
            await interaction.reply("This command is not for you.")
            return
        await interaction.defer(ephemeral=True)
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=1")
                ran = False
                for _ in await cursor.fetchall():
                    ran = True
                    await cursor.execute("UPDATE ServerInfo SET ip=?, lastupdated=? WHERE dbid=1",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                    await interaction.reply(f"Set the IP of the server to {ip}.",ephemeral=True)
                    break
                if not ran:
                    await cursor.execute("INSERT INTO ServerInfo(datelogged, lastupdated, ip, port) VALUES (?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else "",25565))
                    await interaction.reply(f"Set the IP of the server to {ip} (first time).",ephemeral=True)

    @setip_group.command(name='click',description="Sets the current IP of the click server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def setip_click(self, interaction: commands.Context, ip: str=None):
        if interaction.author.id not in me:
            await interaction.reply("This command is not for you.")
            return
        await interaction.defer(ephemeral=True)
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM ServerInfo WHERE dbid=2")
                ran = False
                for _ in await cursor.fetchall():
                    ran = True
                    await cursor.execute("UPDATE ServerInfo SET ip=?, lastupdated=? WHERE dbid=2",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                    await interaction.reply(f"Set the IP of the server to {ip}.",ephemeral=True)
                    break
                if not ran:
                    await cursor.execute("INSERT INTO ServerInfo(datelogged, lastupdated, ip, port) VALUES (?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else "",25565))
                    await interaction.reply(f"Set the IP of the server to {ip} (first time).",ephemeral=True)

    
    @commands.hybrid_group(name='dynmap',description="Commands to get the dynmap of the server.",)#guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def dynmap_group(self, *args): pass

    @dynmap_group.command(name='steph',description="Shows the current URL for the dynmap of the server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(867978433077080165)
    async def dynmap_steph(self, interaction: commands.Context):
        if interaction.guild.id != 867978433077080165:
            await interaction.reply("This command can only be used in the Steph server.")
            return
        try:
            await interaction.defer()
            if interaction.channel.category is not None:
                if interaction.channel.category.id != 1149197939357536286 and interaction.author.id not in me:
                    await interaction.reply("This command can only be used in the StephMC channels.")
                    return
                async with asqlite.connect('users.db') as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT * FROM Dynmap WHERE dbid=3")
                        for row in await cursor.fetchall():
                            await interaction.reply(f"The URL of the Dynmap is {hyperlinkurlorip(dict(row).get('url'))} (last updated {dctimestamp(int(dict(row).get('lastupdated')),'R')})")
                            break
        except:
            logger.error(traceback.print_exc())

    @dynmap_group.command(name='creative',description="Shows the current URL for the dynmap of the server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def dynmap_creative(self, interaction: commands.Context):
        try:
            await interaction.defer()
            if interaction.author.get_role(1133584084770242721) is None:
                await interaction.reply("You do not have the SnugMC role. Pick up this role in <#1133738320560656404> or going in <id:customize> and answer Yes on the SnugMC question.")
                return
            if interaction.channel.category.id != 1135603095385153696 and interaction.author.id not in me:
                await interaction.reply("This command can only be used in the SnugMC channels.")
                return
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM Dynmap WHERE dbid=1")
                    for row in await cursor.fetchall():
                        await interaction.reply(f"The URL of the Dynmap is {hyperlinkurlorip(dict(row).get('url'))} (last updated {dctimestamp(datetime.datetime.fromtimestamp(dict(row).get('lastupdated')),'R')})")
                        break
        except:
            traceback.print_exc()

    @dynmap_group.command(name='click',description="Shows the current URL for the dynmap of the server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def dynmap_click(self, interaction: commands.Context):
        try:
            await interaction.defer()
            if interaction.author.get_role(1135603650295767171) is None:
                await interaction.reply("You do not have the ClickMC role. Pick up this role in <#1133738320560656404> or go to <id:customize> and answer Yes on the ClickMC question.")
                return
            if interaction.channel.category.id != 1135603095385153696 and interaction.author.id not in me and interaction.author.id not in me:
                await interaction.reply("This command can only be used in the ClickMC channels.")
                return
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM Dynmap WHERE dbid=2")
                    for row in await cursor.fetchall():
                        await interaction.reply(f"The URL of the Dynmap is {hyperlinkurlorip(dict(row).get('url'))} (last updated {dctimestamp(datetime.datetime.fromtimestamp(dict(row).get('lastupdated')),'R')})")
                        break
        except:
            traceback.print_exc()

    @commands.hybrid_group(name='setdynmap',description="Commands to set the dynmap of the server.",)#guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def setdynmap_group(self, *args): pass

    @setdynmap_group.command(name='steph',description="Sets the current dynmap URL of the steph server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(867978433077080165)
    async def setdynmap_steph(self, interaction: commands.Context, ip: str=None):
        if interaction.author.id not in me:
            await interaction.reply("This command is not for you.")
            return
        await interaction.defer(ephemeral=True)
        url = hyperlinkurlorip(ip)
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM Dynmap WHERE dbid=3")
                ran = False
                for _ in await cursor.fetchall():
                    ran = True
                    await cursor.execute("UPDATE Dynmap SET url=?, lastupdated=? WHERE dbid=3",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                    await interaction.reply(f"Set the Dynmap URL of the server to {url}.",ephemeral=True)
                    break
                if not ran:
                    await cursor.execute("INSERT INTO Dynmap(datelogged, lastupdated, url) VALUES (?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else ""))
                    await interaction.reply(f"Set the Dynamp URL of the server to {url} (first time).",ephemeral=True)
        s = ""
        for role in interaction.guild.roles:
            if "snugmc" in role.name.lower():
                s += f"{role.mention} ({role.id})\n"
        
    @setdynmap_group.command(name='creative',description="Sets the current dynmap URL of the creative server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def setdynmap(self, interaction: commands.Context, ip: str=None):
        try:
            if interaction.author.id not in me:
                await interaction.reply("This command is not for you.")
                return
            await interaction.defer(ephemeral=True)
            url = hyperlinkurlorip(ip)
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM Dynmap WHERE dbid=1")
                    ran = False
                    #url = ""
                    for _ in await cursor.fetchall():
                        ran = True
                        await cursor.execute("UPDATE Dynmap SET url=?, lastupdated=? WHERE dbid=1",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                        await interaction.reply(f"Set the Dynmap URL of the server to {url}.",ephemeral=True)
                    if not ran:
                        await cursor.execute("INSERT INTO Dynmap(datelogged, lastupdated, url) VALUES (?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else ""))
                        await interaction.reply(f"Set the Dynamp URL of the server to {url}) (first time).",ephemeral=True)
        except:
            traceback.print_exc()

    @setdynmap_group.command(name='click',description="Sets the current dynmap URL of the click server.",guild_ids=[1135603095385153696,1122231942453141565])
    @app_commands.guilds(*guilds)
    async def setdynmap_click(self, interaction: commands.Context, ip: str=None):
        try:
            if interaction.author.id not in me:
                await interaction.reply("This command is not for you.")
                return
            await interaction.defer(ephemeral=True)
            url = hyperlinkurlorip(ip)
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM Dynmap WHERE dbid=2")
                    ran = False
                    for _ in await cursor.fetchall():
                        ran = True
                        await cursor.execute("UPDATE Dynmap SET url=?, lastupdated=? WHERE dbid=2",(ip if ip != None else "",int(datetime.datetime.now().timestamp())))
                        await interaction.reply(f"Set the Dynmap URL of the server to {url}.",ephemeral=True)
                    if not ran:
                        await cursor.execute("INSERT INTO Dynmap(datelogged, lastupdated, url) VALUES (?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),ip if ip != None else ""))
                        await interaction.reply(f"Set the Dynamp URL of the server to {url} (first time).",ephemeral=True)
        except:
            traceback.print_exc()
    
    ch = None
    ch2 = None

    @tasks.loop(seconds=10)
    async def infloop2(self):
        try:
            global embmsg_2, embmsg_3, ch, ch2
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


async def setup(bot):
    await bot.add_cog(MinecraftServerCog(bot))
    