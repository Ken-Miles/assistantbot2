import discord
from discord import app_commands, ui
from discord.app_commands import Group
from discord.ext import commands, tasks
from main import me, logger_
from aidenlib.main import makeembed_bot, makeembed, getorfetch_channel, getorfetch_user
from enum import Enum
import asqlite
import datetime
import asyncio
import traceback
import logging
import os

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


ticket_category = 1133473132418699366
archived_tickets_category = 1142465661185052836


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ticket_group = Group(name="ticket",description="Ticket Commands",guild_ids=[1135603095385153696,1122231942453141565])
    
    @ticket_group.command(name="close",description="Closes a ticket")
    async def ticket_close(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True)
        ticket = await get_ticket(chid=interaction.channel.id)
        claimedby = ticket['claimedby']
        user = ticket['userid']
        if interaction.user.id != me:
            await interaction.followup.send(f"Hey <@{claimedby}>, {interaction.user.mention} wants to lock this ticket.",view=ConfirmTicketButton(claimedby=claimedby))
        else:
            await archive_ticket(ticket_ch=interaction.channel)
            #await interaction.channel.remove_user(interaction.guild.get_member(user))
            await interaction.followup.send(f"Locked Ticket.",ephemeral=True)
    

    @ticket_group.command(name="delete",description="Deletes a ticket")
    async def ticket_delete(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True)
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        if interaction.user.id != me:
            await interaction.followup.send("You are not allowed to do this.",ephemeral=True)
            return
        await interaction.response.send_message(view=ConfirmButton(func_confirm=ch.delete,func_cancel=pass_))

    @ticket_group.command(name="save",description="Saves a ticket")
    async def ticket_save(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True)
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        if interaction.user.id != me:
            await interaction.followup.send("You are not allowed to do this.",ephemeral=True)
            return
        file = await save_ticket(ch)
        await interaction.followup.send(f"Saved Transcript, attached below:",ephemeral=True,file=file)

    @ticket_group.command(name="reopen",description="Reopens a ticket")
    async def ticket_reopen(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True)
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        if interaction.user.id != me:
            await interaction.followup.send("You are not allowed to do this.",ephemeral=True)
            return
        try:
            await unarchive_ticket(ticket_ch=ch)
        except Exception as e: 
            print(e)
            logger_.warning(traceback.format_exc())
            await interaction.followup.send(f"Failed to reopen ticket.",ephemeral=True)
        await interaction.followup.send(f"Reopened Ticket.",view=SupportTicketButtons())

    @ticket_group.command(name="buttons",description="Buttons")
    async def ticket_buttons(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        if interaction.user.id != me:
            await interaction.response.send_message("This command is not for you")
            return
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        await interaction.response.send_message(view=SupportTicketButtons())

    @ticket_group.command(name="transcript",description="Creates a transcript for a ticket.")
    async def ticket_transcript(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True,ephemeral=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        file = await save_ticket(ch)
        await interaction.followup.send(f"Saved Transcript, attached below:",ephemeral=True,file=file)

    @ticket_group.command(name='claim',description="Claims a ticket. Mod only.")
    async def ticket_claim(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        await claim_ticket(ch, interaction.user)
        await interaction.followup.send(f"Claimed Ticket.",ephemeral=True)

    @ticket_group.command(name='unclaim',description="Unclaims a ticket. Mod only.")
    async def ticket_unclaim(self, interaction: discord.Interaction, ch: discord.abc.GuildChannel=None):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        if ch is None: ch = interaction.channel
        if type(ch) not in [discord.TextChannel,discord.Thread]: await interaction.followup.send("This command can only be used in a ticket channel.",ephemeral=True)
        await unclaim_ticket(ch)
        await interaction.followup.send(f"Unclaimed Ticket.",ephemeral=True)
    
    @ticket_group.command(name="gettranscript",description="Gets a transcript for a ticket.")
    async def ticket_gettranscript(self, interaction: discord.Interaction, ticket_num: int=None):
        await interaction.response.defer(thinking=True)
        if ticket_num is None:
            ticket = await get_ticket(user=interaction.user)
        else:
            ticket = await get_ticket(num=ticket_num)
        if ticket is None: await interaction.followup.send("Invalid ticket number.",ephemeral=True)
        else:
            file = await save_ticket(interaction.guild.get_channel(ticket["chid"]))
            await interaction.followup.send(f"Saved Transcript, attached below:",ephemeral=True,file=file)

    
    @ticket_group.command(name="tickets",description="Gets tickets for a user.")
    async def ticket_gettickets(interaction: discord.Interaction, user: discord.User=None):
        await interaction.response.defer(thinking=True)
        if user is None: user = interaction.user
        elif user != None and interaction.user.id != me and interaction.user != user:
            await interaction.followup.send("You can only lookup your own tickets.")
            return
        tickets = await get_tickets(user)
        if tickets is None: await interaction.followup.send("No tickets found.",ephemeral=True)
        else:
            returnv = ""
            tr = 0
            for ticket in tickets:
                tr += 1
                returnv += f"Ticket #`{formatticketnum(ticket['ticket_num'])}` ({TicketType(ticket['tickettype'])}) | Opened at {dctimestamp(ticket.get('datelogged'),'f')} {dctimestamp(ticket.get('datelogged'),'R')} | Claimed by {'<@'+str(ticket.get('claimedby'))+'>' if ticket.get('claimedby', False) else '`Unclaimed`'} | <#{ticket.get('chid')}>\n"
            returnv = f"You have {tr} tickets open:\n{returnv}"
            await interaction.followup.send(returnv,ephemeral=True)

    @commands.hybrid_command(name="sendticket",description="Owner only. Sends a message.")
    async def send_ticket(self, interaction: commands.Context, ch: discord.TextChannel=None):
        if interaction.author.id not in me:
            await interaction.reply("This command is not for you")
            return
        
        if ch is None: ch = interaction.channel
        
        emb = makeembed("Minecraft Support Ticket",description="Open a ticket by pressing the below button to directly contact the Minecraft Server Admin if you need help or wish to report something!",color=discord.Colour.brand_green())

        await ch.send(embed=emb,view=OpenTicketView())

class TicketType(Enum):
    SUPPORT = 1
    BUG = 2
    REPORT = 3
    ROLE = 4

    def __str__(self):
        return self.name.title()

class MinecraftServers(Enum):
    SURVIVAL = "survival"
    CREATIVE = "creative"
    CLICK_ARCHIVE = "click"
    TEST = "testing"
    NA = "na"

    def __str__(self):
        return self.name.title()

async def getnextticketnum(cursor: asqlite.Cursor=None) -> int:
    num = -1
    if cursor is None:
        async with asqlite.connect("users.db") as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
                tr = 0
                for row in await cursor.fetchall():
                    row = dict(row)
                    tr += 1
                    if num == -1:
                        num = row["ticket_num"]
                    elif num > row["ticket_num"] > 0:
                        return num+1
                if tr == 1: return 2
                return None
    else:
        await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
        tr = 0
        for row in await cursor.fetchall():
            row = dict(row)
            tr += 1
            if num == -1:
                num = row["ticket_num"]
        if tr == 1: return 2
        return None

async def create_ticket(interaction: discord.Interaction, tickettype: TicketType, modalresp1: str, modalresp2: str, chtype: discord.ChannelType=discord.ChannelType.private_thread) -> discord.Thread | discord.TextChannel | None:
    try:
        user = interaction.user
        num = await getnextticketnum()
        if num is None:             num = "001"
        else:                       num = formatticketnum(num)

        ch: discord.TextChannel | discord.Thread | None = None

        msg = f"{user.mention} created a ticket!\nA <@&1145241043026051075> will be with you soon."
        emb = makeembed_bot(title=f"Ticket #{num}",description="A <@&1145241043026051075> will be with you soon, hang tight!\nIf you would like to elaborate about your responses here, feel free.",author=str(user),author_icon_url=user.avatar.url)
        try:
            emb.add_field(name="Which server is this issue on?",value=MinecraftServers(modalresp2.strip().lower()))
        except:
            raise ValueError()
        emb.add_field(name="Why did you open this ticket?",value=modalresp1)

        if chtype == discord.ChannelType.text:
            ch = await user.guild.create_text_channel(category=getorfetch_channel(ticket_category,user.guild),name=f"ticket-{num}", topic=f"Ticket for {user}",
                                                reason=f"Ticket created by {user}",
                                                overwrites={user: discord.PermissionOverwrite(read_messages=True,send_messages=True)})
        elif chtype == discord.ChannelType.private_thread:
            #ch = await interaction.guild.get_channel(ticket_category).text_channels[0].create_thread(name=f"ticket-{num}",type=discord.ChannelType.private_thread,invitable=False)
            if interaction.channel.category_id == ticket_category:
                ch = await interaction.channel.create_thread(name=f"ticket-{num}",type=discord.ChannelType.private_thread,invitable=False)
        ticket_open_logger.info(f"Ticket #{num} ({str(tickettype).title()}) created by {user} ({user.id}).")
        await ch.send(msg, embed=emb,view=ClaimTicketView())

        async with asqlite.connect("users.db") as conn:
            async with conn.cursor() as cursor:
                now = int(datetime.datetime.now().timestamp())
                await cursor.execute("INSERT INTO Tickets (datelogged, lastupdated, ticket_num, tickettype, userid, username, chid, chtype, claimedby, issolved, transcript) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                        (now, now, num, tickettype.value, user.id, str(user), ch.id, chtype.value, None, False, None))
                await cursor.execute("SELECT * FROM Tickets WHERE userid=?",(user.id,))
                ran = True
                for _ in await cursor.fetchall():
                    ran = False
                    await cursor.execute("UPDATE Tickets SET ticket_num=? WHERE userid=? AND issolved=?",(num, user.id,False))
                    break
                if ran: await cursor.execute("INSERT INTO TicketUsers(datelogged, lastupdated, ticket_num, userid, username) VALUES (?,?,?,?,?)",(now, now, num, user.id, str(user)))
        return ch
    except ValueError:
        raise ValueError("Invalid server name.")
    except Exception as e:
        logger_.warning(traceback.format_exc())
        raise e

async def get_ticket(user: discord.Member=None, num: int=None, chid: int=None, *, cursor: asqlite.Cursor=None) -> dict | None:
    if cursor is None:
        async with asqlite.connect("users.db") as conn:
            async with conn.cursor() as cursor:
                
                if user != None:    await cursor.execute("SELECT * FROM Tickets WHERE creator=? ORDER BY ticket_num DESC",(user.id,))
                elif num != None:   await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(num,))
                elif chid != None:  await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(chid,))

                for row in await cursor.fetchall():
                    row = dict(row)
                    return row
    else:
        if user != None:     await cursor.execute("SELECT * FROM Tickets WHERE creator=? ORDER BY ticket_num DESC",(user.id,))
        elif num != None:    await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(num,))
        elif chid != None:   await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(chid,))

        for row in await cursor.fetchall():
            return dict(row)
    return None

async def get_tickets(user: discord.Member=None, *, cursor: asqlite.Cursor=None) -> list[dict] | None:
    returnv = []
    if cursor is None:
        async with asqlite.connect("users.db") as conn:
            async with conn.cursor() as cursor:
                if user != None: await cursor.execute("SELECT * FROM Tickets WHERE userid=? ORDER BY ticket_num DESC",(user.id,))
                else: await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
                for row in await cursor.fetchall(): returnv.append(dict(row))
    else:
        if user != None: await cursor.execute("SELECT * FROM Tickets WHERE userid=? ORDER BY ticket_num DESC",(user.id,))
        else: await cursor.execute("SELECT * FROM Tickets ORDER BY ticket_num DESC")
        for row in await cursor.fetchall(): returnv.append(dict(row))
    return returnv

async def archive_ticket(user: discord.Member=None, ticket_num: int=None, ticket_ch: discord.TextChannel | discord.Thread=None, cursor: asqlite.Cursor=None) -> bool:
    return await archive_unarchive_ticket(True, user, ticket_num, ticket_ch, cursor)

async def unarchive_ticket(user: discord.Member=None, ticket_num: int=None, ticket_ch: discord.TextChannel | discord.Thread=None, cursor: asqlite.Cursor=None) -> bool:
    #ticket_reopen_logger.info(f"Ticket #{ticket_num} reopened by {user} ({user.id})")
    return await archive_unarchive_ticket(False, user, ticket_num, ticket_ch, cursor)

async def archive_unarchive_ticket(issolved: bool, user: discord.Member=None, ticket_num: int=None, ticket_ch: discord.TextChannel | discord.Thread=None, cursor: asqlite.Cursor=None) -> bool:
    try:
        if cursor != None:
            if user != None:
                print("Not reccomened to use this. TicketType is not taken into account.")
                await cursor.execute("SELECT * FROM Tickets WHERE userid=? AND issolved=?",(user.id,not issolved))
                for row in await cursor.fetchall():
                    row = dict(row)
                    await cursor.execute("UPDATE Tickets SET issolved=? WHERE userid=? AND issolved=?",(not issolved, user.id,issolved))
                    ticket_ch = user.guild.get_channel_or_thread(row["chid"])
                    if type(ticket_ch) == discord.TextChannel:
                        await ticket_ch.move(category=user.guild.get_channel(archived_tickets_category),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                        await ticket_ch.edit(position=user.guild.get_channel(archived_tickets_category).channels.__len__())
                        if issolved: 
                            ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            for user in await ticket_ch.fetch_members():
                                if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                        else: 
                            ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                        return True
                    elif type(ticket_ch) == discord.Thread:
                        await ticket_ch.edit(archived=issolved,locked=issolved)
                        if issolved: 
                            ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            for user in await ticket_ch.fetch_members():
                                if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                        else: 
                            ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                        return True
            elif ticket_num != None:
                await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(ticket_num,))
                for row in await cursor.fetchall():
                    row = dict(row)
                    await cursor.execute("UPDATE Tickets SET issolved=? WHERE ticket_num=?",(issolved, ticket_num,))
                    ticket_ch = await user.guild.get_channel_or_thread(row["chid"])
                    if type(ticket_ch) == discord.TextChannel:
                        await ticket_ch.move(category=user.guild.get_channel(archived_tickets_category),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                        await ticket_ch.edit(position=user.guild.get_channel(archived_tickets_category).channels.__len__())
                        if issolved: 
                            ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            for user in await ticket_ch.fetch_members():
                                if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                        else: 
                            ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                        return True
                    elif type(ticket_ch) == discord.Thread:
                        await ticket_ch.edit(archived=issolved,locked=issolved)
                        if issolved: 
                            ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            for user in await ticket_ch.fetch_members():
                                if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                        else: 
                            ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                        return True
            elif ticket_ch != None:
                await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
                for row in await cursor.fetchall():
                    row = dict(row)
                    await cursor.execute("UPDATE Tickets SET issolved=? WHERE chid=?",(issolved, ticket_ch.id,))
                    ticket_ch = await user.guild.get_channel_or_thread(row["chid"])
                    if type(ticket_ch) == discord.TextChannel:
                        await ticket_ch.move(category=user.guild.get_channel(archived_tickets_category),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                        await ticket_ch.edit(position=user.guild.get_channel(archived_tickets_category).channels.__len__())
                        if issolved: ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {user.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                        else: ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {user.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                        return True
                    elif type(ticket_ch) == discord.Thread:
                        await ticket_ch.edit(archived=issolved,locked=issolved)
                        if issolved: 
                            ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            for user in await ticket_ch.fetch_members():
                                if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                        else: 
                            ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                            await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                        return True  
        else:
            async with asqlite.connect("users.db") as conn:
                async with conn.cursor() as cursor:
                    if user != None:
                        print("Not reccomened to use this. TicketType is not taken into account.")
                        await cursor.execute("SELECT * FROM Tickets WHERE userid=? AND issolved=?",(user.id,not issolved))
                        for row in await cursor.fetchall():
                            row = dict(row)
                            await cursor.execute("UPDATE Tickets SET issolved=? WHERE userid=? AND issolved=?",(not issolved, user.id,issolved))
                            ticket_ch = await user.guild.get_channel_or_thread(row["chid"])
                            if type(ticket_ch) == discord.TextChannel:
                                await ticket_ch.move(category=user.guild.get_channel(archived_tickets_category),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                                await ticket_ch.edit(position=user.guild.get_channel(archived_tickets_category).channels.__len__())
                                if issolved: 
                                    ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    for user in await ticket_ch.fetch_members():
                                        if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                                else: 
                                    ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                                return True
                            elif type(ticket_ch) == discord.Thread:
                                await ticket_ch.edit(archived=issolved,locked=issolved)
                                if issolved: 
                                    ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    for user in await ticket_ch.fetch_members():
                                        if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                                else: 
                                    ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                                return True
                    elif ticket_num != None:
                        await cursor.execute("SELECT * FROM Tickets WHERE ticket_num=?",(ticket_num,))
                        for row in await cursor.fetchall():
                            row = dict(row)
                            await cursor.execute("UPDATE Tickets SET issolved=? WHERE ticket_num=?",(issolved, ticket_num,))
                            ticket_ch = ticket_ch.guild.get_channel_or_thread(row["chid"])
                            if type(ticket_ch) == discord.TextChannel:
                                await ticket_ch.move(category=user.guild.get_channel(archived_tickets_category),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                                await ticket_ch.edit(position=user.guild.get_channel(archived_tickets_category).channels.__len__())
                                if issolved: 
                                    ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    for user in await ticket_ch.fetch_members():
                                        if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                                else: 
                                    ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                                return True
                            elif type(ticket_ch) == discord.Thread:
                                await ticket_ch.edit(archived=issolved,locked=issolved)
                                if issolved: 
                                    ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    for user in await ticket_ch.fetch_members():
                                        if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                                else: 
                                    ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                                return True
                    elif ticket_ch != None:
                        await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
                        for row in await cursor.fetchall():
                            row = dict(row)
                            await cursor.execute("UPDATE Tickets SET issolved=? WHERE chid=?",(issolved, ticket_ch.id,))
                            ticket_ch = ticket_ch.guild.get_channel_or_thread(row["chid"])
                            if type(ticket_ch) == discord.TextChannel:
                                await ticket_ch.move(category=user.guild.get_channel(archived_tickets_category),reason=f"Ticket #{formatticketnum(row['ticket_num'])} deleted by {user}",sync_permissions=True)
                                await ticket_ch.edit(position=user.guild.get_channel(archived_tickets_category).channels.__len__())
                                if issolved: 
                                    ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    for user in await ticket_ch.fetch_members():
                                        if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                                else: 
                                    ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                                return True
                            elif type(ticket_ch) == discord.Thread:
                                await ticket_ch.edit(archived=issolved,locked=issolved)
                                if issolved: 
                                    ticket_close_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} archived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    for user in await ticket_ch.fetch_members():
                                        if user.id not in [me, 514153552789372929]: await ticket_ch.remove_user(user)
                                else: 
                                    ticket_open_logger.info(f"Ticket #{formatticketnum(row['ticket_num'])} unarchived by {ticket_ch.guild.get_member(row.get('claimedby'))} ({row.get('claimedby')}).")
                                    await ticket_ch.add_user(ticket_ch.guild.get_member(row.get('userid')))
                                return True            
        if ticket_ch != None:
            try:
                if issolved:
                    await ticket_ch.remove_user(user)                
                else:
                    await ticket_ch.add_user(user)
            except: pass
    except Exception as e:
        print(e)
        logger_.warning(traceback.format_exc())
        return False

async def save_ticket(ticket_ch: discord.TextChannel | discord.Thread) -> discord.File | None:
    thread_msgs: list[discord.Message] = [msg async for msg in ticket_ch.history(limit=None)]

    authors: list[discord.ThreadMember] = list(set([msg.author for msg in thread_msgs]))
    authors.extend(await ticket_ch.fetch_members())
    for _ in range(1,3):
        for author in authors:
            if type(author) == discord.ThreadMember:
                authors.remove(author)
                authors.append(await getorfetch_user(author.id,ticket_ch.guild))
    
    authors = list(set(authors))

    thread_msgs.reverse()

    try:
        async with asqlite.connect("users.db") as conn:
            async with conn.cursor() as cursor:
                os.chdir("tickets")
                await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
                row = None
                for row in await cursor.fetchall():
                    row = dict(row)
                    break
                os.chdir(f"{TicketType(row['tickettype'])}".lower())
                with open(f"transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt","w") as f:
                    date = ticket_ch.created_at
                    try:
                        date = f"{date.year}-{0 if len(str(date.month)) == 1 else ''}{date.month}-{0 if len(str(date.day)) == 1 else ''}{date.day}"
                    except Exception as e:
                        print(e)
                        logger_.warning(traceback.format_exc())
                    f.write(f"Ticket #{formatticketnum(row.get('ticket_num'))} | {row.get('username')} ({row.get('userid')}) | {date} | {TicketType(row.get('tickettype'))}\n")
                    f.write(f"\nTicket Members:\n")
                    for author in authors:
                        if author.id == row.get('userid'): f.write(f"{author} ({author.id}) (Creator)\n")
                        elif author.id == me: f.write(f"{author} ({author.id}) (Admin)\n")
                        else: f.write(f"{author} ({author.id})\n")
                    f.write(f"\nTranscript:\n")
                    for msg in thread_msgs:
                        dt = datetime.datetime.strftime(msg.created_at, "%Y-%m-%d %H:%M:%S")
                        if len(msg.attachments) > 0:
                            for attachment in msg.attachments:
                                f.write(f"[{dt}] {msg.author}: {attachment.url}\n")
                        else:
                            f.write(f"[{dt}] {msg.author}: {msg.content}\n")
                    f.write(f"\nClosed at {datetime.datetime.fromtimestamp(row.get('lastupdated'))}")
                    f.write(f"\nTranscribed at {datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')}")
                os.chdir("../../")
                await cursor.execute("UPDATE Tickets SET transcript=? WHERE chid=?",(f"tickets/{TicketType(row['tickettype'])}/transcript_ticket-{row.get('ticket_num')}.txt",ticket_ch.id,))
                with open(f"tickets/{TicketType(row['tickettype'])}/transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt","rb") as f:
                    ticket_transcribe_logger.info(f"Ticket #{row.get('ticket_num')} transcribed to transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt.")
                    return discord.File(f, filename=f"transcript_ticket{row.get('ticket_num')}-{row.get('userid')}.txt")
    except:
        return None

async def claim_ticket(ticket_ch: discord.TextChannel | discord.Thread, user: discord.Member) -> bool:
    return await claim_unclaim_ticket(True,ticket_ch,user)

async def unclaim_ticket(ticket_ch: discord.TextChannel | discord.Thread) -> bool:
    return await claim_unclaim_ticket(False,ticket_ch,None)

async def claim_unclaim_ticket(claim: bool, ticket_ch: discord.TextChannel | discord.Thread, user: discord.Member) -> bool:
    try:
        async with asqlite.connect("users.db") as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM Tickets WHERE chid=?",(ticket_ch.id,))
                for row in await cursor.fetchall():
                    row = dict(row)
                    if bool(row.get("issolved")): return False
                    if claim:
                        await cursor.execute("UPDATE Tickets SET claimedby=? WHERE chid=?",(user.id,ticket_ch.id,))
                    else:
                        await cursor.execute("UPDATE Tickets SET claimedby=? WHERE chid=?",(None,ticket_ch.id,))
                    if claim: ticket_claim_logger.info(f"Ticket #{formatticketnum(formatticketnum(row['ticket_num']))} claimed by {user} ({user.id}).")
                    else: ticket_unclaim_logger.info(f"Ticket #{formatticketnum(formatticketnum(row['ticket_num']))} unclaimed by {user} ({user.id}).")
                    return True
    except:
        return False

async def check_user_ticket(user: discord.Member) -> int | None:
    async with asqlite.connect("users.db") as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM Tickets WHERE userid=?",(user.id,))
            for row in await cursor.fetchall():
                if bool(dict(row).get("issolved")): continue
                return dict(row).get("chid")
    return None

class OpenTicketModal(ui.Modal, title='Questionnaire Response'):
    server = ui.TextInput(label='Which server is this issue on?', placeholder='Survival, Creative, Click or NA',required=True)
    issue = ui.TextInput(label='Please detail your issue/inquiry', placeholder='Why are you making this ticket?',required=True)

    def __init__(self,tickettype: TicketType):
        super().__init__()
        self.type = tickettype

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True,ephemeral=True)
        #if t :=await check_user_ticket(interaction.user):
        #    await interaction.followup.send(f"You already have a ticket open. Go here and close it before opening another: <#{t}>",ephemeral=True)
        #    return
        try:
            ch = await create_ticket(interaction, self.type, self.issue.value, self.server.value)
            await interaction.followup.send(f"Sucessfully created {ch.mention}.",ephemeral=True)
        except:
            await interaction.followup.send("An error occured. Make sure you spelled the server correctly in the first question.",ephemeral=True)

class OpenTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_button_press(interaction: discord.Interaction, type: TicketType):
        if t :=await check_user_ticket(interaction.user):
            await interaction.response.send_message(f"You already have a ticket open. Go here and close it before opening another: <#{t}>",ephemeral=True)
            return
        await interaction.response.send_modal(OpenTicketModal(type))

    @discord.ui.button(label='Report a Bug', style=discord.ButtonStyle.gray, custom_id='persistent_view:bug',emoji="🐛")
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await OpenTicketView.on_button_press(interaction, TicketType.BUG)
        
    @discord.ui.button(label='Report a User', style=discord.ButtonStyle.red, custom_id='persistent_view:user',emoji="👤")
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await OpenTicketView.on_button_press(interaction, TicketType.REPORT)


    @discord.ui.button(label='Report a Complaint', style=discord.ButtonStyle.green, custom_id='persistent_view:complaint',emoji="📝")
    async def grey(self, interaction: discord.Interaction, button: discord.ui.Button):
        await OpenTicketView.on_button_press(interaction, TicketType.SUPPORT)
    
    @discord.ui.button(label='Request Role',style=discord.ButtonStyle.blurple, custom_id='persistent_view:role',emoji="👨🏻‍💻")
    async def blurple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await OpenTicketView.on_button_press(interaction, TicketType.ROLE)

class ClaimTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Claim Ticket', style=discord.ButtonStyle.green, custom_id='persistent_view:claim',emoji="📝")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        await claim_ticket(interaction.channel, interaction.user)
        await interaction.followup.send(f"{interaction.user.mention} has claimed this ticket.")
    
    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.red, custom_id='persistent_view:close',emoji="❌")# x emoji
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != me:
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
        if interaction.user.id != self.claimedby and interaction.user.id != me:
            await interaction.response.send_message('You are not the person who claimed this ticket.')
            return
        await interaction.response.defer(thinking=True)
        if (await get_ticket(chid=interaction.channel.id)).get('issolved') == 0:
            #await interaction.channel.remove_user(interaction.guild.get_member(ticket.get('userid')))
            await archive_ticket(ticket_ch=interaction.channel)
            await interaction.followup.send(f"Locked Ticket.")
        self.value = True
        if self.confirm_func != None and self.args != None:
            await self.confirm_func(*self.args)
        elif self.confirm_func != None:
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
        if self.cancel_func != None:
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
        if interaction.user.id != me:
            await interaction.followup.send(f"Hey <@{claimedby}>, {interaction.user.mention} wants to lock this ticket.",view=ConfirmTicketButton(claimedby=claimedby))
        else:
            await archive_ticket(ticket_ch=interaction.channel)
    
    @discord.ui.button(label='Delete Ticket', style=discord.ButtonStyle.red, custom_id='persistent_view:delete_ticket',emoji="🗑️")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        await interaction.followup.send(view=ConfirmButton(func_confirm=interaction.channel.delete,func_cancel=pass_))
    
    @discord.ui.button(label='Save Transcript', style=discord.ButtonStyle.gray, custom_id="persistent_view:save_transcript",emoji="📄")
    async def save_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True,ephemeral=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        file = await save_ticket(interaction.channel)
        await interaction.followup.send(f"Saved Transcript.",ephemeral=True,file=file)
    
    @discord.ui.button(label='Reopen Ticket', style=discord.ButtonStyle.green, custom_id='persistent_view:reopen_ticket',emoji="🔓")
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != me:
            await interaction.followup.send("This command is not for you")
            return
        await unarchive_ticket(ticket_ch=interaction.channel)
        await interaction.followup.send(f"Reopened Ticket.",ephemeral=True)

def formatticketnum(num: int) -> str:
    if len(str(num)) == 1:      return f"00{num}"
    elif len(str(num)) == 2:    return f"0{num}"
    else:                       return str(num)

def _pass_(): pass
async def pass_(): pass

async def setup(bot: discord.ext.commands.Bot):
    bot.add_view(ClaimTicketView())
    bot.add_view(OpenTicketView())
    await bot.add_cog(TicketCog(bot))
