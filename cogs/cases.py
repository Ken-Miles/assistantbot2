import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union
import discord
from discord import Activity, ActivityType, AuditLogEntry, app_commands
from discord.abc import Snowflake
from discord.ext import tasks, commands
from utils import CogU, BotU, ContextU, FutureTime, dctimestamp, makeembed_bot
from utils.constants import emojidict
import traceback
from cogs.models import Cases
import re

def can_execute_action(ctx: ContextU, user: discord.Member, target: discord.Member) -> bool:
    return user.id == ctx.bot.owner_id or user == ctx.guild.owner or user.top_role > target.top_role

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
                m = await ctx.bot.getorfetch_member(member_id, ctx.guild)
                if m is None:
                    # hackban case
                    return type('_Hackban', (), {'id': member_id, '__str__': lambda s: f'Member ID {s.id}'})()

        assert isinstance(ctx.author, discord.Member)
        if not can_execute_action(ctx, ctx.author, m):
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

        if not self.bot.is_owner(ctx.author) and ctx.author.id != case.user_id and not ctx.author.guild_permissions.view_audit_log:
            return await ctx.send(embed=makeembed_failedaction('You do not have permission to view this case.', ctx.author))

        if case is None:
            return await ctx.send(embed=makeembed_failedaction('Case not found.', ctx.author))

        emb = makeembed_bot(f"Case {case.case_id}", timestamp=case.created_at)
        affected_user = await self.bot.getorfetch_user(case.user_id, guild=ctx.guild)
        if affected_user is not None:
            emb.add_field(name='Affected Member', value=f"{affected_user} ({affected_user.mention})")
        else:
            emb.add_field(name='Affected Member', value=f'ID {case.user_id} (<@{case.user_id}>)')
        emb.add_field(name='Action', value=case.action)
        emb.add_field(name='Reason', value=case.reason)
        if not case.annonymous:
            emb.add_field(name='Moderator', value=f"<@{case.moderator_id}>")
        
        await ctx.reply(embed=emb)
    
async def setup(bot: BotU):
    await bot.add_cog(CasesCog(bot))
