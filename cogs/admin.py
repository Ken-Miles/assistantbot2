import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union
import discord
from discord import Activity, ActivityType, AuditLogEntry, app_commands
from discord.abc import Snowflake
from discord.ext import tasks, commands
from utils import CogU, BotU, ContextU, FutureTime, dctimestamp, makeembed_bot, RelativeDelta, emojidict
from cogs.models import Cases
import re

class NoMuteRole(commands.CheckFailure):
    pass

class ModerationActionType(Enum):
    ban = ("ban", discord.AuditLogAction.ban)
    unban = ("unban", discord.AuditLogAction.unban)
    kick = ("kick", discord.AuditLogAction.kick)
    timeout = ("timeout", discord.AuditLogAction.member_update)
    untimeout = ("untimeout", discord.AuditLogAction.member_update)
    mute = timeout
    unmute = untimeout

    # audit log actions
    tempban = ("tempban", discord.AuditLogAction.ban)
    warning = ("warning", None)

    @staticmethod
    def from_str(s: str) -> 'ModerationActionType':
        """Get an enum instance from a string.

        Args:
            s (str): The string to convert.

        Raises:
            ValueError: If the string is not a valid action type.

        Returns:
            ModerationActionType: The action type.
        """        
        s = s.strip().lower()
        for action in __class__:
            if action.value[0] == s: # type: ignore
                return action
        raise ValueError(f"Invalid action type: {s}")
    
    @staticmethod
    def from_audit(a: discord.AuditLogAction) -> 'ModerationActionType':
        """Get an enum instance from a discord.AuditLogAction.

        Args:
            a (discord.AuditLogAction): The action to convert.

        Raises:
            ValueError: If the action is not a valid action type.

        Returns:
            ModerationActionType: The action type.
        """        
        for action in __class__:
            if action.value[1] == a and a is not None: # type: ignore
                return action
        raise ValueError(f"Invalid action type: {a}")
    
    def __str__(self) -> str:
        return self.value[0] # type: ignore

MODERATION_AUDIT_ACTIONS = [
    discord.AuditLogAction.ban,
    discord.AuditLogAction.kick,
    discord.AuditLogAction.unban,
    discord.AuditLogAction.member_prune,
    discord.AuditLogAction.member_update,
]

MODERATION_ACTIONS = [
    ModerationActionType.ban,
    ModerationActionType.kick,
    ModerationActionType.unban,
    ModerationActionType.timeout,
    ModerationActionType.untimeout,
    ModerationActionType.mute,
    ModerationActionType.unmute,
]

REASON_RE = re.compile(r"@?(?P<username>[a-zA-Z0-9]{3,16}) \((?P<id>[0-9]{18,22})\): (?P<reason>.*)")

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

# class SendFlags(commands.commands.FlagConverter, prefix='--', delimiter=' '):
#     dm_reason: Optional[bool] = True
#     reply: Optional[discord.Message] = None

class AdminCog(CogU, name='Admin Comands', hidden=False):
    bot: BotU

    def __init__(self, bot: BotU):
        self.bot = bot
    
    @commands.hybrid_command(name='warn', description='Warn a user', aliases=['w'])
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(
        member="The members to warn",
        #dm_reason="Whether the user should be DMed a reason they were warned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def warn(self, ctx: ContextU, member: MemberID, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
    #async def warn(self, ctx: ContextU, member: MemberID, *, )
        """Warn a member.

        This has the same permissions as the `kick` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.warn_member(ctx, member, anonymous=moderator_anonymous, reason=reason)

    @commands.command(name='multiwarn', description='Warn multiple users', aliases=['mw', 'warns'])
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(
        members="The members to warn",
        #dm_reason="Whether the user should be DMed a reason they were warned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def multiwarn(self, ctx: ContextU, members: commands.Greedy[MemberID], anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Warn multiple members.

        This has the same permissions as the `kick` command.
        """
        await ctx.defer()
        assert ctx.guild is not None
        member_list = [await self.bot.getorfetch_member(x, ctx.guild) for x in members if isinstance(x, int)] + [x for x in members if isinstance(x, discord.Member)]
        moderator_anonymous = anonymous == 'anonymous'
        dm_reason_ = dm_reason == 'dmreason'
        await self.warn_member(ctx, member_list, dm_reason=dm_reason_, anonymous=moderator_anonymous, reason=reason)
    
    async def warn_member(self, ctx: ContextU, member: Union[discord.Member, List[discord.Member]], dm_reason: bool=True, anonymous: bool=False, reason: Optional[str]=None) -> bool:
        """Warn a member.

        Args:
            ctx (ContextU): Context of the command.
            member (discord.Member): The member to warn.
            dm_reason (bool): Whether the user should be DMed the reason they were warned. Defaults to True.
            anonymous (bool): Whether the moderator should be viewable when looking up the case. Defaults to False.
            reason (Optional[str], optional): The reason to show in the audit log. Defaults to None.
        
        Returns:
            bool: Whether the action was successful.
        """

        assert ctx.guild is not None

        if not reason:
            original_reason = "No reason provided."
        else:
            original_reason = reason
        reason = f"{ctx.author} ({ctx.author.id}): {original_reason}."
        
        if isinstance(member, discord.Member):
            members = [member]
        else:
            members = member
        
        if not members:
            emb = makeembed_failedaction(
                description="You must specify a member/members to warn.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False
        
        if any([x == ctx.author for x in members]):
            emb = makeembed_failedaction(
                description="You cannot warn yourself.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        if any([x == ctx.guild.owner for x in members]):
            emb = makeembed_failedaction(
                description="You cannot warn the owner of the server.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        sucessful_warns = []
        failed_warns = []
        for member in members:
            try:
                if dm_reason:
                    moderator = ctx.author.mention if not anonymous else "`The server moderators.`"
                    emb = makeembed_bot(
                        title=f"You have been warned in {ctx.guild.name}.",
                        description=f"You have been warned in {ctx.guild.name}.\n> Reason: `{original_reason}`\nPerformed by: {moderator}\n\nPlease reach out to the server staff if you have any questions or wish to appeal.",
                        color=discord.Color.red(),
                    )
                    try: await member.send(embed=emb)
                    except: pass
                
                await self.on_moderation_action(None, ModerationActionType.warning, member, ctx.author, performed_with_bot=True, anonymous=anonymous, reason=original_reason)
                sucessful_warns.append(member)
            except Exception as e:
                failed_warns.append(member)

        if not failed_warns:
            emb = makeembed_successfulaction(
                description=f"{emojidict.get('warning')} {', '.join([x.mention for x in sucessful_warns]).rstrip(', ')} ha{'ve' if len(sucessful_warns) > 1 else 's'} been warned.",
            )
        elif failed_warns and sucessful_warns:
            emb = makeembed_partialaction(
                description=
                f"""{emojidict.get('warning')} {', '.join([x.mention for x in sucessful_warns]).rstrip(', ')} ha{'ve' if len(sucessful_warns) > 1 else 's'} been warned.
                {emojidict.get('warning')} {', '.join([x.mention for x in failed_warns]).rstrip(', ')} could not be warned.""",
            )
        else:
            emb = makeembed_failedaction(
                description=f"{emojidict.get('warning')} {', '.join([x.mention for x in failed_warns]).rstrip(', ')} could not be warned.",
            )
        await ctx.reply(embed=emb)
        return True

    @commands.hybrid_command(name='mute', description='Mute a user', aliases=['timeout','to', 'm', 'mu', 'silence'])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @can_mute()
    @app_commands.describe(
        member="The person to mute",
        time="The duration for the mute.",
        #dm_reason="Whether the user should be DMed a reason they were muted. Defaults to True.",
        anonymous="Whether the user should see the responsible moderator. Defaults to False.",
        reason="The reason for performing this action. Optional.",
    )
    async def mute(self, ctx: ContextU, member: MemberID, time: FutureTime, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Temporarily mutes a member for the specified duration.

        The duration can be a a short time form, e.g. 30d or a more human
        duration such as "until thursday at 3PM" or a more concrete time
        such as "2024-12-31".

        This has the same permissions as the `mute` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.mute_member(ctx, member, until=time.dt, anonymous=moderator_anonymous, reason=reason)
    
    @commands.command(name='multimute', description='Mute multiple users.', aliases=['mm', 'mutes'])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @can_mute()
    @app_commands.describe(
        members="The members to mute.",
        time="The duration of the mute.",
        #dm_reason="Whether the user should be DMed a reason they were muted. Defaults to True."
        anonymous="Whether the user should see the responsible moderator. Defaults to False.",
        reason="The reason for performing this action. Optional.",
    )
    async def multimute(self, ctx: ContextU, members: commands.Greedy[MemberID], time: FutureTime, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """
        Temporarily mutes multiple members for the specified duration.

        The duration can be a a short time form, e.g. 30d or a more human
        duration such as "until thursday at 3PM" or a more concrete time
        such as "2024-12-31".

        This has the same permissions as the `mute` command.
        """
        await ctx.defer()
        assert ctx.guild is not None
        member_list = [await self.bot.getorfetch_member(x, ctx.guild) for x in members if isinstance(x, int)] + [x for x in members if isinstance(x, discord.Member)]
        moderator_anonymous = anonymous == 'anonymous'
        return await self.mute_member(ctx, member_list, until=time.dt, anonymous=moderator_anonymous, reason=reason)
   
    @commands.hybrid_command(name='unmute', description='Unmute a user', aliases=['um', 'untimeout', 'uto', 'unsilence'])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @can_mute()
    @app_commands.describe(
        member="The members to unmute",
        #dm_reason="Whether the user should be DMed a reason they were unmuted. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def unmute(self, ctx: ContextU, member: MemberID, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Unmutes a member that has been previously muted.

        This has the same permissions as the `mute` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.mute_member(ctx, member, until=None, anonymous=moderator_anonymous, reason=reason)

    @commands.command(name='multiunmute', description='Unmute multiple users', aliases=['mum', 'unmutes'])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @can_mute()
    @app_commands.describe(
        member="The members to unmute",
        #dm_reason="Whether the user should be DMed a reason they were unmuted. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def multiunmute(self, ctx: ContextU, members: commands.Greedy[MemberID], anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Unmutes multiple members that have been previously muted.

        This has the same permissions as the `mute` command.
        """
        await ctx.defer()
        assert ctx.guild is not None
        member_list = [await self.bot.getorfetch_member(x, ctx.guild) for x in members if isinstance(x, int)] + [x for x in members if isinstance(x, discord.Member)]
        moderator_anonymous = anonymous == 'anonymous'
        await self.mute_member(ctx, member_list, None, moderator_anonymous, reason=reason)

    async def mute_member(self, ctx: ContextU, member: Union[discord.Member, List[discord.Member]], until: Optional[datetime.datetime], anonymous: bool=False, reason: Optional[str]=None) -> bool:
        """Mute a member for a specified duration.

        Args:
            ctx (ContextU): Context of the command.
            member (discord.Member): The member to mute.
            until (Optional[datetime.datetime]): How long to mute for. If None, unmute the member.
            anonymous (bool): Whether the moderator should be viewable when looking up the case. Defaults to False.
            reason (Optional[str], optional): The reason to show in the audit log. Defaults to None.

        Returns:
            bool: Whether the action was successful.
        """
        if not reason:
            original_reason = None
            reason = f"{ctx.author} ({ctx.author.id}): No reason provided."
        else:
            original_reason = reason
            reason = f"{ctx.author} ({ctx.author.id}): {reason}"
        
        is_unmute = until is None
        action = ModerationActionType.unmute if is_unmute else ModerationActionType.mute
        action_emoji = emojidict.get(str(action))

        if isinstance(member, discord.Member):
            members = [member]
        else:
            members = member
        
        if not members:
            emb = makeembed_failedaction(
                description="You must specify a member/members to mute.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False
        
        if any([x == ctx.author for x in members]):
            emb = makeembed_failedaction(
                description="You cannot mute yourself.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False
        
        prompt_response = None

        if any([(x.is_timed_out() and x.timed_out_until and until) for x in members]):
            prompt_response = await ctx.prompt(
                f"One or more members are already muted. Would you like to overwrite their mute with the one specified?\n\n{', '.join([x.mention for x in members if x.is_timed_out() and x.timed_out_until and until])}",
                author_id=ctx.author.id,
            )
            if not prompt_response:
                emb = makeembed_failedaction(
                    description="Action cancelled.",
                )
                await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
                return False
        
        if is_unmute:
            action = ModerationActionType.untimeout
        else:
            action = ModerationActionType.timeout

        sucessful_mutes = []
        failed_mutes = []
        for member in members:
            if not member.is_timed_out() and not until:
                # emb = makeembed_failedaction(
                #     description=f"{emojidict.get('warning')} {member.mention} is not muted.",
                # )
                # await ctx.reply(embed=emb)
                # return False
                continue

            case = await self.on_moderation_action(None, action, member, ctx.author, performed_with_bot=True, anonymous=anonymous, reason=original_reason)
            try:
                await member.timeout(until, reason=f"#{case.case_id} {reason}")
                case.sucessful = True
                sucessful_mutes.append(member)
            except Exception as e:
                failed_mutes.append(member)
                case.sucessful = False
            await case.save()

        if not is_unmute:
            if not failed_mutes:
                emb = makeembed_successfulaction(
                    description=f"{action_emoji} {', '.join([x.mention for x in sucessful_mutes]).rstrip(', ')} ha{'ve' if len(sucessful_mutes) > 1 else 's'} been muted until {dctimestamp(until, 'f')}.",
                )
            elif failed_mutes and sucessful_mutes:
                emb = makeembed_partialaction(
                    description=
                    f"""{action_emoji} {', '.join([x.mention for x in sucessful_mutes]).rstrip(', ')} ha{'ve' if len(sucessful_mutes) > 1 else 's'} been muted until {dctimestamp(until, 'f')}.
                    {emojidict.get('warning')} {', '.join([x.mention for x in failed_mutes]).rstrip(', ')} could not be muted.""",
                )
            else:
                emb = makeembed_failedaction(
                    description=f"{emojidict.get('warning')} {', '.join([x.mention for x in failed_mutes]).rstrip(', ')} could not be muted.",
                )
        else:
            if not failed_mutes:
                emb = makeembed_successfulaction(
                    description=f"{action_emoji} {', '.join([x.mention for x in sucessful_mutes]).rstrip(', ')} ha{'ve' if len(sucessful_mutes) > 1 else 's'} been unmuted.",
                )
            elif failed_mutes and sucessful_mutes:
                emb = makeembed_partialaction(
                    description=
                    f"""{action_emoji} {', '.join([x.mention for x in sucessful_mutes]).rstrip(', ')} ha{'ve' if len(sucessful_mutes) > 1 else 's'} been unmuted.
                    {emojidict.get('warning')} {', '.join([x.mention for x in failed_mutes]).rstrip(', ')} could not be unmuted.""",
                )
            else:
                emb = makeembed_failedaction(
                    description=f"{emojidict.get('warning')} {', '.join([x.mention for x in failed_mutes]).rstrip(', ')} could not be unmuted.",
                )
        await ctx.reply(embed=emb)
        return True

    @commands.hybrid_command(name='kick', description='Kick a user', aliases=['k'])
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(
        member="The members to unmute",
       #dm_reason="Whether the user should be DMed a reason they were kicked. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def kick(self, ctx: ContextU, member: discord.Member, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Kick a member from the server.

        This has the same permissions as the `kick` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.kick_member(ctx, member, anonymous=moderator_anonymous, reason=reason)
    
    @commands.command(name='multikick', description='Kick multiple users', aliases=['mk', 'kicks'])
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(
        members="The members to kick",
        #dm_reason="Whether the user should be DMed a reason they were kicked. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def multikick(self, ctx: ContextU, members: commands.Greedy[Union[int, discord.Member]], anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Kick multiple members from the server.

        This has the same permissions as the `kick` command.
        """
        await ctx.defer()
        assert ctx.guild is not None
        member_list = [await self.bot.getorfetch_member(x, ctx.guild) for x in members if isinstance(x, int)] + [x for x in members if isinstance(x, discord.Member)]
        moderator_anonymous = anonymous == 'anonymous'
        await self.kick_member(ctx, member_list, dm_reason=dm_reason, anonymous=moderator_anonymous, reason=reason)

    async def kick_member(self, ctx: ContextU, member: Union[discord.Member, List[discord.Member]], dm_reason: bool=True, anonymous: bool=False, reason: Optional[str]=None) -> bool:
        """Kick a member from the server.

        Args:
            ctx (ContextU): Context of the command.
            member (discord.Member): The member to kick.
            dm_reason (bool): Whether the user should be DMed the reason they were kicked. Defaults to True.
            anonymous (bool): Whether the moderator should be viewable when looking up the case. Defaults to False.
            reason (Optional[str], optional): The reason to show in the audit log. Defaults to None.

        Returns:
            bool: Whether the action was successful.
        """

        assert ctx.guild is not None

        if not reason:
            original_reason = "No reason provided."
        else:
            original_reason = reason
        reason = f"{ctx.author} ({ctx.author.id}): {original_reason}."
        action = ModerationActionType.kick
        action_emoji = emojidict.get(str(action))

        if isinstance(member, discord.Member):
            members = [member]
        else:
            members = member
        
        if not members:
            emb = makeembed_failedaction(
                description="You must specify a member/members to kick.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False
        
        if any([x == ctx.author for x in members]):
            emb = makeembed_failedaction(
                description="You cannot kick yourself.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        if any([x == ctx.guild.owner for x in members]):
            emb = makeembed_failedaction(
                description="You cannot kick the owner of the server.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        sucessful_kicks = []
        failed_kicks = []
        for member in members:
            try:
                if dm_reason:
                    moderator = ctx.author.mention if not anonymous else "`The server moderators.`"
                    emb = makeembed_bot(
                        title=f"You have been kicked from {ctx.guild.name}.",
                        description=f"You have been kicked from {ctx.guild.name}.\n> Reason: `{original_reason}`\nPerformed by: {moderator}\n\nPlease reach out to the server staff if you have any questions or wish to appeal.",
                        color=discord.Color.red(),
                    )
                    try: await member.send(embed=emb)
                    except: pass
                
                await member.kick(reason=reason)
                sucessful_kicks.append(member)
                await self.on_moderation_action(None, action, member, ctx.author, performed_with_bot=True, anonymous=anonymous, reason=original_reason)
            except Exception as e:
                failed_kicks.append(member)

        if not failed_kicks:
            emb = makeembed_successfulaction(
                description=f"{action_emoji} {', '.join([x.mention for x in sucessful_kicks]).rstrip(', ')} ha{'ve' if len(sucessful_kicks) > 1 else 's'} been kicked.",
            )
        elif failed_kicks and sucessful_kicks:
            emb = makeembed_partialaction(
                description=
                f"""{action_emoji} {', '.join([x.mention for x in sucessful_kicks]).rstrip(', ')} ha{'ve' if len(sucessful_kicks) > 1 else 's'} been kicked.
                {emojidict.get('warning')} {', '.join([x.mention for x in failed_kicks]).rstrip(', ')} could not be kicked.""",
            )
        else:
            emb = makeembed_failedaction(
                description=f"{emojidict.get('warning')} {', '.join([x.mention for x in failed_kicks]).rstrip(', ')} could not be kicked.",
            )
        
        await ctx.reply(embed=emb)
        return True
    
    @commands.hybrid_command(name='tempban', description='Temporarily ban a user', aliases=['tb', 'tban'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(
        member="The members to ban",
        time="The duration of the ban.",
        #dm_reason="Whether the user should be DMed a reason they were banned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def tempban(self, ctx: ContextU, member: MemberID, time: FutureTime, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Temporarily ban a member from the server.

        This has the same permissions as the `ban` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.ban_member(ctx, member, dm_reason=dm_reason, anonymous=moderator_anonymous, reason=reason)
    
    @commands.command(name='multitempban', description='Temporarily ban multiple users', aliases=['mtb', 'tbans'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(
        members="The members to ban",
        time="The duration of the ban.",
        #dm_reason="Whether the user should be DMed a reason they were banned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def multitempban(self, ctx: ContextU, members: commands.Greedy[MemberID], time: RelativeDelta, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Temporarily ban multiple members from the server.

        This has the same permissions as the `ban` command.
        """
        await ctx.defer()
        assert ctx.guild is not None
        member_list = [await self.bot.getorfetch_member(x, ctx.guild) for x in members if isinstance(x, int)] + [x for x in members if isinstance(x, discord.Member)]
        moderator_anonymous = anonymous == 'anonymous'
        await self.ban_member(ctx, member_list, duration=time, dm_reason=dm_reason, anonymous=moderator_anonymous, reason=reason)

    @commands.hybrid_command(name='ban', description='Ban a user', aliases=['remove', 'b'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(
        member="The members to ban",
        #dm_reason="Whether the user should be DMed a reason they were banned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def ban(self, ctx: ContextU, member: MemberID, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Ban a member from the server.

        This has the same permissions as the `ban` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.ban_member(ctx, member, dm_reason=dm_reason, anonymous=moderator_anonymous, reason=reason)

    @commands.command(name='multiban', description='Ban multiple users', aliases=['mb', 'bans'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(
        members="The members to ban",
        #dm_reason="Whether the user should be DMed a reason they were banned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def multiban(self, ctx: ContextU, members: commands.Greedy[MemberID], anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Ban multiple members from the server.

        This has the same permissions as the `ban` command.
        """
        await ctx.defer()
        assert ctx.guild is not None
        #member_list = [await self.bot.getorfetch_member(x, ctx.guild) for x in members if isinstance(x, int)] + [x for x in members if isinstance(x, discord.Member)]
        member_list = [x for x in members]
        moderator_anonymous = anonymous == 'anonymous'
        await self.ban_member(ctx, member_list, dm_reason=dm_reason, anonymous=moderator_anonymous, reason=reason)

    async def ban_member(self, ctx: ContextU, member: Union[discord.Member, List[discord.Member]], duration: Optional[datetime.timedelta]=None, dm_reason: bool=True, anonymous: bool=False, reason: Optional[str]=None) -> bool:
        """Ban a member from the server.

        Args:
            ctx (ContextU): Context of the command.
            member (discord.Member): The member to ban.
            duration (Optional[datetime.timedelta]): How long to ban for. If None, permenantly ban the member.
            dm_reason (bool): Whether the user should be DMed the reason they were banned. Defaults to True.
            anonymous (bool): Whether the moderator should be viewable when looking up the case. Defaults to False.
            reason (Optional[str], optional): The reason to show in the audit log. Defaults to None.

        Returns:
            bool: Whether the action was successful.
        """

        assert ctx.guild is not None

        if not reason:
            original_reason = "No reason provided."
        else:
            original_reason = reason
        
        reason = f"{ctx.author} ({ctx.author.id}): {original_reason}."
        action = ModerationActionType.ban if not duration else ModerationActionType.tempban
        action_emoji = emojidict.get(str(action))

        if isinstance(member, discord.Member):
            members = [member]
        else:
            members = member

        if not members:
            emb = makeembed_failedaction(
                description="You must specify a member/members to ban.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False
        
        if any([x == ctx.author for x in members]):
            emb = makeembed_failedaction(
                description="You cannot ban yourself.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        if any([x == ctx.guild.owner for x in members]):
            emb = makeembed_failedaction(
                description="You cannot ban the owner of the server.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        sucessful_bans = []
        failed_bans = []
        for member in members:
            try:
                if dm_reason:
                    moderator = ctx.author.mention if not anonymous else "`The server moderators.`"
                    if duration:
                        now = discord.utils.utcnow()
                        title = f"You have been temporarily banned from {ctx.guild.name}."
                        desc = f"{title.rstrip('.')} until {dctimestamp(now + duration, 'f')} ({dctimestamp(now+duration, 'f')})."
                    else:
                        title = f"You have been permenantly banned from {ctx.guild.name}."
                        desc = title
                    emb = makeembed_bot(
                        title=title,
                        description=f"{desc}\n> Reason: `{original_reason}`\nPerformed by: {moderator}\n\nPlease reach out to the server staff if you have any questions or wish to appeal.",
                        color=discord.Color.red(),
                    )
                    try: await member.send(embed=emb)
                    except: pass
                
                await member.ban(reason=reason)
                sucessful_bans.append(member)
                await self.on_moderation_action(None, action, member, ctx.author, performed_with_bot=True, anonymous=anonymous, reason=original_reason)
            except Exception as e:
                failed_bans.append(member)
        
        if not failed_bans:
            emb = makeembed_successfulaction(
                description=f"{action_emoji} {', '.join([x.mention for x in sucessful_bans]).rstrip(', ')} ha{'ve' if len(sucessful_bans) > 1 else 's'} been {action}ned{' until ' + dctimestamp(discord.utils.utcnow() + duration, 'f') if duration else ''}.",
            )
        elif failed_bans and sucessful_bans:
            emb = makeembed_partialaction(
                description=
                f"""{action_emoji} {', '.join([x.mention for x in sucessful_bans]).rstrip(', ')} ha{'ve' if len(sucessful_bans) > 1 else 's'} been {action}ned{' until ' + dctimestamp(discord.utils.utcnow() + duration, 'f') if duration else ''}.",
                {emojidict.get('warning')} {', '.join([x.mention for x in failed_bans]).rstrip(', ')} could not be {action}ned.""",
            )
        else:
            emb = makeembed_failedaction(
                description=f"{emojidict.get('warning')} {', '.join([x.mention for x in failed_bans]).rstrip(', ')} could not be {action}ned.",
            )
        
        await ctx.reply(embed=emb)
        return True

    @commands.hybrid_command(name='unban', description='Unban a user', aliases=['ub'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(
        member="The member to unban",
        #dm_reason="Whether the user should be DMed a reason they were unbanned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def unban(self, ctx: ContextU, member: MemberID, anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Unban a member from the server.

        This has the same permissions as the `ban` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        await self.unban_member(ctx, member, anonymous=moderator_anonymous, reason=reason)

    @commands.command(name='multiunban', description='Unban multiple users', aliases=['mub', 'unbans'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(
        members="The members to unban",
        #dm_reason="Whether the user should be DMed a reason they were unbanned. Defaults to True.",
        anonymous="Whether the moderator should be made anonymous.",
        reason="The reason for performing this action. Optional.",
    )
    async def multiunban(self, ctx: ContextU, members: commands.Greedy[int], anonymous: Optional[Literal['anonymous']]=None, *, reason: Optional[str] = None):
        """Unban multiple members from the server.

        This has the same permissions as the `ban` command.
        """
        await ctx.defer()
        moderator_anonymous = anonymous == 'anonymous'
        assert ctx.guild is not None
        member_list = [x for x in members]
        await self.unban_member(ctx, member_list, anonymous=moderator_anonymous, reason=reason)

    async def unban_member(self, ctx: ContextU, members: Union[MemberID, List[MemberID]], anonymous: bool=False, reason: Optional[str]=None) -> bool:
        """Unban a member from the server.

        Args:
            ctx (ContextU): Context of the command.
            member (int): The member to unban.
            anonymous (bool): Whether the moderator should be viewable when looking up the case. Defaults to False.
            reason (Optional[str], optional): The reason to show in the audit log. Defaults to None.

        Returns:
            bool: Whether the action was successful.
        """

        assert ctx.guild is not None

        if not reason:
            original_reason = "No reason provided."
        else:
            original_reason = reason
        reason = f"{ctx.author} ({ctx.author.id}): {original_reason}."
        action = ModerationActionType.unban
        action_emoji = emojidict.get(str(action))

        if isinstance(members, int):
            members = [members]
        
        # try:
        #     member = await self.bot.fetch_user(member)
        # except discord.NotFound:
        #     emb = makeembed_failedaction(
        #         description="User not found.",
        #     )
        #     await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
        #     return False
        members: List[Snowflake] = [discord.Object(id=x) for x in members]

        if not members:
            emb = makeembed_failedaction(
                description="You must specify a member to unban.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        if any([x == ctx.author for x in members]):
            emb = makeembed_failedaction(
                description="You cannot unban yourself.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        if any([x == ctx.guild.owner for x in members]):
            emb = makeembed_failedaction(
                description="You cannot unban the owner of the server.",
            )
            await ctx.reply(embed=emb, ephemeral=True, delete_after=10)
            return False

        sucessful_unbans = []
        failed_unbans = []

        for member in members:
            try:
                await ctx.guild.unban(member, reason=reason)
                sucessful_unbans.append(member)
                await self.on_moderation_action(None, action, member, ctx.author, performed_with_bot=True, anonymous=anonymous, reason=original_reason)
            except Exception as e:
                failed_unbans.append(member)

        if not failed_unbans:
            emb = makeembed_successfulaction(
                description=f"{action_emoji} {', '.join([str(x) for x in sucessful_unbans]).rstrip(', ')} ha{'ve' if len(sucessful_unbans) > 1 else 's'} been unbanned.",
            )
        elif failed_unbans and sucessful_unbans:
            emb = makeembed_partialaction(
                description=
                f"""{action_emoji} {', '.join([str(x) for x in sucessful_unbans]).rstrip(', ')} ha{'ve' if len(sucessful_unbans) > 1 else 's'} been unbanned.
                {emojidict.get('warning')} {', '.join([str(x) for x in failed_unbans]).rstrip(', ')} could not be unbanned.""",
            )
        else:
            emb = makeembed_failedaction(
                description=f"{emojidict.get('warning')} {', '.join([str(x) for x in failed_unbans]).rstrip(', ')} could not be unbanned.",
            )
        await ctx.reply(embed=emb)
        return True

    async def on_moderation_action(self,
        audit: Optional[discord.AuditLogEntry], 
        action: ModerationActionType,
        affected_user: discord.abc.User, performing_user: discord.abc.User, 
        performed_with_bot: bool,  anonymous: bool=False, 
        reason: Optional[str]=None,
        action_str: Optional[str]=None) -> Cases:
        """Log a moderation case action to the database.
        Assigns a case ID, saves then returns that case ID.

        Args:
            audit (Optional[discord.AuditLogEntry]): The audit log entry. Null if a global action.
            action (ModerationActionType): The action performed.
            affected_user (discord.abc.User): The affected user. 
            performing_user (discord.abc.User): The moderating user.
            performed_with_bot (bool): Whether the performing_user used the bot to perform the action.
            anonymous (bool, optional): Whether the moderator should show up when the case is looked up. Defaults to False.
            reason (Optional[str]): The reason provided for why this action was performed. Defaults to None.
        """        
        if audit:
            assert not action_str and action
            guild = audit.guild
            assert await Cases.filter(guild_id=guild.id).exists()
            guild_id = guild.id

            action_name = str(action)
        else:
            assert action is not None
            if isinstance(affected_user, discord.Member):
                guild_id = affected_user.guild.id
            else:
                guild_id = 0
            action_name = str(action)
            assert await self.bot.is_owner(performing_user) or performing_user.id == self.bot.user.id, "Only bot owners can perform global actions."

        case_num = await Cases.get_next_case_num(guild_id)

        case = await Cases.create(
            user_id=affected_user.id,
            moderator_id=performing_user.id,
            guild_id=guild_id,
            case_id=case_num,
            performed_with_bot=performed_with_bot,
            action=action_name,
            anonymous=anonymous,
            reason=reason,
            active=True,
        )

        return case

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        if entry.action in MODERATION_AUDIT_ACTIONS and entry.user_id != self.bot.user.id:
            if entry.action is discord.AuditLogAction.member_update:
                # make sure it was a timeout action
                assert isinstance(entry.before, discord.Member) and isinstance(entry.after, discord.Member)
                assert (entry.before.is_timed_out() != entry.after.is_timed_out()) or (entry.before.timed_out_until != entry.after.timed_out_until)
                if entry.before.is_timed_out() and not entry.after.is_timed_out():
                    action = ModerationActionType.untimeout
                #elif not entry.before.is_timed_out() and entry.after.is_timed_out():
                else: # same as ^
                    action = ModerationActionType.timeout
            else:
                action = ModerationActionType.from_audit(entry.action)

            assert entry.target is not None and entry.user is not None
            assert isinstance(entry.target, discord.abc.User)
            #reason = f"{entry.user} ({entry.user_id}): {entry.reason or 'No reason provided.'}"

            await self.on_moderation_action(entry, action, entry.target, entry.user, performed_with_bot=False, anonymous=False, reason=entry.reason)

async def setup(bot: BotU):
    await bot.add_cog(AdminCog(bot))
