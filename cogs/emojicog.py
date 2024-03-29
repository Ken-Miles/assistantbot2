from __future__ import annotations

from typing import Union

import asyncio
import traceback
from io import BytesIO

import discord
from discord import app_commands, Interaction, Embed, ui
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext import commands
from PIL import Image

from utils import CogU, ContextU, emojidict, makeembed_bot

class EmojiCog(CogU, name="Emojis"):
    bot: Bot

    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.tree.add_command(app_commands.ContextMenu(name='Convert to Emoji', callback=self.emoji_ctx_menu, type=discord.enums.AppCommandType.message))
    
    def _image_to_emoji(self, image: Union[Image.Image, bytes, BytesIO]) -> BytesIO:
        if isinstance(image, bytes):
            image = BytesIO(image)
        if isinstance(image, BytesIO):
            image = Image.open(image)
        img: Image.Image = image
        img.thumbnail((256, 256),Image.Resampling.LANCZOS)
        b = BytesIO()
        img.save(b,format=image.format)
        b.seek(0)
        return b

    async def image_to_emoji(self, image: Union[Image.Image, bytes, BytesIO, discord.Attachment]) -> BytesIO:
        if isinstance(image, discord.Attachment):
            image = await image.read()
        return await asyncio.to_thread(self._image_to_emoji, image)

    @commands.hybrid_command(name='emoji',description='Convert an image to an emoji.')
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    async def convert_emoji(self, ctx: ContextU, name: str, image: discord.Attachment):
        try:
            await ctx.defer()
            assert ctx.guild is not None
            if not image:
                return await ctx.reply('You must provide an image.')
            if not name or name in [e.name for e in ctx.guild.emojis]:
                return await ctx.reply('You must provide a name that is not already taken.')
            img = await self.image_to_emoji(image)
            e = await ctx.guild.create_custom_emoji(name=name, image=img.getvalue(), reason=f'Emoji created by {ctx.author}.')
            await ctx.reply(f'Emoji created: {e}.')
        except:
            traceback.print_exc()
    
    async def emoji_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        try:
            await interaction.response.defer(thinking=True)
            assert interaction.guild is not None
            assert interaction.user is not None and isinstance(interaction.user, discord.Member)
            assert interaction.channel is not None
            if not interaction.user.guild_permissions.manage_emojis:
                return await interaction.followup.send('You must have the Manage Emojis permission to use this command.')
            if not message.attachments:
                return await interaction.followup.send('There must be an image here.')
            img = await self.image_to_emoji(message.attachments[0])
            if not message.content:
                name = message.attachments[0].filename.split('.')[0]
            else:
                name = message.content
            e = await interaction.guild.create_custom_emoji(name=name[:50], image=img.getvalue(), reason=f'Emoji created by {interaction.user}.')
            await interaction.followup.send(f'Emoji created: {e}.')
        except:
            traceback.print_exc()

    @commands.hybrid_command(name='copy',description='Copy emojis from other servers into your server.')
    @commands.has_permissions(manage_emojis=True)
    @commands.guild_only()
    @commands.is_owner()
    @app_commands.describe(emojis='The emojis you want to copy.')
    async def copy(self, ctx: ContextU, *, emojis: str):
        try:
            await ctx.defer()

            emojis = emojis.strip()
            
            assert ctx.guild is not None

            free_spots = ctx.guild.emoji_limit - len(ctx.guild.emojis)

            if len(emojis.split(' ')) > free_spots:
                return await ctx.reply(f"This server doesn't have enough spots to copy all the emojis provided.")

            returnv: List[Emoji] = []

            for emoji in emojis.strip().split(' '):
                if not (match := EMOJI_REGEX.match(emoji.strip())): break
                try:
                    emoji = PartialEmoji.from_str(emoji.strip())
                except: break

               #print('before')
                newemoji = await ctx.guild.create_custom_emoji(
                    name=emoji.name, 
                    image=await emoji.read(),

                    reason=f'Emoji copied by {ctx.author}'
                )
                #print('after')

                returnv.append(newemoji)
                
            else:
                return await ctx.reply(f"One of the emojis provided was not a valid emoji.")
            
            desc = f'Hey {ctx.author.mention}, I copied the emojis to this guild:\n'

            for emoji in returnv: desc += f'`{emoji}`: {emoji}'
            
            await ctx.reply(desc, ephemeral=True)
        except:
            await ctx.reply(f"```{traceback.format_exc()[:2000]}```",ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmojiCog(bot))