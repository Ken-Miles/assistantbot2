import discord
from discord.ext import commands
from discord import app_commands
import inspect
import os
from main import set_voice_status
import unicodedata
from typing import Optional


class OtherCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    
    @commands.command(name='source',description="Displays my full source code or for a specific command.")
    @commands.is_owner()
    @app_commands.describe(command="The command to get the source code for.")
    async def source(self, ctx: commands.Context, *, command: Optional[str] = None): # type: ignore
        """Displays my full source code or for a specific command.

        To display the source code of a subcommand you can separate it by
        periods, e.g. tag.create for the create subcommand of the tag command
        or by spaces.

        Original command written by @danny on Discord. 
        Found at https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/meta.py#L404-L445. 
        """
        source_url = "https://github.com/Ken-Miles/assistantbot2"
        branch = "main"

        if command is None:
            return await ctx.reply(source_url)
        
        if command == "help":
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                return await ctx.reply('Could not find command.')

            # since we found the command we're looking for, presumably anyway, let's
            # try to access the code itself
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename
        
        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            if filename is None:
                return await ctx.reply('Could not find source for command.')

            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            source_url = "https://github.com/Ken-Miles/assistantbot2"
            branch = "main"

        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.reply(final_url)
    
    @commands.hybrid_command(name='charinfo',description="Shows you information about a number of characters.")
    @commands.is_owner()
    @app_commands.describe(characters="The characters to get information about.")
    async def charinfo(self, ctx: commands.Context, *, characters: str):
        """Shows you information about a number of characters.

        Only up to 25 characters at a time.

        Original command written by @danny on Discord. Slight modifications by me.
        Found at https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/meta.py#L298-L313. 
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.reply('Output too long to display.')
        await ctx.reply(msg,ephemeral=True)

    @commands.command(name='voicestatus',description="Set the voice description for a VC.")
    #@commands.has_permissions(set_voice_channel_status=True)
    #@commands.bot_has_permissions(set_voice_channel_status=True)
    @commands.is_owner()
    @app_commands.describe(channel="The voice channel to set the status for.", status="The status to set. Leave empty to remove status.")
    async def changevoicestatus(self, ctx: commands.Context, channel: discord.VoiceChannel, *, status: str):
        await ctx.defer()
        status = status.replace('""',"")
        try:
            code = await set_voice_status(channel, status, [self.bot.session, self.bot.session2, self.bot.session3])
            if status != "":
                await ctx.reply(f"Changed status of {channel.mention} to `{status}`{f' (code {code})' if code != 204 else ''}.")
            else:
                await ctx.reply(f"Removed status of {channel.mention}{f' (code {code})' if code != 204 else ''}.")
        except Exception as e:
            await ctx.reply(f"Error: {e}",delete_after=5)
            return

async def setup(bot):
    await bot.add_cog(OtherCog(bot))
