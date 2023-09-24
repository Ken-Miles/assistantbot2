import discord
from discord import CategoryChannel, app_commands, channel, ui
from discord.app_commands import Group
from discord.ext import commands, tasks
import os
import asyncio
import datetime
import time
import yaml
import logging
from logging import FileHandler, handlers
import aiohttp
import asqlite
import json as Json
from threading import Thread
import traceback
import socket
import json
import mcstatus
import python_mcstatus
import re
from enum import Enum
import pkgutil
from typing import Literal, Union, Optional
from aidenlib.main import getorfetch_channel, getorfetch_user, getorfetch_guild, getorfetch_user, dchyperlink, dctimestamp, makeembed, makeembed_bot, dchyperlink, dctimestamp
from pprint import pprint

with open('client.yml', 'r') as f: token = dict(yaml.safe_load(f)).get('token')

currentdate_epoch = int(datetime.datetime.now().timestamp())
currentdate = datetime.datetime.now()

me = [458657458995462154]

sessions = []

if __name__ == "__main__":
    print(f"""Started running:
{currentdate}
{currentdate_epoch}""")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("?"),intents=intents,activity=discord.Activity(type=discord.ActivityType.watching,name='the Snugtown Discord'), status=discord.Status.do_not_disturb)
tree = bot.tree


logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a+')
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger_ = logging.getLogger("commands")
logger_.addHandler(handler)
logger_.setLevel(logging.INFO)

requests_handler = logging.FileHandler(filename='requests.log', encoding='utf-8', mode='a+')
requests_handler.setFormatter(formatter)
logger_requests = logging.getLogger("requests")
logger_requests.addHandler(requests_handler)
logger_requests.setLevel(logging.INFO)

db_handler = logging.FileHandler(filename='db.log', encoding='utf-8', mode='a+')
db_handler.setFormatter(formatter)
logger_db = logging.getLogger("db")
logger_db.addHandler(db_handler)
logger_db.setLevel(logging.INFO)

mcserver_handler = logging.FileHandler(filename='mcserver.log', encoding='utf-8', mode='a+')
mcserver_handler.setFormatter(formatter)
logger_mcserver = logging.getLogger("mcserver")
logger_mcserver.addHandler(mcserver_handler)
logger_mcserver.setLevel(logging.INFO)

logger_forums = logging.getLogger("forums")
logger_forums.setLevel(logging.INFO)
forums_handler = logging.FileHandler(filename='forums.log', encoding='utf-8', mode='a+')
forums_handler.setFormatter(formatter)
logger_forums.addHandler(forums_handler)

logger_music = logging.getLogger("music")
logger_music.setLevel(logging.INFO)
music_handler = logging.FileHandler(filename='music.log', encoding='utf-8', mode='a+')
music_handler.setFormatter(formatter)
logger_music.addHandler(music_handler)


guilds: list[int] = [1029151630215618600,1134933747800735859, 1078716884758831114]

sessions = []

emojidict: dict[str | int, str] = {
'discord': '<:discord:1080925531580682360>',
# global
"x": '<a:X_:1046808381266067547>',
'x2': "\U0000274c",
"check": '<a:check_:1046808377373769810>',
"check2": '\U00002705',
'L': "\U0001f1f1",
'l': "\U0001f1f1",
"salute": "\U0001fae1",

"calendar": "\U0001f4c6",
"notepad": "\U0001f5d2",
"alarmclock": "\U000023f0",
"timer": "\U000023f2",
True: "<:check:1046808377373769810>",
"maybe": "\U0001f937",
False: "<a:X_:1046808381266067547>",
"pong": "\U0001f3d3",

'red': "\U0001f534",
"yellow": "\U0001f7e1",
"green": "\U0001f7e2",
"blue": "\U0001f535",
'purple': "\U0001f7e3",

"headphones": "\U0001f3a7",

"hamburger": '🍔',
"building": '🏛️',
"click": '🖱️',
"newspaper": '📰',
"pick": '⛏️',
"restart": '🔄',

"skull": "\U0001f480",
"laughing": "\U0001f923",
"notfunny": "\U0001f610",

1: "\U00000031"+"\U0000fe0f"+"\U000020e3",
2: "\U00000032"+"\U0000fe0f"+"\U000020e3",
3: "\U00000033"+"\U0000fe0f"+"\U000020e3",
4: "\U00000034"+"\U0000fe0f"+"\U000020e3",
5: "\U00000035"+"\U0000fe0f"+"\U000020e3",

"stop": "\U000023f9",
"playpause": "\U000023ef",
"eject": "\U000023cf",
"play": "\U000025b6",
"pause": "\U000023f8",
"record": "\U000023fa",
"next": "\U000023ed",
"prev": "\U000023ee",
"fastforward": "\U000023e9",
"rewind": "\U000023ea",
"repeat": "\U0001f501",
"back": "\U000025c0",
"forward": "\U000025b6", # same as play
"shuffle": "\U0001f500",
}

revemojidict = {value: key for key, value in emojidict.items()}

async def createtables():
    async with asqlite.connect("users.db") as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS Users (dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, discordid INT, discorduser TEXT, displayname TEXT, mcusername TEXT, mcusername_lower TEXT, mcuuid TEXT, addedby INT, UNIQUE (dbid, discordid, mcuuid))''')
            logger_db.info("Created Users table (if exists)")
            await cursor.execute('''CREATE TABLE IF NOT EXISTS ArchivedUsers (dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, olddbid INTEGER, olddatelogged INTEGER, oldlastupdated INTEGER, discordid INT, discorduser TEXT, displayname TEXT, mcusername TEXT, mcuuid TEXT, addedby INT, UNIQUE (dbid, discordid, mcuuid, olddbid))''')
            logger_db.info("Created ArchivedUsers table (if exists)")
            await cursor.execute('''CREATE TABLE IF NOT EXISTS NewPlayers(dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, mcusername TEXT, mcuuid TEXT, UNIQUE (dbid, mcusername, mcuuid))''')
            logger_db.info("Created Players table (if exists)")
            await cursor.execute('''CREATE TABLE IF NOT EXISTS ServerInfo(dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, ip TEXT, port INTEGER, UNIQUE (dbid))''')
            logger_db.info("Created ServerInfo table (if exists)")
            await cursor.execute('''CREATE TABLE IF NOT EXISTS Dynmap(dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, url TEXT, UNIQUE (dbid))''')
            logger_db.info("Created Dynmap table (if exists)")
            await cursor.execute('''CREATE TABLE IF NOT EXISTS RestartTimes(dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, servername TEXT, time INTEGER)''')
            logger_db.info("Created RestartTimes table (if exists)")
            await cursor.execute("CREATE TABLE IF NOT EXISTS Tickets(dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, ticket_num INTEGER, tickettype INTEGER, userid INTEGER, username TEXT, chid INTEGER, chtype INTEGER, claimedby INTEGER, issolved INTEGER, transcript TEXT, UNIQUE(dbid, ticket_num))")
            logger_db.info("Created Tickets table (if exists)")
            await cursor.execute("CREATE TABLE IF NOT EXISTS TicketUsers(dbid INTEGER PRIMARY KEY AUTOINCREMENT, userid INTEGER, username TEXT, ticket_num INTEGER, UNIQUE(dbid))")
            logger_db.info("Created TicketUsers table (if exists)")

async def set_voice_status(channelorid: Union[discord.VoiceChannel, int], status: Optional[str], sessions=None):
    if isinstance(channelorid, discord.VoiceChannel): channelorid = channelorid.id
    r = await request_put(f'https://discord.com/api/v9/channels/{channelorid}/voice-status',json={"status": status}, sessions=sessions,headers=
    {"Authorization": f"Bot {token}",
    "X-Super-Properties": "eyJvcyI6IkxpbnV4IiwiYnJvd3NlciI6IkZpcmVmb3giLCJkZXZpY2UiOiIiLCJzeXN0ZW1fbG9jYWxlIjoicnUtUlUiLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoWDExOyBMaW51eCB4ODZfNjQ7IHJ2OjEwOS4wKSBHZWNrby8yMDEwMDEwMSBGaXJlZm94LzExNy4wIiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE3LjAiLCJvc192ZXJzaW9uIjoiIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjIyNzEwMiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="})
    return r


async def request_get(url: str,sessions=sessions) -> dict | None:
    #sessions: list[aiohttp.ClientSession] = [bot.session, bot.session2, bot.session3]
    #global sessions
    requestcount: int = 0
    for session in sessions:
        try:
            if requestcount == 2: logger_requests.info("session2")
            elif requestcount == 3: logger_requests.info("session3")
            try:
                r = await session.get(url)
                logger_requests.info(f"Request sent: {r.status} from {r.url}")
                if str(r.status).startswith("2"):
                    r = await r.json()
                    return r
                elif str(r.status).startswith("4"):
                    if r.status == 429:
                        await asyncio.sleep(10)
                        return await request_get(url)
                    if r.status == 404:
                        raise ValueError("404")
                else:
                    raise Exception(f"Status Code: {r.status}")
            except ValueError:
                raise ValueError
            except Exception as e:
                logger_requests.warning(traceback.format_exc())
        except:
            logger_requests.warning(traceback.format_exc())

async def request_post(url: str, json: list | dict, normal: bool=False):
    headers = {'Content-Type': 'application/json'}
    if normal:
        try:
            r = await bot.session.post(url,json=Json.dumps(json), headers=headers)
            r = await r.json()
            return r
        except Exception as e:
            print(f"session2")
            try:
                r = await bot.session2.post(url,json=Json.dumps(json), headers=headers)
                r = await r.json()
                return r
            except Exception as e:
                print(f"session3")
                try:
                    r = await bot.session3.post(url,json=Json.dumps(json), headers=headers)
                    r = await r.json()
                    return r
                except Exception as e:
                    print(f"Exception: {e}")
                    return None

sessions = []

async def request_put(url, **kwargs):
    try:
        global sessions
        if kwargs.get('sessions') != None: 
            sessions = kwargs.get('sessions')
            kwargs.pop('sessions')
        requestcount: int = 0
        for session in sessions:
            try:
                #if session == bot.session2: logger_requests.info("session2")
                #elif session == bot.session3: logger_requests.info("session3")
                try:
                    r = await session.put(url, **kwargs)
                    requestcount += 1
                    logger_requests.info(f"{'PUT':<6} | Request sent: {r.status} from {r.url}")
                    if str(r.status).startswith("2") and r.status != 204:
                        try:
                            r = await r.json()
                        except:
                            return await r.text()
                        return r
                    elif r.status == 204:
                        return r.status
                    elif str(r.status).startswith("4"):
                        if r.status == 429:
                            await asyncio.sleep(10)
                            return await request_put(url, **kwargs)
                        if r.status == 404:
                            raise ValueError("404")
                    else:
                        raise Exception(f"Status Code: {r.status}")
                except ValueError:
                    raise ValueError
                except Exception as e:
                    logger_requests.warning(traceback.format_exc())
            except:
                logger_requests.warning(traceback.format_exc())
    except:
        logger_.warning(traceback.format_exc())

def hyperlinkurlorip(iporurl: str):
    # Regular expression pattern for IPv4 addresses
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'

    # Regular expression pattern for IPv6 addresses
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'

    # Check if the input matches either IPv4 or IPv6 pattern
    if not (re.match(ipv4_pattern, iporurl) or re.match(ipv6_pattern, iporurl)):# or iporurl.startswith("http"):
        if iporurl.startswith("http://") or iporurl.startswith("https://"):
            return dchyperlink(iporurl,'this','See the dynmap!')
        return f"`{iporurl}`"

# @tree.command(name='allemojis',guilds=[discord.Object(x) for x in [1134933747800735859]])
# async def allemojis(interaction: discord.Interaction):
#     try:
#         await interaction.response.defer(thinking=True,ephemeral=True)
#         emojis: list[discord.Emoji] = await interaction.guild.fetch_emojis()
#         emoji_string = ""
#         for emoji in emojis:
#             emoji_string += f'''"{emoji.name}": `{emoji}`,\n'''
#         await interaction.followup.send(emoji_string)
#     except Exception as e:
#         traceback.print_exc()

# @bot.hybrid_command(name='resettimer',description="Shows the approximate time to the reset.")
# async def time_to_reset(ctx: commands.Context):
#     await ctx.message.reply("")

new_town_ideas = 1130364285491626055
town_jobs = 1130366266247491654
suggestions = 1130644472657608755
auction_house = 1132321569427947730
shops = 1137651359978623066
mc_suggestions = 1133889335637311578
snugmc_suggestions = 1133889335637311578
clickmc_suggestions = 1135604021424566292
solvable = [new_town_ideas, town_jobs, auction_house, mc_suggestions, shops]


restarttime: dict[str, int] = {}

restart_group = Group(name="restarttime",description="Commands that state the restart time for a server.",guild_ids=[1135603095385153696,1122231942453141565])

@restart_group.command(name="click",description="Gets the time until the click server restarts.")
async def restarttime_click(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM RestartTime WHERE servername=?",("click",))
            for row in await cursor.fetchall():
                await interaction.response.send_message(f"The server restarts {dctimestamp(dict(row).get('time'),'R')} ({dctimestamp(dict(row).get('time'),'f')}).")
                return

@bot.hybrid_command(name='uptime',description="Shows how long the bot has been online.")
async def uptime(ctx: commands.Context):
    await ctx.defer(ephemeral=True)
    await ctx.reply(f"The bot started {dctimestamp(currentdate,'R')} ({dctimestamp(currentdate,'f')}).",delete_after=5.0 if ctx.interaction is None else None)


@bot.hybrid_command(name="ping",description="See what the bot's ping is.",) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def ping(ctx: commands.Context):
    msg: Optional[discord.Message] = None
    a: float = datetime.datetime.now().timestamp()
    if ctx.interaction is None: await ctx.message.add_reaction(str(emojidict.get('pong')))
    else: msg = await ctx.reply("Testing ping...")
    b: float = datetime.datetime.now().timestamp()
    if msg: await msg.edit(content=f"{emojidict.get('pong')} Pong! Latency is `{str(bot.latency*1000)}`ms (edit time `{round(b-a,14)}`).")
    else: await ctx.reply(f"{emojidict.get('pong')} Pong! Latency is `{str(bot.latency*1000)}`ms (edit time `{round(b-a,14)}`).")
    logger_.info(f"Latency is {str(bot.latency*1000)}ms (edit time {round(b-a,20)}).")

async def showunlinked():
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:

            users = []
            users2 = []
            async for user in (bot.get_guild(1122231942453141565)).fetch_members(limit=100):
                if not user.bot:
                    users.append(user.id)
            returnv = ""
            await cursor.execute("SELECT * FROM Users")
            for row in await cursor.fetchall():
                users2.append(int(dict(row).get('discordid')))
            
            #if bot.user.id in users: users.remove(bot.user.id)
            if bot.user.id in users2: users2.remove(bot.user.id)

            for user in users:
                if user not in users2:
                    returnv += f"<@{user}>\n"
            
            return returnv

async def populaterestarttimes():
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM RestartTimes")
            for row in await cursor.fetchall():
                try:
                    restarttime[dict(row).get('servername')] = dict(row).get('time')
                    logger_db.info(f"Populated restart time for {dict(row).get('servername')}.")
                    if int(restarttime.get(dict(row).get('time'))) < int(datetime.datetime.now().timestamp()):
                        time = int(restarttime.get(dict(row).get('time')))
                        while time < int(datetime.datetime.now().timestamp()): time += 21_600
                        await cursor.execute("UPDATE RestartTimes SET lastupdated=?, time=? WHERE servername=?",(int(datetime.datetime.now().timestamp()),time,dict(row).get('servername')))
                        logger_db.info(f"Updated restart time for {dict(row).get('servername')} to {time}.")
                except:
                    logger_db.warning(f"Could not populate restart time for {dict(row).get('servername')}.")
            
            #await cursor.execute("INSERT INTO RestartTimes (datelogged, lastupdated, servername, time) VALUES (?,?,?,?)",(int(datetime.datetime.now().timestamp()),int(datetime.datetime.now().timestamp()),"click",1679969675))
       
            
@bot.event
async def on_ready():
    global me
    date = datetime.datetime.now()
    print(f"{date}: Ready!")
    if bot.owner_ids:  me = [x for x in bot.owner_ids]
    elif bot.owner_id: me = [bot.owner_id]
    #await tree.sync()
    #bot.add_view()
    #await tree.sync(guild=discord.Object(1134933747800735859))
    #g = bot.get_guild(1122231942453141565)
    #print(g.get_channel(1132321569427947730).available_tags)
    #print(g.get_channel(1130366266247491654).available_tags)

reaction_roles: dict[str | None, tuple[int, str]] = {
    emojidict.get("hamburger"): (1133584084770242721, "SnugMC"),
    emojidict.get("building"): (1124072236328947842, "Litematica"),
    emojidict.get("click"): (1135603650295767171, "ClickMC"),
    emojidict.get("newspaper"): (1130599557638672485, "Update Pings"),
    emojidict.get("pick"): (1133738592867471371, "Minecraft Pings"),
    #emojidict.get("")
}

# @bot.event
# async def on_raw_reaction_add(reaction: discord.RawReactionActionEvent):
#     if reaction.channel_id == 1133738320560656404 and reaction.message_id == 1133738592867471371:
#         global reaction_roles
#         townofsnug = bot.get_guild(1122231942453141565)

#         for emoji, role in reaction_roles.items():
#             if emoji == reaction.emoji.name and reaction.member.get_role(role[0]) is None:
#                 await reaction.member.add_roles(townofsnug.get_role(role[0]),reason=f"{reaction.member}: Reaction role for {role[1]}.")
#                 break

# @bot.event
# async def on_raw_reaction_remove(reaction: discord.RawReactionActionEvent):
#     if reaction.channel_id == 1133738320560656404 and reaction.message_id == 1133738592867471371:
#         global reaction_roles
#         townofsnug = bot.get_guild(1122231942453141565)

#         for emoji, role in reaction_roles.items():
#             if emoji == reaction.emoji.name and reaction.member.get_role(role[0]) is not None:
#                 await reaction.member.remove_roles(townofsnug.get_role(role[0]),reason=f"{reaction.member}: Reaction role for {role[1]}.")
#                 break


gamertag_msg = None
msgcount = 0



@bot.event
async def on_message(message: discord.Message):
    global gamertag_msg, msgcount
    
    if message.author == bot.user: return

    gamertags = 1124152862411341894
    if message.channel.id == gamertags:
        msgcount += 1
        if msgcount >= 5:
            msgcount = 0
            if gamertag_msg is None:
                async for msg in (bot.get_channel(gamertags)).history(limit=7):
                    if msg.author == bot.user and len(msg.embeds) > 1:
                        gamertag_msg = msg
                        break
            if gamertag_msg != None:
                await gamertag_msg.delete()

            gamertag_msg = await message.channel.send(embeds=[makeembed_bot(title="Gamertags",description=f"If you haven't already, post your gamertag (your Minecraft Username) in this channel __in it's own message__. You will be linked to the bot by the owner so others can know what your minecraft username is. You can see other's profiles via </profile:1131265945571176560> once your MC and discord account is linked."),
                                                          makeembed_bot(title="Unlinked Users",description=await showunlinked(),footer="Made by @aidenpearce3066 | Last Updated",timestamp=datetime.datetime.now(),color=discord.Colour.darker_grey())])

    if message.content.lower().strip().startswith("/link"):
        click = 1143394656068059238
        surv = 1143319379925278813
        creat = 1143396237748486146

        msg = f'''Hi! I don't think you did the command correctly.\n'''

        if message.channel.category.id == 1135603095385153696 and message.author.get_role(1135603681904037969) is None: # clickmc, clickMC verified role
            msg += f''' Use the </link:{click}> command (click it) if you are trying to get on the __ClickMC__ server.'''
        elif message.channel.category.id == 1122231942453141565: # snugmc
            if "survival" in message.channel.name and message.author.get_role(1133484031254736987) is None:
                msg += f''' Use the </link:{surv}> command (click it) if you are trying to get on the __Survival__ server.'''
            elif message.author.get_role(1133484031254736987) is None:
                msg += f''' Use the </link:{creat}> command (click it) if you are trying to get on the __Creative__ server.'''
            else:
                 msg += f""" Use the </link:{click}> command (click it) if you are trying to get on the __ClickMC__ server.
Use the </link:{surv}> command (click it) if you are trying to get on the __Survival__ server.
Use the </link:{creat}> command (click it) if you are trying to get on the __Creative__ server."""
        else:
            msg += f""" Use the </link:{click}> command (click it) if you are trying to get on the __ClickMC__ server.
Use the </link:{surv}> command (click it) if you are trying to get on the __Survival__ server.
Use the </link:{creat}> command (click it) if you are trying to get on the __Creative__ server."""

        if msg != "":
            await message.reply(msg)

    await bot.process_commands(message)

async def send_annoucement(message: discord.Message | dict):
    wb: discord.Webhook = discord.Webhook.from_url("https://discord.com/api/webhooks/1133114267374194858/8k8PSkqiZv0bmZqyFQZj_7DOaQak5HXLAJJHWaTGTDm-uKgqIMtFgX8z1IHtnJJqlvj4")
    if type(message) == dict:
        message = discord.Message(state=bot._connection, channel=bot.get_channel(1133114267374194858), data=message)
    await wb.send(content=message.content,username=message.author.display_name,avatar_url=message.author.avatar_url)

click_guild = None
click_mc_chat = None
click_mc_annoucements = None

async def send_joinleave():
    wb: discord.Webhook = discord.Webhook.from_url("https://discord.com/api/webhooks/1133115809854656593/DzCrXTvp6OZJOtk4TgXcPq_0BThsEbaUGKoLrpkM8My4E8yXJEJQs_fRinDlJV-5qzet")
    if type(message) == dict:
        message = discord.Message(state=bot._connection, channel=click_mc_chat, data=message)#await wb.send(content=)
    await wb.send(content=message.content,username=message.author.display_name,avatar_url=message.author.avatar_url)

async def set_click_guild(data: dict):
    global click_guild
    click_guild = discord.Guild(state=bot._connection, data=data)
async def set_mc_chat(data: dict):
    global click_mc_chat
    click_mc_chat = discord.TextChannel(state=bot._connection, guild=click_guild, data=data)
async def set_mc_annoucements(data: dict):
    global click_mc_annoucements
    click_mc_annoucements = discord.TextChannel(state=bot._connection, guild=click_guild, data=data)

# virus's stuff


def read(sock, n):
    A = b''
    while len(A) < n:
        A += sock.recv(n - len(A))
    return A


def read_varint(sock, remaining=0):
    A = 0
    for B in range(5):
        C = ord(sock.recv(1))
        A |= (C & 127) << 7 * B
        if not C & 128:
            return remaining - (B + 1), A


def read_header(sock, compression=False):
    B = sock
    C, A = read_varint(B)
    if compression:
        A, C = read_varint(B, A)
    A, D = read_varint(B, A)
    return A, D

def get_status(addr, port=25565):
    start_time = time.perf_counter()
    sock = socket.create_connection((addr, port), 0.7)
    end_time = time.perf_counter()
    ping = round((end_time - start_time) * 1000, 2)
    sock.send(b"\x06\x00\x00\x00\x00\x00\x01")
    sock.send(b"\x01\x00")
    length, _ = read_header(sock)
    length, _ = read_varint(sock, length)
    data = json.loads(read(sock, length))
    data['ping'] = ping
    return data


@tree.context_menu(name='View Profile')
async def profile_cm(interaction: discord.Interaction, user: discord.Member):
    try:
        #await (bot.get_cog("mc_linking")).profile(interaction,user)
        await unlink(interaction,user)
    except:
        traceback.print_exc()


@tree.context_menu(name='MC Username')
async def link_menu(interaction: discord.Interaction, msg: discord.Message):
    try:
        #await (bot.get_cog("mc_linking")).link(interaction,msg.author, msg.content)
        await link(interaction,msg.author, msg.content)
    except:
        traceback.print_exc()


@tree.context_menu(name='Unlink MC Username')
async def unlink_menu(interaction: discord.Interaction, user: discord.Member):
    try:
        #await (bot.get_cog("mc_linking")).unlink(interaction, user)
        await unlink(interaction,user)
    except:
        traceback.print_exc()

# @tree.context_menu(name="Create Help Thread")
# async def create_help_thread(interaction: discord.Interaction, message: discord.Message):
#     HELP_CHANNEL =  1150849190293950544
#     try:
#         if interaction.guild is None: 
#             await interaction.response.send_message("You can't create a help thread in a DM!",ephemeral=True)
#             return
#         await interaction.response.defer(thinking=True)
#         help_ch = interaction.guild.get_channel(HELP_CHANNEL)
#         if isinstance(help_ch, discord.CategoryChannel) or help_ch is None: return
#         wbs = await help_ch.webhooks()
#         wb = None
#         for wb_ in wbs:
#             if wb_.name.lower() == "helper":
#                 wb = wb_
#                 break
#             if len(wbs) == 1:
#                 wb = wb_
#         if wb is None:
#             wb = await help_ch.create_webhook(name="Helper")
#         if not isinstance(help_ch,discord.ForumChannel): return
#         th = await help_ch.create_thread(reason=f"Help thread for {message.author} (ran by {interaction.user})",
#         name=message.content if len(message.content) <= 100 else f"Help thread for {message.author}",content=f"{message.jump_url}\n{message.content}")
#         if not isinstance(th[0], discord.Thread): return
#         await th[1].delete()
#         await th[0].add_user(message.author)
#         await wb.send(content=f"{message.jump_url}\n{message.content}",username=message.author.display_name,avatar_url=message.author.avatar.url,thread=th[0])
#         #await th[0].purge(limit=1,check=lambda x: x.is_system())
#         await interaction.followup.send(f"Created help thread for {message.author}!",ephemeral=True)
#     except:
#         traceback.print_exc()
#         logger_.warning(traceback.format_exc())


@tree.context_menu(name='Purge to here')
#@commands.has_permissions(manage_messages=True)
#@commands.guild_only()
async def purge_to_here(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    try:
        msgs = await interaction.channel.purge(limit=100,after=message.created_at)
        try:
            await message.delete()
            msgs.append(message)
        except: pass
        await interaction.followup.send(f"Purged {len(msgs)} message{'s' if len(msgs) != 1 else ''}.",ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to do that.",ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}",ephemeral=True)


@bot.command("invite",description="invite the bot to your server",hidden=True)
@commands.is_owner()
async def invite(ctx: commands.Context):
    if await bot.is_owner(ctx.author):
        await ctx.reply(discord.utils.oauth_url(bot.user.id,permissions=ctx.guild.me.guild_permissions),ephemeral=True)

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
ch = None
ch2 = None

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

mcserverinfo = None
@tasks.loop(seconds=10)
async def infloop2():
    try:
        global embmsg_2, embmsg_3, ch, ch2
        a = datetime.datetime.now()
        for serverip in ["TheClick.mcserver.us","132.145.29.252"]:
            try:
                if ch is None:
                    ch = await (await bot.fetch_guild(1122231942453141565)).fetch_channel(1133245103306186865)
                if ch2 is None:
                    ch2 = await (await bot.fetch_guild(1029151630215618600)).fetch_channel(1153205238992490526)
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

                if e.players.sample is not None:
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
                embs = [makeembed(title="Server Info",description=desc,color=color if color is not discord.utils.MISSING else discord.Colour.blurple(),timestamp=datetime.datetime.now()),emb2]
                embs[0].set_footer(text="Made by @aidenpearce3066 | Last updated")
                if embmsg_2 is None and serverip == "TheClick.mcserver.us":
                    async for msg in ch.history(limit=5):
                        if msg.author == bot.user: 
                            embmsg_2 = msg
                            await embmsg_2.edit(embeds=embs)
                    if embmsg_2 is None:
                        embmsg_2 = await ch.send(embeds=embs)
                elif serverip == "TheClick.mcserver.us":
                    await embmsg_2.edit(embeds=embs)
                if embmsg_3 is None and serverip == "132.145.29.252":
                    async for msg in ch2.history(limit=5):
                        if msg.author == bot.user: 
                            embmsg_3 = msg
                            await embmsg_3.edit(embeds=embs)
                    if embmsg_3 is None:
                        embmsg_3 = await ch2.send(embeds=embs)
                elif serverip == "132.145.29.252":
                    await embmsg_2.edit(embeds=embs)
                b = datetime.datetime.now()
                logger_mcserver.info(f"Updated server info in {b.timestamp()-a.timestamp()} seconds.")
            except Exception as e:
                raise e
    except:
        logger.error(f"Error in infloop2: {traceback.format_exc()}")

class MinecraftType(Enum):
        bedrock = False
        java = True


async def link(interaction: commands.Context | discord.Interaction, user: discord.User, mcusername: str, mctype: MinecraftType=MinecraftType.java):
    ctx: bool = type(interaction) == commands.Context
    if type(ctx) == commands.Context: interaction.user = interaction.author
    if interaction.user.id not in me:
        await interaction.response.send_message("This command is not for you.")
        return
    
    if ctx: 
        await interaction.defer()
    else: await interaction.response.defer(thinking=True)
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM Users WHERE discordid=?",(user.id))
            ran = False
            for row in await cursor.fetchall():
                ran = True
                break
            if ran:
                if ctx:       
                    await interaction.reply("This user has already linked their MC username to their discord account.",ephemeral=True)
                    return
                else: 
                    await interaction.followup.send("This user has already linked their MC username to their discord account.",ephemeral=True)
                    return
            if not ran:
                tr = 0
                r = None
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
                    else:        await interaction.followup.send(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.",ephemeral=True)
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

# class Scanner:
#     def __init__(self, db):
#         self.db = db
#         self.data = self.read()

#     def read(self):
#         return self.db.execute("SELECT * FROM ip")

#     @staticmethod
#     async def get_data(ip_id, ip, port=25565):
#         print(f'\nGetting data of {ip_id} ({ip}:{port})', end='')
#         r = ''
#         try:
#             r = get_status(ip, port)
#         except TimeoutError:
#             print("    Offline", end='')
#             r = 'Offline'
#         except ConnectionResetError:
#             print("    Connection reset")
#             r = 'Connection reset'
#         except ConnectionRefusedError:
#             print("    Connection refused")
#             r = 'Connection refused'
#         except TypeError:
#             print("    Type error")
#             r = 'Type error'
#         return r

#     def update_country(self, ip_id, ip):
#         try:
#             country = requests.get(f"https://geolocation-db.com/json/{ip}&position=true").json()['country_name']
#             self.db.execute(f"UPDATE ip SET country = '{country}' WHERE nr = {str(ip_id)}")
#         except simplejson.errors.JSONDecodeError:
#             country = 'Unknown'
#         return f'Country: {country}'

#     def update_players(self, ip_id, ip, data, advanced):
#         try:
#             online_players = data['players']['online']
#         except KeyError:
#             online_players = 0
#         self.db.execute(f'UPDATE ip SET "onlinePlayers" = {online_players} WHERE nr = {str(ip_id)}')
#         try:
#             max_online_players = data['players']['max']
#         except KeyError:
#             max_online_players = 20
#         self.db.execute(f'UPDATE ip SET "maxPlayers" = {max_online_players} WHERE nr = {str(ip_id)}')
#         if advanced:
#             try:
#                 if 'sample' in data['players']:
#                     players = data['players']['sample']
#                     if self.db.getType() == 'sqlite':
#                         self.db.execute(f"UPDATE ip SET players = '{str(players)}' WHERE nr = {str(ip_id)}")
#                     elif self.db.getType() == 'postgres':
#                         self.db.execute("UPDATE ip SET players = %s WHERE nr = %s", (str(players), str(ip_id)))
#                     return f'({online_players}/{max_online_players}) Players: {[name["name"] for name in players]}'
#                 else:
#                     self.db.execute(f"UPDATE ip SET players = '{[]}' WHERE nr = {str(ip_id)}")
#                     return f'({online_players}/{max_online_players}) \nPlayer names could not be retrieved'
#             except sqlite3.OperationalError:
#                 return f'({online_players}/{max_online_players}) \nPlayer names could not be retrieved'
#         else:
#             return f'({online_players}/{max_online_players})'

#     def update_version(self, ip_id, ip, data):
#         try:
#             version = data['version']['name']
#             self.db.execute(f"UPDATE ip SET version = '{version}' WHERE nr = {str(ip_id)};")
#             return f'Version: {version}'
#         except KeyError:
#             print(data)
#         except TypeError:
#             print(data)

#     def update_motd(self, ip_id, ip, data):
#         try:
#             motd = data['description']['text']
#             if motd == '':
#                 motd = data['description']['extra'][0]['text']
#         except:
#             try:
#                 motd = motd = data['description']['extra'][0]['text']
#             except:
#                 try:
#                     motd = data['description']
#                 except:
#                     motd = 'Non db compatible motd'

#         motd = remove_non_ascii(motd).replace("@", "").replace('"', "").replace("'", "")
#         self.db.execute(f"UPDATE ip SET motd = '{motd}' WHERE nr = {str(ip_id)}")
#         return f'Motd: {motd}'

#     def update_ping(self, ip_id, data):
#         ping = data['ping']
#         self.db.execute(f"UPDATE ip SET ping = CAST('{str(ping)}' AS float) WHERE nr = {str(ip_id)}")
#         return f'Ping: {ping}'

#     def update_last_online(self, ip_id):
#         time_now = time.strftime("%d %b %Y %H:%M:%S")
#         self.db.execute(f"UPDATE ip SET last_online = '{time_now}' WHERE nr = {str(ip_id)}")

#     #def update_rcon(self, ip_id, ip):
#     #    rcon = check_rcon(ip, 25575)
#     #    self.db.execute(f"UPDATE ip SET rcon = '{rcon}' WHERE nr = {str(ip_id)}")
#     #    return f'Rcon: {rcon}'

#     def update_type(self, ip_id, ip, data):
#         return f'Type scan not implemented'

#     def update_plugin(self, ip_id, ip, data):
#         return f'Plugin scan not implemented'

#     def update_timeline(self, ip_id, data):
#         time_now = time.strftime("%d %b %H:%M:%S")
#         timeline = eval(self.db.execute(f'SELECT timeline FROM ip WHERE nr = {str(ip_id)}')[0][0])
#         # timeline[time_now] = json.dumps(data)
#         if self.db.getType() == 'sqlite':
#             timeline_id = self.db.execute('INSERT INTO timeline (timestamp, data) VALUES (?, ?) RETURNING id;',
#                                           (str(time_now), str(json.dumps(data))))
#             timeline.append(timeline_id[0][0])
#             self.db.execute(f"UPDATE ip SET timeline = ? WHERE nr = ?", (str(timeline), str(ip_id)))
#         elif self.db.getType() == 'postgres':
#             timeline_id = self.db.execute('INSERT INTO timeline (timestamp, data) VALUES (%s, %s) RETURNING id;',
#                                           (str(time_now), str(json.dumps(data))))
#             try:
#                 timeline.append(timeline_id[0][0])
#             except AttributeError:
#                 timeline = [timeline_id[0][0]]
#             self.db.execute(f"UPDATE ip SET timeline = %s WHERE nr = %s", (str(timeline), str(ip_id)))

#     def join_server(self, ip_id, ip, port):
#         requests.get(f'http://localhost:25567/connect?ip={ip}&port={port}')
#         time.sleep(1)
#         while "net.minecraft.class_412" in requests.get(f'http://localhost:25567/getScreen').text:
#             time.sleep(.3)
#         time.sleep(3)
#         r = requests.get(f'http://localhost:25567/getDisconnectReason')
#         if r.text != 'Not on a DisconnectedScreen':
#             if 'white' in r.text or 'White' in r.text:
#                 self.db.execute(f"UPDATE ip SET whitelist = 'true' WHERE nr = {str(ip_id)}")
#                 requests.get(f'http://localhost:25567/disconnect')
#                 return f'Whitelist active'
#         r = requests.get(f'http://localhost:25567/getScreen')
#         if r.status_code == 404:
#             self.db.execute(f"UPDATE ip SET whitelist = 'false' WHERE nr = {str(ip_id)}")
#             requests.get(f'http://localhost:25567/disconnect')
#             return f'No whitelist'
#         requests.get(f'http://localhost:25567/disconnect')

#     def update_shodon(self, ip_id, ip):
#         result = requests.get(f'https://internetdb.shodan.io/{ip}')
#         if result.status_code == 200:
#             self.db.execute(f"UPDATE ip SET shodon = '{result.text}' WHERE nr = {str(ip_id)}")
#             return f'Shodon: {result.text}'

#     async def update_db(self, ip_id, ip, port, data, advanced, join, version, shodon):
#         self.update_timeline(ip_id, data)

#         if data != 'Offline' and data != 'Connection reset' and data != 'Connection refused' and data != 'Type error':
#             print(f'Updating {ip_id} ({ip}:{port}) ')
#             print(self.update_version(ip_id, ip, data))
#             print(self.update_motd(ip_id, ip, data))
#             print(self.update_players(ip_id, ip, data, advanced))
#             print(self.update_ping(ip_id, data))
#             self.update_last_online(ip_id)
#             if advanced:
#                 print(self.update_type(ip_id, ip, data))
#                 print(self.update_country(ip_id, ip))
#                 print(self.update_plugin(ip_id, ip, data))
#                 print(self.update_rcon(ip_id, ip))
#             if join:
#                 v = self.db.execute(f'SELECT version FROM ip WHERE nr = {str(ip_id)}')[0][0]
#                 if version in v:
#                     print(f'Joining {ip_id} ({ip}:{port})')
#                     print(self.join_server(ip_id, ip, port))
#             if shodon:
#                 print(self.update_shodon(ip_id, ip))
#         else:
#             print(f'{ip_id} ({ip}:{port}) is Offline')

#         print('\n----------\n')
#         return ''

#     async def update(self, batch_size=100, advanced=False, join=False, version="1.19.4", shodon=False,
#                      async_batches=True):
#         ip_data = self.read()
#         batches = [ip_data[i:i + batch_size] for i in range(0, len(ip_data), batch_size)]
#         results = []
#         for batch in batches:
#             request_tasks = []
#             db_tasks = []
#             for ip_data in batch:
#                 ip_id = ip_data[0]
#                 ip = ip_data[1]
#                 port = int(ip_data[2])

#                 if async_batches:
#                     task = asyncio.ensure_future(self.get_data(ip_id, ip, port))
#                     request_tasks.append(task)
#                 else:
#                     data = await self.get_data(ip_id, ip, port)
#                     results.append(data)

#             if async_batches:
#                 results = await asyncio.gather(*request_tasks)

#             for ip_data in batch:
#                 ip_id = ip_data[0]
#                 ip = ip_data[1]
#                 port = int(ip_data[2])
#                 data = results[batch.index(ip_data)]

#                 if async_batches:
#                     task = asyncio.ensure_future(self.update_db(ip_id, ip, port, data, advanced, join, version, shodon))
#                     db_tasks.append(task)
#                 else:
#                     await self.update_db(ip_id, ip, port, data, advanced, join, version, shodon)

#             if async_batches:
#                 await asyncio.gather(*db_tasks)

#     async def single_update(self, ip_id, advanced=True, join=False, version="1.19.4", shodon=True):
#         ip_data = self.db.execute(f"SELECT * FROM ip WHERE nr = {str(ip_id)} LIMIT 1")[0]
#         if ip_data:
#             ip = ip_data[1]
#             port = int(ip_data[2])

#             try:
#                 data = await self.get_data(ip_id, ip, port)
#                 await self.update_db(ip_id, ip, port, data, advanced, join, version, shodon)
#             except TimeoutError:
#                 print(f'{ip_id} ({ip}:{port}) is Offline')
#             except ConnectionResetError:
#                 print(f'{ip_id} ({ip}:{port}) connection reset')
#             except ConnectionRefusedError:
#                 print(f'{ip_id} ({ip}:{port}) connection refused')
#             except TypeError:
#                 print(f'{ip_id} ({ip}:{port}) type error')
#         else:
#             print(f'Server with ID {ip_id} not found in the database.')

#     def run(self, batch_size=100, advanced=False, join=False, version="1.19.4", shodan=False, max_workers=1000000,
#             async_batches=True):
#         executor = ThreadPoolExecutor(max_workers=max_workers)

#         loop = asyncio.get_event_loop()
#         loop.set_default_executor(executor)
#         loop.run_until_complete(
#             self.update(batch_size=batch_size, advanced=advanced, join=join, version=version, shodon=shodan,
#                         async_batches=async_batches))
#         executor.shutdown(wait=True)

# old reaction add code

# if reaction.emoji.name == emojidict.get('hamburger'):
#     if reaction.member.get_role(snugmc) is None:
#         await reaction.member.add_roles(townofsnug.get_role(snugmc),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for SnugMC.")
#     elif reaction.member.get_role(snugmc) is not None:
#         await reaction.member.remove_roles(townofsnug.get_role(snugmc),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for SnugMC.")
# elif reaction.emoji.name == emojidict.get('building'):
#     if reaction.member.get_role(litematica) is None:
#         await reaction.member.add_roles(townofsnug.get_role(litematica),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for Litematica.")
#     elif reaction.member.get_role(litematica) is not None:
#         await reaction.member.remove_roles(townofsnug.get_role(litematica),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for Litematica.")
# elif reaction.emoji.name == emojidict.get('click'):
#     if reaction.member.get_role(clickmc) is None:
#         await reaction.member.add_roles(townofsnug.get_role(clickmc),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for ClickMC.")
#     elif reaction.member.get_role(clickmc) is not None:
#         await reaction.member.remove_roles(townofsnug.get_role(clickmc),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for ClickMC.")
# elif reaction.emoji.name == emojidict.get('newspaper'): 
#     if reaction.member.get_role(updateping) is None:
#         await reaction.member.add_roles(townofsnug.get_role(updateping),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for Update Ping.")
#     elif reaction.member.get_role(updateping) is not None:
#         await reaction.member.remove_roles(townofsnug.get_role(updateping),reason=f"{townofsnug.get_member(reaction.user_id)}: Reaction role for Update Ping.")

async def main():
    async with aiohttp.ClientSession() as session:
        async with aiohttp.ClientSession() as session2:
            async with aiohttp.ClientSession() as session3:
                global sessions
                bot.session = session
                bot.session2 = session2
                bot.session3 = session3
                bot.sessions = sessions
                await createtables()
                await populaterestarttimes()
                #voteloop.start()
                infloop2.start()
                discord.utils.setup_logging(handler=handler)
                #for m in pkgutil.iter_modules(path=["./"]):
                #    if not m.name.startswith("_") and m.name != "main": await bot.load_extension(m.name)
                for file in os.listdir('./'):
                    if not file.startswith('_') and not file == "main.py" and file.endswith('.py'):
                        try:
                            await bot.load_extension(f'{file[:-3]}')
                        except Exception as e:
                            print(f'Failed to load extension {file[:-3]}.')
                            logger_.warning(traceback.format_exc())
                sessions = [session,session2,session3]
                await bot.load_extension('jishaku')
                #await bot.load_extension('aidenlib.cogs.helper_cog')
                await bot.start(token)
                #await tree.sync()

if __name__ == '__main__': asyncio.run(main())
