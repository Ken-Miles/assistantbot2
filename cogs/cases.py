import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union
import discord
from discord import Activity, ActivityType, AuditLogEntry, app_commands
from discord.abc import Snowflake
from discord.ext import tasks, commands
from utils import CogU, BotU, ContextU, FutureTime, dctimestamp, makeembed_bot, emojidict
import traceback
from cogs.models import Cases
import re

from utils.paginator import FiveButtonPaginator, create_paginator, generate_pages

def can_execute_action(ctx: ContextU, user: discord.Member, target: discord.Member) -> bool:
    return user.id == ctx.bot.owner_id or user == ctx.guild.owner or user.top_role > target.top_role

def format_case_num(case_id: int) -> str:
    if case_id < 10:
        return f"#000{case_id}"
    elif case_id < 100:
        return f"#00{case_id}"
    elif case_id < 1000:
        return f"#0{case_id}"
    else:
        return f"#{case_id}"

class MemberID(commands.Converter):
    async def convert(self, ctx: ContextU, argument: str): # type: ignore
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
            else:
                assert ctx.guild is not None
                m = await ctx.bot.getorfetch_user(member_id, ctx.guild)
                if m is None:
                    # hackban case
                    return type('_Hackban', (), {'id': member_id, '__str__': lambda s: f'Member ID {s.id}'})()

        assert isinstance(ctx.author, discord.Member)
        if isinstance(m, discord.Member) and not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')
        return m

def can_mute():
    async def predicate(ctx: ContextU) -> bool:
        is_owner = await ctx.bot.is_owner(ctx.author)
        if ctx.guild is None or isinstance(ctx.author, discord.User):
            return False

        if not ctx.author.guild_permissions.manage_roles and not is_owner:
            return False

        return True
    return commands.check(predicate)

def makeembed_failedaction(*args, **kwargs):
    kwargs['title'] = kwargs.get('title', 'Action Failed')
    kwargs['color'] = kwargs.get('color', discord.Color.brand_red())
    emb = makeembed_bot(*args, **kwargs)
    return emb

def makeembed_partialaction(*args, **kwargs):
    kwargs['title'] = kwargs.get('title', 'Action Partially Successful')
    kwargs['color'] = kwargs.get('color', discord.Color.gold())
    emb = makeembed_bot(*args, **kwargs)
    return emb

def makeembed_successfulaction(*args, **kwargs):
    kwargs['title'] = kwargs.get('title', 'Action Successful')
    emb = makeembed_bot(*args, **kwargs)
    return emb

class CasesCog(CogU, name='Admin Case Comands', hidden=False):
    bot: BotU

    def __init__(self, bot: BotU):
        self.bot = bot
    
    @commands.command(name='case', aliases=['c'])
    @commands.guild_only()
    async def case(self, ctx: ContextU, case_id: int):
        """Get information about a case"""
        await ctx.defer()

        case = await Cases.filter(guild_id=ctx.guild.id, case_id=case_id).first()

        if not await self.bot.is_owner(ctx.author) and ctx.author.id != case.user_id and not ctx.author.guild_permissions.view_audit_log:
            return await ctx.send(embed=makeembed_failedaction('You do not have permission to view this case.', ctx.author))

        if case is None:
            return await ctx.send(embed=makeembed_failedaction('Case not found.', ctx.author))

        affected_user = await self.bot.getorfetch_user(case.user_id, guild=ctx.guild)
        if affected_user is None:
            emb = makeembed_bot(timestamp=case.created_at, author=f'User {case.user_id}')
        else:
            emb = makeembed_bot(timestamp=case.created_at, author=affected_user.name, author_icon_url=affected_user.avatar.url)
        
        emb.add_field(name='Case Number', value=format_case_num(case.case_id),inline=False)
        if affected_user is not None:
            emb.add_field(name='Affected Member', value=f"{affected_user} ({affected_user.mention})", inline=False)
        else:
            emb.add_field(name='Affected Member', value=f'ID {case.user_id} (<@{case.user_id}>)', inline=False)
        emb.add_field(name='Action', value=f"{emojidict.get(case.action)} {case.action}", inline=False)
        emb.add_field(name='Reason', value=case.reason, inline=False)
        if not case.annonymous:
            emb.add_field(name='Moderator', value=f"<@{case.moderator_id}>")
        
        return await ctx.reply(embed=emb)

    @commands.command(name='cases', aliases=['cs'])
    @commands.guild_only()
    async def cases(self, ctx: ContextU, member: MemberID):
        """Get all cases for a member"""
        await ctx.defer()

        cases = await Cases.filter(guild_id=ctx.guild.id, user_id=member.id)

        if not cases:
            return await ctx.send(embed=makeembed_failedaction('No cases found for this user.', ctx.author))

        if not await self.bot.is_owner(ctx.author) and ctx.author.id != member.id and not ctx.author.guild_permissions.view_audit_log:
            return await ctx.send(embed=makeembed_failedaction('You do not have permission to view this user\'s cases.', ctx.author))

        pages = []        
        desc = ''
        for case in cases:
            desc = f"{emojidict.get(case.action)} {format_case_num(case.case_id)} - {case.action}\n\- `{case.reason}`"
            pages.append(desc)
            desc = ''
        
        items_on_page = 0
        items_per_page = None
        tr = 0
        pagenum = 0

        embeds = []

        for item in pages:
            tr += 1

            if (items_per_page and items_on_page == items_per_page) or (not items_per_page and len(desc)+len(str(item)) > 2000):
                pagenum += 1
                items_on_page = 0

                emb = makeembed_bot(
                    author=str(member),
                    author_icon_url=member.avatar.url,
                    description=desc
                )
                embeds.append(emb)
                desc = ''

            desc += str(item)+'\n'
            items_on_page += 1
        
        if desc:
            pagenum += 1
            emb = makeembed_bot(
                    author=str(member),
                    author_icon_url=member.avatar.url,
                    description=desc
                )
            embeds.append(emb)
        
        for embed in embeds:
            if not embed.footer or not embed.footer.text:
                continue
            if ' | page' in embed.footer.text.lower():
                footer = embed.footer.text[embed.footer.text.lower().find(' | page'):]
            else:
                footer = f"{embed.footer.text.strip()} | Page {embeds.index(embed)+1}/{len(embeds)}"
            embed.set_footer(text=footer)

        return await create_paginator(ctx, embeds, FiveButtonPaginator, author_id=ctx.author.id, timeout=300, delete_message_after=True)

async def setup(bot: BotU):
    await bot.add_cog(CasesCog(bot))
