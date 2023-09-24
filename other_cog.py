import discord
from discord import VoiceChannel, app_commands, guild, http
from discord.ext import commands, tasks
from discord.app_commands import Group
from aidenlib.main import makeembed_bot, dchyperlink
import inspect
import os
from main import set_voice_status, token, sessions
from typing import Union

class OtherCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    
    @commands.is_owner()
    @commands.command(name='source',description="Displays my full source code or for a specific command.")
    async def source(self, ctx: commands.Context, *, command: str = None): # type: ignore
        """Displays my full source code or for a specific command.

        To display the source code of a subcommand you can separate it by
        periods, e.g. tag.create for the create subcommand of the tag command
        or by spaces.
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
    
    @commands.command(name='voicestatus',description="Set the voice description for a VC.")
    #@commands.has_permissions(set_voice_channel_status=True)
    #@commands.bot_has_permissions(set_voice_channel_status=True)
    @commands.is_owner()
    async def changevoicestatus(self, ctx: commands.Context, channel: discord.VoiceChannel, *, status: str):
        if ctx.guild is None:
            await ctx.reply("This command cannot be used in DMS.",delete_after=5)
            return
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
