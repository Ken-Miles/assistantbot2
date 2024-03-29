from __future__ import annotations

import sys
import time
import traceback

from utils import CogU, ContextU, dctimestamp, BotU

from discord.ext import commands

class ErrorHandler(CogU, hidden=True):
    bot: BotU

    def __init__(self, bot: BotU):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: ContextU, error: commands.CommandError):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        #kwargs = {'ephemeral': True, 'delete_after': 10.0 if not ctx.interaction else None}
        kwargs = {}

        message = None

        reply_method = ctx.reply

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.reply(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            reply_method = ctx.author.send
            kwargs = {}
            message = f'{ctx.command} can not be used in Private Messages.'
        
        elif isinstance(error, commands.MissingPermissions):
            message = f"You are missing the following permissions: {', '.join(error.missing_permissions)}"
        
        elif isinstance(error, commands.BotMissingPermissions):
            message = f"I am missing the following permissions: {', '.join(error.missing_permissions)}"
        
        elif isinstance(error, commands.NotOwner):
            message = "You must be the owner of this bot to use this command."

        elif isinstance(error, commands.BadArgument):
            message = 'Invalid argument. Please try again.'

        elif isinstance(error, commands.CommandOnCooldown):
            message = f"This command is on cooldown. Please try again {dctimestamp(int(time.time()+error.retry_after)+1,'R')}."
        
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"Missing required argument: `{error.param.name}`"
        
        elif isinstance(error, commands.TooManyArguments):
            message = f"Too many arguments. Please try again."
        
        elif isinstance(error, commands.CheckFailure):
            message = f"The check for this command failed. You most likely do not have permission to use this command or are using it in the wrong channel."
        
        elif isinstance(error, commands.CommandInvokeError):
            message = f"An error occured while running this command. Please try again later."
            traceback.print_exc()
        
        # verification errors
        # elif isinstance(error, NotLinked):
        #     message = 'You need to have your roblox account linked to do this..'
        # elif isinstance(error, AlreadyLinked):
        #     message = 'You already have your roblox account linked.'

        else:
            # All other Errors not returned come here. And we can just print the default TraceBack.
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        
        if reply_method == ctx.reply: kwargs = {'ephemeral': True}
        try: await reply_method(message,**kwargs)
        except: pass


    # @commands.Cog.listener()
    # async def on_command_error(self, ctx: ContextU, error: Union[commands.CommandError, Exception]):
    #     ignored = (commands.CommandNotFound, commands.UserInputError)
    #     delete_after = (10.0 if not ctx.interaction else None)
    #     kwargs = {'ephemeral': True, 'delete_after': delete_after}
    #     if isinstance(error, ignored): return
    #     elif isinstance(error, commands.CommandInvokeError):
    #         traceback.print_exc()
    #     elif isinstance(error, InvalidUsernameException):
    #         await ctx.reply("Please enter a valid roblox username.")
    #     elif isinstance(error, commands.CommandOnCooldown):
    #         await ctx.reply(f"Command is on cooldown. Try again {dctimestamp(int(round(error.retry_after+time.time()+1)), 'R')}.",**kwargs)
    #     elif isinstance(error, commands.NotOwner):
    #         await ctx.reply("You're not my father (well creator...)",**kwargs)
    #     else:
    #         await ctx.reply(str(error),**kwargs)
    #         traceback.print_exc()

    #  @commands.Cog.listener()
    #     async def on_command_error(self, ctx: commands.Context, error: Union[commands.CommandError, Exception]):
    #         ignored = (commands.CommandNotFound, commands.UserInputError)
    #         delete_after = (10.0 if not ctx.interaction else None)
    #         kwargs = {'ephemeral': True, 'delete_after': delete_after}
    #         if isinstance(error, ignored): return
    #         elif isinstance(error, commands.CommandInvokeError):
    #             worker_important_logger.warning(traceback.format_exc())
    #         elif isinstance(error, InvalidUsernameException):
    #             await ctx.reply("Please enter a valid roblox username.")
    #         elif isinstance(error, commands.CommandOnCooldown):
    #             await ctx.reply(f"Command is on cooldown. Try again {dctimestamp(int(round(error.retry_after+time.time())), 'R')}.",**kwargs)
    #         elif isinstance(error, commands.NotOwner):
    #             await ctx.reply("You're not my father (well creator...)",**kwargs)
    #         else:
    #             await ctx.reply(str(error),**kwargs)
    #             worker_important_logger.warning(traceback.format_exc())

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
