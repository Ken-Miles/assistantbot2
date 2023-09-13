import discord
from discord import app_commands
from discord.ext import commands
from main import me, emojidict, guilds, logger_, logger_db, dctimestamp, request_get, logger, sessions
import datetime
import traceback
import os
import asqlite
from enum import Enum
from aidenlib.main import makeembed_bot, makeembed


allplayers = []
async def lastonline_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        if interaction.user.id not in me:
            return []
        if len(allplayers) == 0:
            async with asqlite.connect('users.db') as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM Players")
                    for row in await cursor.fetchall():
                        allplayers.append(dict(row).get('mcusername'))
    
        returnv = []
        returnv2 = []
        current = current.lower().strip()
        for name in allplayers:
            name_ = name.lower().strip()
            if name_.startswith(current):
                returnv.append(app_commands.Choice(name=name,value=name))
            elif name_ in current:
                returnv2.append(app_commands.Choice(name=name,value=name))
        returnv.extend(returnv2)
        return returnv
    except:
        logger_.error(traceback.format_exc())

playerlist = []
async def lastonline_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if len(playerlist) == 0:
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM Players")
                for row in await cursor.fetchall():
                    playerlist.append(dict(row).get('mcusername'))
    
    exact_matches = []
    other_matches = []
    non_matches = []

    current = current.lower().strip()

    for player in playerlist:
        player_ = player
        player = player.lower().strip()
        if player.startswith(current):
            exact_matches.append(app_commands.Choice(name=player_, value=player_))
        elif current in player:
            other_matches.append(app_commands.Choice(name=player_, value=player_))
        else:
            non_matches.append(app_commands.Choice(name=player_, value=player_))
        if len(exact_matches) + len(other_matches) >= 25:
            break
    
    exact_matches.extend(other_matches)
    exact_matches.extend(non_matches)

    return list(exact_matches)

class MinecraftType(Enum):
        bedrock = False
        java = True

class MinecraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot    

    async def profile(self, interaction: commands.Context, user: discord.User=None, mcusername: str=None):
        if type(interaction) == commands.Context: interaction.user = interaction.author
        if user == None and mcusername is None: user = interaction.user
        await interaction.defer()
        async with asqlite.connect('users.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM Users WHERE discordid=?",(interaction.user.id))
                ran = False
                for row in await cursor.fetchall():
                    ran = True
                    break
                if not ran:
                    await interaction.followup.send("You need to have your Minecraft and Discord account linked. Go to <#1124152862411341894> and put your minecraft username in a message.",ephemeral=True)
                    return
                if user:
                    await cursor.execute(f"SELECT * FROM Users WHERE discordid=?",(user.id,))
                elif mcusername:
                    await cursor.execute(f"SELECT * FROM Users WHERE mcusername=?",(mcusername,))
                ran = False
                data = None
                for row in await cursor.fetchall():
                    row = dict(row)
                    ran = True
                    data = row
                    break
                if not ran:
                    if user == self.bot.user:
                        await interaction.reply("bro i aint got a minecraft account dumbass")
                    else:
                        await interaction.reply("This user has not linked their MC username to their discord account yet.",ephemeral=True)
                    return
                else:
                    returnv: str = f"""<@{data.get('discordid')}> has linked their MC username to their discord account:
    **Discord**: {data.get('discordid')}
    **Discord ID:** `{data.get('discordid')}`
    **Discord Username:** `{data.get('discorduser')}`
    **Display Name:** `{data.get('displayname')}`
    **Minecraft Username:** `{data.get('mcusername')}`
    **Minecraft UUID:** `{data.get('mcuuid')}`

    Added by <@{data.get('addedby')}>
    Logged at {dctimestamp(data.get('datelogged'),"F")}, Last Updated {dctimestamp(data.get('lastupdated'),"R")}"""
                    await interaction.reply(embed=makeembed_bot(f"Requested by @{interaction.user}",thumbnail=f"https://crafatar.com/avatars/{data.get('mcuuid')}",description=returnv),ephemeral=True)

    @commands.hybrid_command(name='profile',description="Shows somebody's linked Minecraft profile.")
    @app_commands.autocomplete(mc_username=lastonline_autocomplete)
    @app_commands.guilds(*guilds)
    async def profile_cmd(self, interaction: commands.Context, user: discord.User=None, mc_username: str=None):
        try:
            await self.profile(interaction,user,mc_username)
        except:
            logger_.error(traceback.format_exc())

    # @commands.command(name='profile',description="Shows somebody's profile.")
    # async def profile_cmd2(ctx: commands.Context, user: discord.User=None):
    #     try:
    #         await profile(ctx,user)
    #     except:
    #         logger_.error(traceback.format_exc())
    
    @commands.hybrid_command(name='link',description="Links your MC username to your discord account.")
    @app_commands.guilds(*guilds)
    async def link_cmd(self, interaction: commands.Context, user: discord.User, mcusername: str):
        try:
            await link(interaction, user, mcusername)
        except:
            logger_.error(traceback.format_exc())

    @commands.hybrid_command(name='unlink',description="Unlinks your MC username from your discord account.")
    @app_commands.guilds(*guilds)
    async def unlink_cmd(self, interaction: commands.Context, user: discord.User):
        try:
            await unlink(interaction, user)
        except:
            logger_.error(traceback.format_exc())

    @commands.hybrid_command(name='lastonline',description="Looks up when a user was last on the Click server.")
    @app_commands.autocomplete(mcusername=lastonline_autocomplete)
    @app_commands.guilds(*guilds)
    async def lastonline(self, ctx: commands.Context, mcusername: str):
        await ctx.defer()

        data = None
        if mcusername in allplayers:
            data = await lookup_user(mcusername)
        
        if data is None:
            await ctx.reply("This user has not been on the Click server. (1.20)")
            return
        desc = f"""Username: `{data.get('mcusername')}`\nUUID: `{data.get('mcuuid')}`\n\nLast Online: {dctimestamp(data.get('lastupdated'),"R")} ({dctimestamp(data.get('lastupdated'),"F")})
    First Seen: {dctimestamp(data.get('datelogged'),"R")} ({dctimestamp(data.get('datelogged'),"F")})"""
        emb = makeembed_bot(f"Requested by {ctx.author}",description=desc,thumbnail=f"https://crafatar.com/avatars/{data.get('mcuuid')}",author=f"Information on {data.get('mcusername')}",author_url=f"https://namemc.com/profile/{data.get('mcuuid')}")

        await ctx.reply(embed=emb)

async def link(interaction: commands.Context | discord.Interaction, user: discord.User, mcusername: str, mctype: MinecraftType=MinecraftType.java):
    ctx: bool = type(interaction) == commands.Context
    if ctx == commands.Context: interaction.user = interaction.author
    if interaction.author.id not in me: 
        await interaction.response.send_message("This command is not for you.")
        return
    if ctx: await interaction.defer()
    else: await interaction.response.defer(thinking=True)
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM Users WHERE discordid=?",(user.id))
            ran = False
            for row in await cursor.fetchall():
                ran = True
                break
            if ran:
                if ctx:       await interaction.reply("This user has already linked their MC username to their discord account.",ephemeral=True)
                else: await interaction.followup.send("This user has already linked their MC username to their discord account.",ephemeral=True)
                r = None
                if mctype == MinecraftType.java:
                    while True:
                        try:
                            tr += 1
                            r = await request_get(f"https://api.mojang.com/users/profiles/minecraft/{mcusername.strip()}")
                            break 
                        except ValueError:
                            if tr >= 5:
                                if ctx:       await interaction.reply(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.")
                                else: await interaction.followup.send(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.")
                                return
                            continue
                    return
            if not ran:
                tr = 0
                while True:
                    try:
                        tr += 1
                        r = await request_get(f"https://api.mojang.com/users/profiles/minecraft/{mcusername.strip()}")
                        break 
                    except ValueError:
                        if tr >= 5:
                            if ctx:      await interaction.reply(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.")
                            else:await interaction.followup.send(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.")
                            return
                        continue
                if r is None:
                    if ctx:      await interaction.reply(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.")
                    else:        await interaction.followup.send("An error occured. Please try again.",ephemeral=True)
                    logger.error(f"Error getting MC UUID for {mcusername}: {traceback.format_exc()}")
                    return
                await cursor.execute("INSERT INTO Users (datelogged, lastupdated, discordid, discorduser, displayname, mcusername, mcuuid, addedby) VALUES (?,?,?,?,?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),user.id,user.name,user.display_name,r.get('name'),r.get('id'),interaction.user.id))
                emb = makeembed(title='Entered information into database',timestamp=datetime.datetime.now(),description=f"Successfully linked the MC username `{r.get('name')}` to <@{user.id}>'s discord account.",color=discord.Colour.green(),thumbnail=f"https://crafatar.com/avatars/{r.get('id')}",)
                if ctx: await interaction.reply(embed=emb)
                else: await interaction.followup.send(embed=emb)
                if interaction.guild.get_member(user.id) != None and type(user) == discord.Member:
                    await interaction.guild.get_member(user.id).edit(nick=r.get('name'))

   
async def unlink(interaction: discord.Interaction | commands.Context, user: discord.Member=None):
    ctx = type(interaction) == commands.Context
    if ctx: interaction.user = interaction.author
    if user == None: user = interaction.user
    if interaction.user.id not in me: 
        if ctx: await interaction.reply("This command is not for you.")
        else: await interaction.response.send_message("This command is not for you.")
        return
    if ctx: await interaction.defer()
    else: await interaction.response.defer(thinking=True)
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM Users WHERE discordid=?",(user.id,))
            ran = False
            for row in await cursor.fetchall():
                row = dict(row)
                ran = True
                await cursor.execute("INSERT INTO ArchivedUsers (datelogged, lastupdated, olddbid, olddatelogged, oldlastupdated, discordid, discorduser, displayname, mcusername, mcuuid, addedby) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),row.get('dbid'),row.get('datelogged'),row.get('lastupdated'),row.get('discordid'),row.get('discorduser'),row.get('displayname'),row.get('mcusername'),row.get('mcuuid'),row.get('addedby')))
                logger_db.info(f"Archived user {row.get('dbid')}")
                await cursor.execute("DELETE FROM Users WHERE dbid=?",(row.get('dbid'),))
                logger_db.info(f"Deleted user {row.get('dbid')}")

            if not ran:
                if ctx: await interaction.reply("This user has not linked their MC username to their discord account yet.",ephemeral=True)
                else: await interaction.followup.send("This user has not linked their MC username to their discord account yet.",ephemeral=True)
                return
            
            if ran:
                emb = makeembed(title='Removed information from database',timestamp=datetime.datetime.now(),description=f"Successfully unlinked the MC username `{row.get('mcusername')}` from <@{user.id}>'s discord account.",color=discord.Colour.green(),thumbnail=f"https://crafatar.com/avatars/{row.get('mcuuid')}",)
                if ctx: await interaction.reply(embed=emb)
                else: await interaction.followup.send(embed=emb)

async def lookup_user(mcusername: str):
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM Users WHERE mcusername=?",(mcusername,))
            data = None
            for row in await cursor.fetchall():
                data = dict(row)
                break
            return data

async def setup(bot):
    await bot.add_cog(MinecraftCog(bot))