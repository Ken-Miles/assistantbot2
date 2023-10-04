import discord
from discord import app_commands, ui, Member
from discord.app_commands import Group
from discord.ext import commands, tasks
from yaml import Token
from main import me, logger_, guilds
from aidenlib.main import makeembed_bot, makeembed, getorfetch_channel, getorfetch_user, getorfetch_guild, dctimestamp, getorfetch_member
from enum import Enum
import asqlite
import datetime
import asyncio
import traceback
import logging
import os
from typing import List, Optional, Tuple, Union, Dict, Literal
import tortoise
from tortoise import Tortoise, fields
from tortoise.models import Model
import pytz
import io

dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
ticket_handler = logging.FileHandler(filename='tickets.log',encoding='utf-8', mode='a')
ticket_handler.setFormatter(formatter)

ticket_open_logger = logging.getLogger("open")
ticket_open_logger.addHandler(ticket_handler)
ticket_open_logger.setLevel(logging.INFO)

ticket_close_logger = logging.getLogger("close")
ticket_close_logger.addHandler(ticket_handler)
ticket_close_logger.setLevel(logging.INFO)

ticket_claim_logger = logging.getLogger("claim")
ticket_claim_logger.addHandler(ticket_handler)
ticket_claim_logger.setLevel(logging.INFO)

ticket_unclaim_logger = logging.getLogger("claim")
ticket_unclaim_logger.addHandler(ticket_handler)
ticket_unclaim_logger.setLevel(logging.INFO)

ticket_transcribe_logger = logging.getLogger("transcribe")
ticket_transcribe_logger.addHandler(ticket_handler)
ticket_transcribe_logger.setLevel(logging.INFO)

ticket_reopen_logger = logging.getLogger("reopen")
ticket_reopen_logger.addHandler(ticket_handler)
ticket_reopen_logger.setLevel(logging.INFO)

SNUGTOWN = 1122231942453141565


async def getorfetch_member(userid: int, guild: discord.Guild) -> Optional[Member]:
    """Gets a member from a guild, if not found, fetches it"""
    member = guild.get_member(userid)
    if member is None:
        member = await guild.fetch_member(userid)
    return member

class Base(Model):
    dbid = fields.IntField(pk=True,generated=True,unique=True)
    datelogged = fields.DatetimeField(auto_now_add=True)
    lastupdated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class Ticket(Base):
    ticket_num = fields.BigIntField(unique=True)
    tickettype = fields.BigIntField()
    guildid = fields.BigIntField()
    chid = fields.BigIntField()
    chtype = fields.BigIntField()
    userid = fields.BigIntField()
    username = fields.TextField()
    claimedby = fields.BigIntField(null=True)
    issolved = fields.BooleanField(default=False)
    transcript = fields.TextField(null=True)

    class Meta:
        table = "Tickets"

class TicketUsers(Base):
    ticket_num = fields.BigIntField()
    guildid = fields.BigIntField()
    userid = fields.BigIntField()
    username = fields.TextField()

    class Meta:
        table = "TicketUsers"

class TicketGuilds(Base):
    guildid = fields.BigIntField()
    ticket_category = fields.BigIntField()
    archived_tickets_category = fields.BigIntField()

    class Meta:
        table = "TicketGuilds"

class TicketType(Base):
    guildid = fields.BigIntField()
    tickettype = fields.IntField()
    name = fields.TextField()
    color = fields.TextField(default=1)
    emoji = fields.TextField(null=True)

    class Meta:
        table = "TicketType"

class GuildSettings(Base):
    guildid = fields.BigIntField(unique=True)
    owner_id = fields.BigIntField()
    ticket_category = fields.BigIntField()
    archived_tickets_category = fields.BigIntField(null=True)
    usingtextchannels = fields.BooleanField(default=False)
    modrole = fields.BigIntField()
    adminrole = fields.BigIntField()
    messageid = fields.BigIntField(null=True)

    class Meta:
        table = "GuildSettings"


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #ticket_group = HybridGroup(name="ticket",description="Ticket Commands",guild_ids=[1135603095385153696,1122231942453141565])

    @commands.hybrid_group(name='ticket',description="Ticket commands")
    @app_commands.guilds(*guilds)
    async def ticket_group(self, interaction: commands.Context): pass
    
    @ticket_group.command(name="close",description="Closes a ticket")
    @commands.guild_only()
    async def ticket_close(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer()
        ticket = await get_ticket(interaction.guild,chid=interaction.channel.id) # type: ignore
        claimedby = ticket['claimedby']
        user = ticket['userid']
        if ch is None:
            if interaction.author.id not in me:
                await interaction.reply(f"Hey <@{claimedby}>, {interaction.author.mention} wants to lock this ticket.",view=ConfirmTicketButton(claimedby=claimedby))
            else:
                await archive_ticket(ticket_ch=interaction.channel)
                #await interaction.channel.remove_user(interaction.guild.get_member(user))
                await interaction.reply(f"Locked Ticket.",ephemeral=True)
        else:
            if interaction.author.id not in me:
                await ch.send(f"Hey <@{claimedby}>, {interaction.author.mention} wants to lock this ticket.",view=ConfirmTicketButton(claimedby=claimedby))
            else:
                await archive_ticket(ticket_ch=ch)
                #await ch.remove_user(interaction.guild.get_member(user))
                await ch.send(f"Locked Ticket.")
                await interaction.reply(f"Locked Ticket.",ephemeral=True)

    @ticket_group.command(name="delete",description="Deletes a ticket")
    @commands.guild_only()
    async def ticket_delete(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer()
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        await interaction.followup.send(view=ConfirmButton(func_confirm=ch.delete,func_cancel=pass_))

    @ticket_group.command(name="save",description="Saves a ticket")
    @commands.guild_only()
    async def ticket_save(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer(ephemeral=True)
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        file = await save_ticket(ch)
        await interaction.reply(f"Saved Transcript, attached below:",ephemeral=True,file=file)

    @ticket_group.command(name="reopen",description="Reopens a ticket")
    @commands.guild_only()
    async def ticket_reopen(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer()
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        try:
            await unarchive_ticket(ticket_ch=ch)
        except Exception as e: 
            print(e)
            logger_.warning(traceback.format_exc())
            await interaction.reply(f"Failed to reopen ticket.",ephemeral=True)
        await interaction.reply(f"Reopened Ticket.",view=SupportTicketButtons())

    @ticket_group.command(name="buttons",description="Buttons")
    @commands.guild_only()
    async def ticket_buttons(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        await interaction.reply(view=SupportTicketButtons())

    @ticket_group.command(name="transcript",description="Creates a transcript for a ticket.")
    @commands.guild_only()
    async def ticket_transcript(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer(ephemeral=True)
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        file = await save_ticket(ch)
        await interaction.reply(f"Saved Transcript, attached below:",ephemeral=True,file=file)

    @ticket_group.command(name='claim',description="Claims a ticket. Mod only.")
    @commands.guild_only()
    async def ticket_claim(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer()
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        await claim_ticket(ch, interaction.author)
        await interaction.reply(f"Claimed Ticket.",ephemeral=True)

    @ticket_group.command(name='unclaim',description="Unclaims a ticket. Mod only.")
    @commands.guild_only()
    async def ticket_unclaim(self, interaction: commands.Context, ch: Optional[discord.abc.GuildChannel]=None):
        await interaction.defer()
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.reply("This command can only be used in a ticket channel.",ephemeral=True)
        await unclaim_ticket(ch)
        await interaction.reply(f"Unclaimed Ticket.",ephemeral=True)

    @ticket_group.command(name="gettranscript",description="Gets a transcript for a ticket.")
    @commands.guild_only()
    async def ticket_gettranscript(self, interaction: commands.Context, ticket_num: Optional[int]=None):
        await interaction.defer()
        if ticket_num is None:
            ticket = await get_ticket(interaction.guild,user=interaction.author)
        else:
            ticket = await get_ticket(interaction.guild,num=ticket_num)
        if ticket is None: await interaction.reply("Invalid ticket number.",ephemeral=True)
        else:
            file = await save_ticket(await getorfetch_channel(interaction.guild,ticket["chid"]))
            await interaction.reply(f"Saved Transcript, attached below:",ephemeral=True,file=file)

    
    @ticket_group.command(name="tickets",description="Gets tickets for a user.")
    @commands.guild_only()
    async def ticket_gettickets(interaction: commands.Context, user: Optional[discord.User]=None):
        await interaction.defer()
        if user is None: user = interaction.author
        elif user is not None and interaction.author.id not in me and interaction.author != user:
            await interaction.reply("You can only lookup your own tickets.")
            return
        tickets = await get_tickets(user)
        if tickets is None: await interaction.reply("No tickets found.",ephemeral=True)
        else:
            returnv = ""
            tr = 0
            for ticket in tickets:
                tr += 1
                returnv += f"Ticket #`{formatticketnum(ticket['ticket_num'])}` ({ticket['tickettype']}) | Opened at {dctimestamp(ticket.get('datelogged'),'f')} {dctimestamp(ticket.get('datelogged'),'R')} | Claimed by {'<@'+str(ticket.get('claimedby'))+'>' if ticket.get('claimedby', False) else '`Unclaimed`'} | <#{ticket.get('chid')}>\n"
            returnv = f"You have {tr} tickets open:\n{returnv}"
            await interaction.reply(returnv,ephemeral=True)

    @commands.hybrid_command(name="sendticketbuttons",description="Owner only. Sends a message with the ticket buttons.")
    @commands.guild_only()
    @commands.is_owner()
    async def send_ticket(self, interaction: commands.Context, ch: Optional[discord.TextChannel]=None):
        if ch is None: ch = interaction.channel
        emb = makeembed("Support Ticket",description="Open a ticket by pressing the below button to directly contact the Admin Team about your inquiry.",color=discord.Colour.brand_green())
        await ch.send(embed=emb,view=OpenTicketView())

    @commands.hybrid_group(name='settings',description="Settings commands")
    @app_commands.guilds(*guilds)
    async def settings_group(self, interaction: commands.Context): pass

    @settings_group.command(name="setcategory",description="Sets the ticket category.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def settings_setcategory(self, interaction: commands.Context, category: discord.CategoryChannel):
        await interaction.defer()
        try:
            await GuildSettings.filter(guildid=interaction.guild.id).update(ticket_category=category.id)
        except:
            await GuildSettings.create(guildid=interaction.guild.id,ticket_category=category.id,archived_tickets_category=None)
        await interaction.reply(f"Set ticket category to {category.mention}",ephemeral=True)
    
    @settings_group.command(name='setmodrole',description="Sets the mod role.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def settings_setmodrole(self, interaction: commands.Context, role: discord.Role):
        await interaction.defer()
        try:
            await GuildSettings.filter(guildid=interaction.guild.id).update(modrole=role.id)
        except:
            await GuildSettings.create(guildid=interaction.guild.id,modrole=role.id)
        await interaction.reply(f"Set mod role to {role.mention}",ephemeral=True)
    
    @settings_group.command(name='setadminrole',description="Sets the admin role.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def settings_setadminrole(self, interaction: commands.Context, role: discord.Role):
        await interaction.defer()
        try:
            await GuildSettings.filter(guildid=interaction.guild.id).update(adminrole=role.id)
        except:
            await GuildSettings.create(guildid=interaction.guild.id,adminrole=role.id)
        await interaction.reply(f"Set admin role to {role.mention}",ephemeral=True)

    @settings_group.command(name='setticketchannel',description="Sets whether to use text channels or threads.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def settings_setticketchannel(self, interaction: commands.Context, value: bool):
        await interaction.defer()
        try:
            await GuildSettings.filter(guildid=interaction.guild.id).update(usingtextchannels=value)
        except:
            await GuildSettings.create(guildid=interaction.guild.id,usingtextchannels=value)
        await interaction.reply(f"Set using text channels to {value}",ephemeral=True)

    @settings_group.command('addtickettype',description="Adds a ticket type.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.describe(name="Name of the ticket type you want to add. (e.g. Support)",
    emoji="Emoji to use for the ticket type. (e.g. :tools:)",
    color="Color to use for the ticket button. Default gray."
    )
    # @app_commands.choices(color=[
    #     app_commands.Choice(name="Red",value=4),
    #     app_commands.Choice(name="Green",value=3),
    #     app_commands.Choice(name="Blue",value=1),
    #     app_commands.Choice(name="Grey (default)",value=2),
    # ])
    async def settings_addtickettype(self, interaction: commands.Context, name: str, color: Literal["Red","Green","Blue","Gray","Grey"]="Gray", emoji: Optional[str]=None):
        await interaction.defer()     
        color_: discord.ButtonStyle = discord.ButtonStyle(color)   
        try:
            await TicketType.create(guildid=interaction.guild.id,tickettype=name,color=int(color_),emoji=emoji)
        except:
            await interaction.reply(f"Failed to add ticket type {name} ({emoji if emoji else ''}) with color {color}",ephemeral=True)
            logger_.error(traceback.format_exc())
            return
        await interaction.reply(f"Added ticket type {name}{f' ({emoji})' if emoji else ''} with color {color}",ephemeral=True)

# class AidenTicketType(Enum):
#     SUPPORT = 1
#     BUG = 2
#     REPORT = 3
#     ROLE = 4

#     def __str__(self):
#         return self.name.title()

# class MinecraftServers(Enum):
#     SURVIVAL = "survival"
#     CREATIVE = "creative"
#     CLICK_ARCHIVE = "click"
#     TEST = "testing"
#     NA = "na"

#     def __str__(self):
#         return self.name.title()

async def getnextticketnum(guild: Union[discord.Guild, int], cursor: Optional[asqlite.Cursor]=None) -> int:
    """Returns the next ticket number, or 0 if none are found"""
    num = -1
    if isinstance(guild, discord.Guild): guild = guild.id
    #if cursor is None:
    try: num = int((await Ticket.filter(guildid=guild).order_by("-ticket_num").first()).ticket_num)
    except: pass
    return num+1
        # async with asqlite.connect("users.db") as conn:
        #     async with conn.cursor() as cursor:
        #         await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
        #         tr = 0
        #         for row in await cursor.fetchall():
        #             row = dict(row)
        #             tr += 1
        #             if num == -1:
        #                 num = row["ticket_num"]
        #             elif num > row["ticket_num"] > 0:
        #                 return num+1
        #         if tr == 1: return 2
        #         return None
    # else:
    #     await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
    #     tr = 0
    #     for row in await cursor.fetchall():
    #         row = dict(row)
    #         tr += 1
    #         if num == -1:
    #             num = row["ticket_num"]
    #     if tr == 1: return 2
    #     return None

async def create_ticket(interaction: discord.Interaction, tickettype: str, modal1: ui.TextInput, modal2: ui.TextInput, chtype: discord.ChannelType=discord.ChannelType.private_thread) -> Union[discord.Thread, discord.TextChannel, None]:
    try:
        user = interaction.author
        num = await getnextticketnum(interaction.guild)
        guildsettings = await GuildSettings.filter(guildid=interaction.guild.id).first()
        ticket_category = guildsettings.ticket_category
        modrole = guildsettings.modrole
        adminrole = guildsettings.adminrole
        if num is None:             num = "001"
        else:                       num = formatticketnum(num)

        ch: Optional[Union[discord.TextChannel, discord.Thread]] | None = None

        msg = f"{user.mention} created a ticket!\nA <@&{modrole}> or <@&{adminrole}> will be with you soon."
        emb = makeembed_bot(title=f"Ticket #{num}",description=f"A <@&{modrole}> or <@&{adminrole}> will be with you soon, hang tight!\nIf you would like to elaborate about your responses here, feel free.",author=str(user),author_icon_url=user.avatar.url)
        try:
            emb.add_field(name=modal2.label,value=modal2.value)
        except:
            raise ValueError()
        emb.add_field(name=modal1.label,value=modal1.value)

        if chtype == discord.ChannelType.text:
            ch = await user.guild.create_text_channel(category=getorfetch_channel(ticket_category,user.guild),name=f"ticket-{num}", topic=f"Ticket for {user}",
                                                reason=f"Ticket created by {user}",
                                                overwrites={user: discord.PermissionOverwrite(read_messages=True,send_messages=True,read_message_history=True)})
        elif chtype == discord.ChannelType.private_thread:
            #ch = await interaction.guild.get_channel(ticket_category).text_channels[0].create_thread(name=f"ticket-{num}",type=discord.ChannelType.private_thread,invitable=False)
            if interaction.channel.category_id == ticket_category:
                ch = await interaction.channel.create_thread(name=f"ticket-{num}",type=discord.ChannelType.private_thread,invitable=False)
        ticket_open_logger.info(f"{interaction.guild}: Ticket #{num} ({str(tickettype).title()}) created by {user} ({user.id}).")
        await ch.send(msg, embed=emb,view=ClaimTicketView())

        # async with asqlite.connect("users.db") as conn:
        #     async with conn.cursor() as cursor:
        #         now = int(datetime.datetime.now().timestamp())
        #         await cursor.execute("INSERT INTO Tickets (datelogged, lastupdated, ticket_num, tickettype, userid, username, chid, chtype, claimedby, issolved, transcript) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        #                                 (now, now, num, tickettype.value, user.id, str(user), ch.id, chtype.value, None, False, None))
        #         await cursor.execute("SELECT * FROM Tickets WHERE userid=?",(user.id,))
        #         ran = True
        #         for _ in await cursor.fetchall():
        #             ran = False
        #             await cursor.execute("UPDATE Tickets SET ticket_num=? WHERE userid=? AND issolved=?",(num, user.id,False))
        #             break
        #         if ran: await cursor.execute("INSERT INTO TicketUsers(datelogged, lastupdated, ticket_num, userid, username) VALUES (?,?,?,?,?)",(now, now, num, user.id, str(user)))
        # return ch
        await Ticket.create(ticket_num=num,tickettype=tickettype,guildid=interaction.guild.id,chid=ch.id,chtype=chtype.value,userid=user.id,username=str(user))
    except ValueError:
        raise ValueError("Invalid server name.")
    except Exception as e:
        logger_.warning(traceback.format_exc())
        raise e

async def get_ticket(guild: Union[discord.Guild,int],user: Optional[discord.Member]=None, num: Optional[int]=None, chid: Optional[int]=None, *, cursor: Optional[asqlite.Cursor]=None) -> Optional[Dict]:
    # if cursor is None:
    #     async with asqlite.connect("users.db") as conn:
    #         async with conn.cursor() as cursor:
                
    #             if user is not None:    await cursor.execute("SELECT * FROM Tickets WHERE creator=? ORDER BY ticket_num DESC",(user.id,))
    #             elif num is not None:   await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(num,))
    #             elif chid is not None:  await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(chid,))

    #             for row in await cursor.fetchall():
    #                 return dict(row)
    # else:
    #     if user is not None:     await cursor.execute("SELECT * FROM Tickets WHERE creator=? ORDER BY ticket_num DESC",(user.id,))
    #     elif num is not None:    await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(num,))
    #     elif chid is not None:   await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(chid,))

    #     for row in await cursor.fetchall():
    #         return dict(row)
    # return None
    if isinstance(guild, discord.Guild): guild = guild.id
    if user is not None:     returnv = await Ticket.filter(userid=user.id,guildid=guild).order_by("-ticket_num").first()
    elif num is not None:    returnv = await Ticket.filter(ticket_num=num,guildid=guild).first()
    elif chid is not None:   returnv = await Ticket.filter(chid=chid,guildid=guild).first()
    return dict(returnv)


async def get_tickets(guild: Union[discord.Guild,int],user: Optional[discord.Member]=None, *, cursor: Optional[asqlite.Cursor]=None) -> List[dict] | None:
    # returnv = []
    # if cursor is None:
    #     async with asqlite.connect("users.db") as conn:
    #         async with conn.cursor() as cursor:
    #             if user is not None: await cursor.execute("SELECT * FROM Tickets WHERE userid=? ORDER BY ticket_num DESC",(user.id,))
    #             else: await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
    #             for row in await cursor.fetchall(): returnv.append(dict(row))
    # else:
    #     if user is not None: await cursor.execute("SELECT * FROM Tickets WHERE userid=? ORDER BY ticket_num DESC",(user.id,))
    #     else: await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
    #     for row in await cursor.fetchall(): returnv.append(dict(row))
    # return returnv
    if isinstance(guild, discord.Guild): guild = guild.id
    if user is not None: returnv = await Ticket.filter(userid=user.id,guildid=guild).order_by("-ticket_num").all()
    else: returnv = await Ticket.all()
    return [dict(i) for i in returnv]

async def archive_ticket(user: Optional[discord.Member]=None, ticket_num: Optional[int]=None, ticket_ch: Optional[Union[discord.TextChannel, discord.Thread]]=None, cursor: Optional[asqlite.Cursor]=None) -> bool:
    return await archive_unarchive_ticket(True, user, ticket_num, ticket_ch, cursor)

async def unarchive_ticket(user: Optional[discord.Member]=None, ticket_num: Optional[int]=None, ticket_ch: Optional[Union[discord.TextChannel, discord.Thread]]=None, cursor: Optional[asqlite.Cursor]=None) -> bool:
    #ticket_reopen_logger.info(f"{interaction.guild}: Ticket #{ticket_num} reopened by {user} ({user.id})")
    return await archive_unarchive_ticket(False, user, ticket_num, ticket_ch, cursor)

async def archive_unarchive_ticket(issolved: bool, user: Optional[discord.Member]=None, ticket_num: Optional[int]=None, ticket_ch: Optional[Union[discord.TextChannel, discord.Thread]]=None, cursor: Optional[asqlite.Cursor]=None) -> bool:
    try:
        # if cursor is not None:
        #     if user is not None:
        #         print("Not reccomened to use this. TicketType is not taken into account.")
        #         await cursor.execute("SELECT * FROM Tickets WHERE userid=? AND issolved=?",(user.id,not issolved))
        #         for row in await cursor.fetchall():
        #             row = dict(row)
        #             await cursor.execute("UPDATE Tickets SET issolved=? WHERE userid=? AND issolved=?",(not issolved, user.id,issolved))
        #             ticket_ch = await getorfetch_channel(row["chid"],user.guild)
        #             if type(ticket_ch) == discord.TextChannel:
        #                 await ticket_ch.move(category=await getorfetch_channel(row["chid"],user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
        #                 await ticket_ch.edit(position=await getorfetch_channel(row["chid"],user.guild).channels.__len__())
        #                 if issolved: 
        #                     ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     for user in await ticket_ch.fetch_members():
        #                         if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                 else: 
        #                     ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                     return True
        #             elif type(ticket_ch) == discord.Thread:
        #                 await ticket_ch.edit(archived=issolved,locked=issolved)
        #                 if issolved: 
        #                     ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     for user in await ticket_ch.fetch_members():
        #                         if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                 else: 
        #                     ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                 return True
        #     elif ticket_num is not None:
        #         await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(ticket_num,))
        #         for row in await cursor.fetchall():
        #             row = dict(row)
        #             await cursor.execute("UPDATE Tickets SET issolved=? WHERE ticket_num=?",(issolved, ticket_num,))
        #             ticket_ch = await getorfetch_channel(row["chid"],user.guild)
        #             if type(ticket_ch) == discord.TextChannel:
        #                 await ticket_ch.move(category=await getorfetch_channel(row["chid"],user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
        #                 await ticket_ch.edit(position=await getorfetch_channel(row["chid"],user.guild).channels.__len__())
        #                 if issolved: 
        #                     ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     for user in await ticket_ch.fetch_members():
        #                         if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                 else: 
        #                     ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                 return True
        #             elif type(ticket_ch) == discord.Thread:
        #                 await ticket_ch.edit(archived=issolved,locked=issolved)
        #                 if issolved: 
        #                     ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     for user in await ticket_ch.fetch_members():
        #                         if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                 else: 
        #                     ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                 return True
        #     elif ticket_ch is not None:
        #         await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
        #         for row in await cursor.fetchall():
        #             row = dict(row)
        #             await cursor.execute("UPDATE Tickets SET issolved=? WHERE chid=?",(issolved, ticket_ch.id,))
        #             ticket_ch = await getorfetch_channel(row["chid"],user.guild)
        #             if type(ticket_ch) == discord.TextChannel:
        #                 await ticket_ch.move(category=await getorfetch_channel(row["chid"],user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
        #                 await ticket_ch.edit(position=await getorfetch_channel(row["chid"],user.guild).channels.__len__())
        #                 if issolved: ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {user.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
        #                 else: ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {user.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
        #                 return True
        #             elif type(ticket_ch) == discord.Thread:
        #                 await ticket_ch.edit(archived=issolved,locked=issolved)
        #                 if issolved: 
        #                     ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     for user in await ticket_ch.fetch_members():
        #                         if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                 else: 
        #                     ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                     await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                 return True  
        # else:
        #     async with asqlite.connect("users.db") as conn:
        #         async with conn.cursor() as cursor:
        #             if user is not None:
        #                 print("Not reccomened to use this. TicketType is not taken into account.")
        #                 await cursor.execute("SELECT * FROM Tickets WHERE userid=? AND issolved=?",(user.id,not issolved))
        #                 for row in await cursor.fetchall():
        #                     row = dict(row)
        #                     await cursor.execute("UPDATE Tickets SET issolved=? WHERE userid=? AND issolved=?",(not issolved, user.id,issolved))
        #                     ticket_ch = await getorfetch_channel(row["chid"],user.guild)
        #                     if type(ticket_ch) == discord.TextChannel:
        #                         await ticket_ch.move(category=await getorfetch_channel(row["chid"],user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
        #                         await ticket_ch.edit(position=await getorfetch_channel(row["chid"],user.guild).channels.__len__())
        #                         if issolved: 
        #                             ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             for user in await ticket_ch.fetch_members():
        #                                 if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                         else: 
        #                             ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                         return True
        #                     elif type(ticket_ch) == discord.Thread:
        #                         await ticket_ch.edit(archived=issolved,locked=issolved)
        #                         if issolved: 
        #                             ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             for user in await ticket_ch.fetch_members():
        #                                 if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                         else: 
        #                             ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                         return True
        #             elif ticket_num is not None:
        #                 await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(ticket_num,))
        #                 for row in await cursor.fetchall():
        #                     row = dict(row)
        #                     await cursor.execute("UPDATE Tickets SET issolved=? WHERE ticket_num=?",(issolved, ticket_num,))
        #                     ticket_ch = await getorfetch_channel(row["chid"],ticket_ch.guild)
        #                     if type(ticket_ch) == discord.TextChannel:
        #                         await ticket_ch.move(category=await getorfetch_channel(row["chid"],user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
        #                         await ticket_ch.edit(position=await getorfetch_channel(row["chid"],user.guild).channels.__len__())
        #                         if issolved: 
        #                             ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             for user in await ticket_ch.fetch_members():
        #                                 if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                         else: 
        #                             ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                         return True
        #                     elif type(ticket_ch) == discord.Thread:
        #                         await ticket_ch.edit(archived=issolved,locked=issolved)
        #                         if issolved: 
        #                             ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             for user in await ticket_ch.fetch_members():
        #                                 if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                         else: 
        #                             ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                         return True
        #             elif ticket_ch is not None:
        #                 await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
        #                 for row in await cursor.fetchall():
        #                     row = dict(row)
        #                     await cursor.execute("UPDATE Tickets SET issolved=? WHERE chid=?",(issolved, ticket_ch.id,))
        #                     ticket_ch = await getorfetch_channel(row["chid"],ticket_ch.guild)
        #                     if type(ticket_ch) == discord.TextChannel:
        #                         await ticket_ch.move(category=await getorfetch_channel(row["chid"],user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
        #                         await ticket_ch.edit(position=await getorfetch_channel(row["chid"],user.guild).channels.__len__())
        #                         if issolved: 
        #                             ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             for user in await ticket_ch.fetch_members():
        #                                 if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                         else: 
        #                             ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                         return True
        #                     elif type(ticket_ch) == discord.Thread:
        #                         await ticket_ch.edit(archived=issolved,locked=issolved)
        #                         if issolved: 
        #                             ticket_close_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             for user in await ticket_ch.fetch_members():
        #                                 if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
        #                         else: 
        #                             ticket_open_logger.info(f"{interaction.guild}: Ticket #{formatticketnum(row['ticket_num'])} unarchived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
        #                             await ticket_ch.add_user(await getorfetch_user(row.get('userid'),ticket_ch.guild))
        #                         return True            

        settings = await GuildSettings.filter(guildid=ticket_ch.guild.id).first()
        guild = ticket_ch.guild
        if user is not None:
            row = await Ticket.filter(userid=user.id,issolved=not issolved).first()
            row = dict(row)
            ticket_ch = await getorfetch_channel(row["chid"],user.guild)
            if issolved:
                if type(ticket_ch) == discord.TextChannel:
                    await ticket_ch.move(category=await getorfetch_channel(settings.archived_tickets_category,user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                    await ticket_ch.edit(position=await getorfetch_channel(settings.chid,user.guild).channels.__len__(),name='archived-'+row["ticket_num"])
                elif type(ticket_ch) == discord.Thread:
                    await ticket_ch.edit(name='archived-'+row["ticket_num"])
                ticket_close_logger.info(f"{guild}: Ticket #{formatticketnum(row['ticket_num'])} archived by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
            else:
                if type(ticket_ch) == discord.TextChannel:
                    await ticket_ch.move(category=await getorfetch_channel(settings.chid,user.guild),reason=f"Ticket #{formatticketnum(row['ticket_num'])} reopened by {user}",sync_permissions=True)
                    pos = 0
                    for ch in await getorfetch_channel(settings.ticket_category,user.guild).channels:
                        num = ch.name.replace('ticket-').replace('archived-').strip()
                        pos += 1
                        try: num = int(num)
                        except: continue
                        if num < int(row['ticket_num']):
                            await ticket_ch.edit(position=pos,category=settings.ticket_category,name='ticket-'+row["ticket_num"])
                elif isinstance(ticket_ch, discord.Thread):
                    await ticket_ch.edit(name='ticket-'+row["ticket_num"])
                ticket_reopen_logger.info(f"{guild}: Ticket #{formatticketnum(row['ticket_num'])} reopenened by {await getorfetch_user(row.get('claimedby'),ticket_ch.guild)} ({row.get('claimedby')}).")
            if isinstance(ticket_ch, discord.Thread):
                await ticket_ch.edit(archived=issolved,locked=issolved)
        if ticket_ch is not None:
            if isinstance(ticket_ch, discord.Thread):
                for author in await ticket_ch.fetch_members():
                    if (await getorfetch_member(author.id,ticket_ch.guild)).get_role(settings.adminrole) is not None \
                    or (await getorfetch_member(author.id,ticket_ch.guild)).get_role(settings.modrole) is not None \
                    or author.id == ticket_ch.guild.owner \
                    or (await getorfetch_user(author.id,ticket_ch.guild)).bot:
                        continue
                    try:
                        if issolved:
                            await ticket_ch.remove_user(author)                
                        else:
                            await ticket_ch.add_user(author)
                    except: pass
        await (await Ticket.filter(userid=user.id,issolved=not issolved).first()).update_from_dict({"issolved": issolved})
    except Exception as e:
        print(e)
        logger_.warning(traceback.format_exc())
        return False

async def save_ticket(ticket_ch: Union[discord.TextChannel, discord.Thread]) -> Optional[discord.File]:
    if isinstance(ticket_ch, discord.Thread):
        msgs: list[discord.Message] = [msg async for msg in ticket_ch.history(limit=None)]

        authors: list[discord.ThreadMember] = list(set([msg.author for msg in msgs]))
        authors.extend(await ticket_ch.fetch_members())
        for _ in range(1,3):
            for author in authors:
                if isinstance(author, discord.ThreadMember):
                    authors.remove(author)
                    authors.append(await getorfetch_user(author.id,ticket_ch.guild))
        
        authors = list(set(authors))

        msgs.reverse()
    elif isinstance(ticket_ch, discord.TextChannel):
        msgs = [m async for m in ticket_ch.history(limit=None)]

        authors: list[discord.Member] = list(set([msg.author for msg in msgs]))
        for _ in range(1,3):
            for author in authors:
                if type(author) == discord.Member:
                    #await ticket_ch.set_permissions(author,discord.PermissionOverwrite(view_channel=False),reason="Ticket being transcribed.")
                    authors.append(await getorfetch_user(author.id,ticket_ch.guild))
        
        authors = list(set(authors))
    transcript = ""
    date = ticket_ch.created_at

    row = dict(await Ticket.get(chid=ticket_ch.id))
    try:
        date = f"{date.year}-{0 if len(str(date.month)) == 1 else ''}{date.month}-{0 if len(str(date.day)) == 1 else ''}{date.day}"
    except Exception as e:
        print(e)
        logger_.warning(traceback.format_exc())
    
    tickettype = row.get('tickettype')
    # if row.get('guildid') == SNUGTOWN:
    #     tickettype = AidenTicketType(tickettype)
    # else:
    tickettype = (await TicketType.filter(guildid=row.get('guildid'),tickettype=tickettype).first()).tickettype
    transcript += f"Guild {ticket_ch.guild.name} ({row.get('guildid')})\n{'Thread' if type(ticket_ch) == discord.ChannelType.private_thread else 'Text Channel'} #{ticket_ch.name} ({ticket_ch.id})\n"
    transcript += f"Ticket #{formatticketnum(str(row.get('ticket_num')))} | {row.get('username')} ({row.get('userid')}) | {date} | {tickettype}\n"
    transcript += f"\nTicket Members:\n"
    for author in authors:
        if author.id == row.get('userid'):
            transcript += f"{author} ({author.id}) (Creator)\n"
        elif author.id == ticket_ch.guild.owner:
            transcript += f"{author} ({author.id}) (Guild Owner)\n"
        elif (await getorfetch_member(author.id,ticket_ch.guild)).guild_permissions.administrator:
            transcript += f"{author} ({author.id}) (Admin)\n"
        else:
            transcript += f"{author} ({author.id})\n"
    transcript += f"\nTranscript:\n"
    for msg in msgs:
        dt = datetime.datetime.strftime(msg.created_at, "%Y-%m-%d %H:%M:%S")
        transcript += f"[{dt}] {msg.author}: {msg.content}\n"
        if len(msg.attachments) > 0:
            for attachment in msg.attachments:
                transcript += f"(Attachment) {attachment.url}\n"
    
    transcript += f"\nClosed at {datetime.datetime.fromtimestamp(int(row.get('lastupdated')))}"
    transcript += f"\nTranscribed at {datetime.datetime.fromtimestamp(int(datetime.datetime.now().timestamp()))}"

    await Ticket.filter(chid=ticket_ch.id).update(transcript=transcript)

    file = discord.File(io.BytesIO(transcript.encode()), filename=f"{row.get('guildid')}-ticket{row.get('ticket_num')}-{row.get('userid')}.txt")
    return file
    # try:
    #     async with asqlite.connect("users.db") as conn:
    #         async with conn.cursor() as cursor:
    #             os.chdir("tickets")
    #             await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
    #             row = None
    #             for row in await cursor.fetchall():
    #                 row = dict(row)
    #                 break
    #             os.chdir(f"{AidenTicketType(row['tickettype'])}".lower())
    #             with open(f"transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt","w") as f:
    #                 date = ticket_ch.created_at
    #                 try:
    #                     date = f"{date.year}-{0 if len(str(date.month)) == 1 else ''}{date.month}-{0 if len(str(date.day)) == 1 else ''}{date.day}"
    #                 except Exception as e:
    #                     print(e)
    #                     logger_.warning(traceback.format_exc())
    #                 f.write(f"Ticket #{formatticketnum(row.get('ticket_num'))} | {row.get('username')} ({row.get('userid')}) | {date} | {AidenTicketType(row.get('tickettype'))}\n")
    #                 f.write(f"\nTicket Members:\n")
    #                 for author in authors:
    #                     if author.id == row.get('userid'): f.write(f"{author} ({author.id}) (Creator)\n")
    #                     elif author.id == me: f.write(f"{author} ({author.id}) (Admin)\n")
    #                     else: f.write(f"{author} ({author.id})\n")
    #                 f.write(f"\nTranscript:\n")
    #                 for msg in thread_msgs:
    #                     dt = datetime.datetime.strftime(msg.created_at, "%Y-%m-%d %H:%M:%S")
    #                     if len(msg.attachments) > 0:
    #                         for attachment in msg.attachments:
    #                             f.write(f"[{dt}] {msg.author}: {attachment.url}\n")
    #                     else:
    #                         f.write(f"[{dt}] {msg.author}: {msg.content}\n")
    #                 f.write(f"\nClosed at {datetime.datetime.fromtimestamp(row.get('lastupdated'))}")
    #                 f.write(f"\nTranscribed at {datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')}")
    #             os.chdir("../../")
    #             await cursor.execute("UPDATE Tickets SET transcript=? WHERE chid=?",(f"tickets/{AidenTicketType(row['tickettype'])}/transcript_ticket-{row.get('ticket_num')}.txt",ticket_ch.id,))
    #             with open(f"tickets/{AidenTicketType(row['tickettype'])}/transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt","rb") as f:
    #                 ticket_transcribe_logger.info(f"{interaction.guild}: Ticket #{row.get('ticket_num')} transcribed to transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt.")
    #                 return discord.File(f, filename=f"transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt")
    # except:
    #     return None

async def claim_ticket(ticket_ch: Optional[Union[discord.TextChannel, discord.Thread]], user: discord.Member) -> bool:
    return await claim_unclaim_ticket(True,ticket_ch,user)

async def unclaim_ticket(ticket_ch: Optional[Union[discord.TextChannel, discord.Thread]]) -> bool:
    return await claim_unclaim_ticket(False,ticket_ch,None)

async def claim_unclaim_ticket(claim: bool, ticket_ch: Optional[Union[discord.TextChannel, discord.Thread]], user: discord.Member) -> bool:
    # try:
    #     async with asqlite.connect("users.db") as conn:
    #         async with conn.cursor() as cursor:
    #             await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
    #             for row in await cursor.fetchall():
    #                 row = dict(row)
    #                 if bool(row.get("issolved")): return False
    #                 if claim:
    #                     await cursor.execute("UPDATE Tickets SET claimedby=? WHERE chid=?",(user.id,ticket_ch.id,))
    #                 else:
    #                     await cursor.execute("UPDATE Tickets SET claimedby=? WHERE chid=?",(None,ticket_ch.id,))
    #                 if claim: ticket_claim_logger.info(f"{ticket_ch.guild.id}: Ticket #{formatticketnum(formatticketnum(row['ticket_num']))} claimed by {user} ({user.id}).")
    #                 else: ticket_unclaim_logger.info(f"{ticket_ch.guild.id}: Ticket #{formatticketnum(formatticketnum(row['ticket_num']))} unclaimed by {user} ({user.id}).")
    #                 return True
    # except:
    #     return False
    try:
        row = dict(await Ticket.get(chid=ticket_ch.id))
        if bool(row.get("issolved")): return False
        if claim:
            await Ticket.filter(chid=ticket_ch.id).update(claimedby=user.id)
        else:
            await Ticket.filter(chid=ticket_ch.id).update(claimedby=None)
        if claim: ticket_claim_logger.info(f"{ticket_ch.guild.id}: Ticket #{formatticketnum(formatticketnum(row['ticket_num']))} claimed by {user} ({user.id}).")
        else: ticket_unclaim_logger.info(f"{ticket_ch.guild.id}: Ticket #{formatticketnum(formatticketnum(row['ticket_num']))} unclaimed by {user} ({user.id}).")
        return True
    except:
        return False

async def check_user_ticket(user: discord.Member, guild: Optional[discord.Guild]) -> Optional[int]:
    """Checks to see if a user has an open ticket. Returns the ticket number if so."""
    # async with asqlite.connect("users.db") as conn:
    #     async with conn.cursor() as cursor:
    #         await cursor.execute("SELECT * FROM Tickets WHERE userid=?",(user.id,))
    #         for row in await cursor.fetchall():
    #             if bool(dict(row).get("issolved")): continue
    #             return dict(row).get("chid")
    # return None
    if guild is None: guild = user.guild
    async for ticket in Ticket.filter(guildid=guild.id,userid=user.id,issolved=False).order_by("ticket_num"):
        return dict(ticket).get('ticket_num')


class OpenTicketModal(ui.Modal, title='Questionnaire Response'):
    server = ui.TextInput(label='Which server is this issue on?', placeholder='Survival, Creative, Click or NA',required=True)
    issue = ui.TextInput(label='Please detail your issue/inquiry', placeholder='Why are you making this ticket?',required=True)

    def __init__(self,tickettype: str, ):
        super().__init__()
        self.type = tickettype

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True,ephemeral=True)
        #if t := await check_user_ticket(interaction.author):
        #    await interaction.reply(f"You already have a ticket open. Go here and close it before opening another: <#{t}>",ephemeral=True)
        #    return
        try:
            ch = await create_ticket(interaction, self.type, self.issue.value, self.server.value)
            await interaction.followup.send(f"Sucessfully created {ch.mention}.",ephemeral=True)
        except:
            await interaction.followup.send("An error occured. Make sure you spelled the server correctly in the first question.",ephemeral=True)

class CustomizableOpenTicketButton(discord.ui.Button):
    def __init__(self, button: discord.ui.Button, type: str, guild: discord.Guild):
        """Type should be the ticket type."""
        super().__init__(style=button.style, label=button.style, disabled=button.disabled, custom_id=button.custom_id, url=button.url, emoji=button.emoji, row=button.row)
    
    async def callback(self, interaction: discord.Interaction):
        if t := await check_user_ticket(interaction.user,interaction.guild):
            await interaction.response.send_message(f"You already have a ticket open. Go here and close it before opening another: <#{t}>",ephemeral=True)
            return
        await interaction.response.send_modal(OpenTicketModal(type))

class OpenTicketView(discord.ui.View):
    buttons: Optional[List[discord.ui.Button]]
    def __init__(self, *buttons: list[CustomizableOpenTicketButton]):
        """Takes *args, which should be the Button objecfts."""
        super().__init__(timeout=None)
        for button in buttons:
            try:
                self.add_item(button)
            except:
                raise TypeError("Button must be a discord.ui.Button or subclassed object.")

class ClaimTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Claim Ticket', style=discord.ButtonStyle.green, custom_id='persistent_view:claim',emoji="📝")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id not in me:
            await interaction.followup.send("This command is not for you")
            return
        await claim_ticket(interaction.channel, interaction.user)
        await interaction.followup.send(f"{interaction.user.mention} has claimed this ticket.")
    
    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.red, custom_id='persistent_view:close',emoji="❌")# x emoji
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id not in me:
            await interaction.followup.send("This command is not for you")
            return
        await archive_ticket(ticket_ch=interaction.channel)
        await interaction.followup.send("Closed Ticket.")
        
class ConfirmButton(discord.ui.View):
    def __init__(self,func_confirm,func_cancel):
        super().__init__()
        self.confirm_func = func_confirm
        self.cancel_func = func_cancel
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Confirming...', ephemeral=True)
        self.value = True
        await self.confirm_func()
        self.stop()
    


    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Cancelling...', ephemeral=True)
        self.value = False
        await self.cancel_func()
        self.stop()

class ConfirmTicketButton(discord.ui.View):
    def __init__(self,claimedby: int, func_confirm=None, func_cancel=None, func_confirm_args=None):
        super().__init__()
        self.confirm_func = func_confirm
        self.cancel_func = func_cancel
        self.claimedby = claimedby
        self.args = func_confirm_args
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.claimedby and interaction.user.id not in me:
            await interaction.response.send_message('You are not the person who claimed this ticket.')
            return
        await interaction.response.defer(thinking=True)
        if (await get_ticket(chid=interaction.channel.id)).get('issolved') == 0:
            #await interaction.channel.remove_user(interaction.guild.get_member(ticket.get('userid')))
            await archive_ticket(ticket_ch=interaction.channel)
            await interaction.followup.send(f"Locked Ticket.")
        self.value = True
        if self.confirm_func is not None and self.args is not None:
            await self.confirm_func(*self.args)
        elif self.confirm_func is not None:
            await self.confirm_func()
        await interaction.followup.send(f"Locked Ticket.")
        self.stop()

    


    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.claimedby:
            await interaction.response.send_message('You are not the person who claimed this ticket.')
            return
        await interaction.response.send_message('Cancelling...',)
        self.value = False
        if self.cancel_func is not None:
            await self.cancel_func()
        self.stop()

class SupportTicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Lock Ticket', style=discord.ButtonStyle.gray, custom_id='persistent_view:close_ticket',emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        ticket = await get_ticket(chid=interaction.channel.id)
        claimedby = ticket['claimedby']
        user = ticket['userid']
        if interaction.user.id not in me:
            await interaction.followup.send(f"Hey <@{claimedby}>, {interaction.user.mention} wants to lock this ticket.",view=ConfirmTicketButton(claimedby=claimedby))
        else:
            await archive_ticket(ticket_ch=interaction.channel)
    
    @discord.ui.button(label='Delete Ticket', style=discord.ButtonStyle.red, custom_id='persistent_view:delete_ticket',emoji="🗑️")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id not in me:
            await interaction.reply("This command is not for you")
            return
        await interaction.reply(view=ConfirmButton(func_confirm=interaction.channel.delete,func_cancel=pass_))
    
    @discord.ui.button(label='Save Transcript', style=discord.ButtonStyle.gray, custom_id="persistent_view:save_transcript",emoji="📄")
    async def save_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True,ephemeral=True)
        if interaction.user.id not in me:
            await interaction.reply("This command is not for you")
            return
        file = await save_ticket(interaction.channel)
        await interaction.reply(f"Saved Transcript.",ephemeral=True,file=file)
    
    @discord.ui.button(label='Reopen Ticket', style=discord.ButtonStyle.green, custom_id='persistent_view:reopen_ticket',emoji="🔓")
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id not in me:
            await interaction.reply("This command is not for you")
            return
        await unarchive_ticket(ticket_ch=interaction.channel)
        await interaction.reply(f"Reopened Ticket.",ephemeral=True)

def formatticketnum(num: Union[int, str]) -> str:
    if len(str(num)) == 1:      return f"00{num}"
    elif len(str(num)) == 2:    return f"0{num}"
    else:                       return str(num)

#async def get(class_) )

def _pass_(): pass
async def pass_(): pass

async def setup(bot: commands.Bot):
    bot.add_view(ClaimTicketView())
    bot.add_view(OpenTicketView())
    await bot.add_cog(TicketCog(bot))

async def main():
    await tortoise.Tortoise.init(config_file='config.yml')
    await tortoise.Tortoise.generate_schemas()
    # async with asqlite.connect("users.db") as conn:
    #     async with conn.cursor() as cursor:
    #         await cursor.execute("SELECT * FROM Tickets ORDER BY dbid ASC")
    #         for row in await cursor.fetchall():
    #             row = dict(row) 
    #             row.pop('dbid')
    #             row.pop('datelogged')
    #             row.pop('lastupdated')
    #             row['guildid'] = 1122231942453141565
    #             with open(f"{os.getcwd()}/{str(row.get('transcript')).lower().replace('-','').replace('.txt','')}-{row.get('userid')}.txt",'r') as f:
    #                 row['transcript'] = f.read()
    #             await Ticket.create(**row)

asyncio.run(main())