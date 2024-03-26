from __future__ import annotations
from enum import Enum

from typing import Optional, List, Union

import inspect
import os
import re
import traceback
import unicodedata
from attr import has

import discord
from discord.ext import commands
from discord import Emoji, PartialEmoji, app_commands
from tortoise import Tortoise
from cogs.models import MinecraftLinkedUsers

from utils import CogU, ContextU, makeembed, makeembed_bot
from utils.context import BotU
from utils.methods import generic_autocomplete

guilds = [discord.Object(1203186214468063232)]
usernames = []
#AVATAR_URL = "https://crafatar.com/avatars/"
AVATAR_URL = "https://mc-heads.net/avatar/"

async def setup_autocomplete():
    global usernames
    await MinecraftLinkedUsers.all().values_list('minecraft_username',flat=True)
    
async def mcusername_autocomplete(interaction: discord.Interaction, current: str):
    global usernames
    return await generic_autocomplete(current, usernames, interaction)

def is_in_guild():
    async def predicate(ctx: commands.Context):
        if ctx.guild:
            return ctx.guild.id in [x.id for x in guilds]
        return False
    return commands.check(predicate)

class MinecraftType(Enum):
    java = 0
    bedrock = 1

class MinecraftCog(CogU, name='Minecraft'):
    def __init__(self, bot: BotU):
        self.bot = bot

        self.bot.tree.add_command(app_commands.ContextMenu(name='MC Profile', callback=self.profile_ctx_menu, type=discord.enums.AppCommandType.user, guild_ids=[x.id for x in guilds]))
        self.bot.tree.add_command(app_commands.ContextMenu(name='Link Java Account', callback=self.link_java_ctx_menu, type=discord.enums.AppCommandType.message, guild_ids=[x.id for x in guilds]))
        self.bot.tree.add_command(app_commands.ContextMenu(name='Link Bedrock Account', callback=self.link_bedrock_ctx_menu, type=discord.enums.AppCommandType.message, guild_ids=[x.id for x in guilds]))
    

    async def profile_ctx_menu(self, interaction: discord.Interaction, user: discord.User):
        await self.profile(await ContextU.from_interaction(interaction), user)

    @commands.is_owner()
    async def link_java_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        try:
            username = message.content.split(' ')[0]
            await self.link(interaction, message.author, username, MinecraftType.java)
        except:
            traceback.print_exc()

    @commands.is_owner()
    async def link_bedrock_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        username = message.content.split(' ')[0]
        await self.link(interaction, message.author, username, MinecraftType.bedrock)
    
    @commands.is_owner()
    async def unlink_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        await self.unlink(await ContextU.from_interaction(interaction), message.author)

    async def profile(self, ctx: commands.Context, user: Optional[discord.User]=None, mcusername: Optional[str]=None):
        if user == None and mcusername is None: user = ctx.author

        await ctx.defer()

        mcuser = await MinecraftLinkedUsers.filter(discord_id=user.id).first()

        if mcuser is None:
            return await ctx.reply("This user has not linked their MC username to their discord account yet.",ephemeral=True)
        
        returnv: str = f"""<@{mcuser.discord_id}> has linked their MC username to their discord account:"""

        emb = makeembed_bot(f"Requested by @{ctx.author}",thumbnail=f"{AVATAR_URL}{mcuser.minecraft_uuid}" if mcuser.minecraft_uuid else None,description=returnv)
        emb.add_field(name="Discord", value=f"<@{mcuser.discord_id}>")
        emb.add_field(name="Minecraft Username", value=f"`{mcuser.minecraft_username}`")
        emb.add_field(name="Minecraft UUID", value=f"`{mcuser.minecraft_uuid}`")
        emb.add_field(name='Platform', value="Java" if mcuser.isjava else "Bedrock")

        await ctx.reply(embed=emb,ephemeral=True)

    @commands.hybrid_command(name='profile',description="Shows somebody's linked Minecraft profile.")
    @app_commands.autocomplete(mc_username=mcusername_autocomplete)
    @app_commands.guilds(*guilds)
    @is_in_guild()
    async def profile_cmd(self, interaction: commands.Context, user: Optional[discord.User]=None, mc_username: Optional[str]=None):
        await self.profile(interaction,user,mc_username)

    # @commands.command(name='profile',description="Shows somebody's profile.")
    # async def profile_cmd2(ctx: commands.Context, user: discord.User=None):
    #     try:
    #         await profile(ctx,user)
    #     except:
    #         logger_.error(traceback.format_exc())
    
    @commands.hybrid_command(name='link',description="Links your MC username to your discord account.")
    @app_commands.guilds(*guilds)
    @commands.is_owner()
    @is_in_guild()
    async def link_cmd(self, interaction: commands.Context, user: discord.User, mcusername: str):
        await self.link(interaction, user, mcusername)

    @commands.hybrid_command(name='unlink',description="Unlinks your MC username from your discord account.")
    @app_commands.guilds(*guilds)
    @commands.is_owner()
    @is_in_guild()
    async def unlink_cmd(self, interaction: commands.Context, user: discord.User):
        await self.unlink(interaction, user)
    
    async def link(self, interaction: Union[commands.Context, discord.Interaction], user: discord.abc.User, mcusername: str, mctype: MinecraftType=MinecraftType.java):
        if isinstance(interaction, discord.Interaction):
            ctx = await ContextU.from_interaction(interaction)
        else:
            ctx = interaction

        await ctx.defer()

        if await MinecraftLinkedUsers.filter(discord_id=user.id).exists():
            return await ctx.reply("This user has already linked their MC username to their discord account.",ephemeral=True)

        if mctype is MinecraftType.java:
            r = await self._get(f"https://api.mojang.com/users/profiles/minecraft/{mcusername.strip()}")
            if r is None:
                for _ in range(5):
                    r = await self._get(f"https://api.mojang.com/users/profiles/minecraft/{mcusername.strip()}")
                    if r: break

            if r is None:
                return await ctx.reply(f"Hey <@{user.id}>: This is not a valid MC Username. Double check your spelling and try again.")
            
            r = await r.json()

            await MinecraftLinkedUsers.create(
                discord_id=user.id,
                minecraft_uuid=r.get('id'),
                minecraft_username=r.get('name'),
                isjava=True,
                linked_by=user.id
            )

        else:
            await MinecraftLinkedUsers.create(
                discord_id=user.id,
                minecraft_username=mcusername,
                isjava=False,
                linked_by=user.id
            )
        
        emb = makeembed_bot(title='Entered information into database',description=f"Successfully linked the MC username `{r.get('name')}` to <@{user.id}>'s discord account.",thumbnail=f"{AVATAR_URL}{r.get('id')}",)
        await ctx.reply(embed=emb)
        if not isinstance(user, discord.Member): return

        try:
            await user.edit(nick=f"{'.' if mctype is MinecraftType.bedrock else ''}{r.get('name')}")
        except discord.Forbidden:
            pass

    async def unlink(self, interaction: Union[commands.Context, discord.Interaction], user: discord.abc.User):
        if isinstance(interaction, discord.Interaction):
            ctx = await ContextU.from_interaction(interaction)
        else:
            ctx = interaction
        
        await ctx.defer()
        
        if not await MinecraftLinkedUsers.filter(discord_id=user.id).exists():
            return await ctx.reply("This user has not linked their MC username to their discord account yet.",ephemeral=True)

        await MinecraftLinkedUsers.filter(discord_id=user.id).delete()
        emb = makeembed_bot(title='Removed information from database',description=f"Successfully unlinked <@{user.id}>'s discord account from their MC username.",)
        await ctx.reply(embed=emb)


async def setup(bot: BotU):
    await Tortoise.init(config_file='db.yml')
    await Tortoise.generate_schemas()
    await setup_autocomplete()
    await bot.add_cog(MinecraftCog(bot))