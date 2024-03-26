from __future__ import annotations

from re import S
import traceback
from typing import Optional, Sequence, Union

import discord
from discord import ForumChannel, ForumTag, app_commands
from discord.ext import commands

from utils import CogU, ContextU, generic_autocomplete, emojidict
from utils.context import BotU

SOLVED_TAGS = ["Solved", "Completed", "Sold", "Closed", "Approved", "Implemented"]
SOLVED_TAGS_LOWER = [x.lower() for x in SOLVED_TAGS]

async def solved_autocomplete(interaction: discord.Interaction, current: str):
    return await generic_autocomplete(current, SOLVED_TAGS_LOWER, interaction)

def is_help_thread():
    async def predicate(ctx: ContextU):
        if isinstance(ctx.channel, discord.Thread):
            if isinstance(ctx.channel.parent, ForumChannel):
                return True
        return False
    return commands.check(predicate)

def can_close_threads(ctx: ContextU) -> bool:
    if not isinstance(ctx.channel, discord.Thread):
        return False

    if not isinstance(ctx.author, discord.Member):
        return False

    permissions = ctx.channel.permissions_for(ctx.author)

    return isinstance(ctx.channel.parent, ForumChannel) and (
        permissions.manage_threads or ctx.channel.owner_id == ctx.author.id
    )

async def find_solved_tag(tags: Sequence[discord.ForumTag]) -> Optional[discord.ForumTag]:
    for tag in tags:
        if tag.name.lower().strip() in SOLVED_TAGS_LOWER:
            return tag
    return None

class ForumCog(CogU, name="Forums"):
    def __init__(self, bot: BotU):
        self.bot: BotU = bot

    async def mark_as_solved(self, thread: discord.Thread, user: discord.abc.User) -> None:
        tags: Sequence[ForumTag] = thread.applied_tags

        solved_tag = await find_solved_tag(tags)

        if solved_tag and solved_tag not in tags:
            tags = [solved_tag] + tags[:4]

        await thread.edit(
            locked=True,
            archived=True,
            applied_tags=tags[:5],
            reason=f'Marked as solved by {user} (ID: {user.id})',
        )
    
    async def mark_as_unsolved(self, thread: discord.Thread, user: discord.abc.User) -> None:
        tags: Sequence[ForumTag] = thread.applied_tags

        solved_tag = await find_solved_tag(tags)

        if solved_tag:
            tags.remove(solved_tag)

        await thread.edit(
            locked=False,
            archived=False,
            applied_tags=tags[:5],
            reason=f'Marked as unsolved by {user} (ID: {user.id})',
        )

    @commands.command(name='solved', aliases=['is_solved'])
    @commands.guild_only()
    @commands.cooldown(1, 20, commands.BucketType.channel)
    @is_help_thread()
    async def solved_2(self, ctx: ContextU):
        """Marks a thread as solved."""
        await ctx.defer()

        assert isinstance(ctx.channel, discord.Thread)

        if can_close_threads(ctx) and ctx.invoked_with == 'solved':
            await ctx.message.add_reaction(str(emojidict.get(True)))
            await ctx.send("This thread has been marked as solved/sold. If you need to reopen it, please contact a moderator.")
            await self.mark_as_solved(ctx.channel, ctx.author)
        else:
            msg = f"<@{ctx.channel.owner_id}>, would you like to mark this thread as solved? This has been requested by {ctx.author.mention}."
            confirm = await ctx.prompt(msg, author_id=ctx.channel.owner_id, timeout=300.0)

            if ctx.channel.locked:
                return

            if confirm:
                await ctx.send(
                    f'Marking as solved. Note that next time, you can mark the thread as solved yourself with `?solved`.'
                )
                await ctx.send("This thread has been marked as solved/sold. If you need to reopen it, please contact a moderator.")
                await self.mark_as_solved(ctx.channel, ctx.channel.owner or ctx.author)
            elif confirm is None:
                await ctx.send('Timed out waiting for a response. Not marking as solved.')
            else:
                await ctx.send('Not marking as solved.')

    @commands.Cog.listener() # this means its an event when the a post is made in a forum channel
    async def on_thread_create(self, thread: discord.Thread): # this is the function that runs when a post is made in a forum channel
        assert thread.guild is not None
        if isinstance(thread, discord.Thread) and isinstance(thread.parent, ForumChannel):
            try:
                starter_message = thread.starter_message
                if not starter_message:
                    starter_message = [x async for x in thread.history(limit=1, oldest_first=True)][0]
                await starter_message.pin(reason=f'Thread opened by {thread.owner}, automatic pin.')
            except:
                pass
    
    @commands.command(name='unsolved', aliases=['is_unsolved'])
    @commands.guild_only()
    @commands.cooldown(1, 20, commands.BucketType.channel)
    @is_help_thread()
    async def unsolved(self, ctx: ContextU):
        await ctx.defer()

        assert isinstance(ctx.channel, discord.Thread)

        if can_close_threads(ctx) and ctx.invoked_with == 'unsolved':
            await ctx.message.add_reaction(str(emojidict.get(True)))
            await ctx.reply("This thread has been marked as unsolved.")
            await self.mark_as_unsolved(ctx.channel, ctx.author)
        else:
            msg = f"<@{ctx.channel.owner_id}>, would you like to mark this thread as unsolved? This has been requested by {ctx.author.mention}."
            confirm = await ctx.prompt(msg, author_id=ctx.channel.owner_id, timeout=300.0)

            if ctx.channel.locked:
                return

            if confirm:
                await ctx.reply(
                    f'Marking as unsolved. Note that next time, you can mark the thread as unsolved yourself with `?unsolved`.'
                )
                await self.mark_as_unsolved(ctx.channel, ctx.channel.owner or ctx.author)
            elif confirm is None:
                await ctx.reply('Timed out waiting for a response. Not marking as unsolved.')
            else:
                await ctx.reply('Not marking as unsolved.')

async def setup(bot):
    await bot.add_cog(ForumCog(bot)) # adds the cog to the bot
