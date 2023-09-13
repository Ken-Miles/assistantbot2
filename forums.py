import discord
from discord import app_commands, ui
from discord.app_commands import Group
from discord.ext import commands, tasks
import traceback
from main import logger_forums, me

new_town_ideas = 1130364285491626055
town_jobs = 1130366266247491654
suggestions = 1130644472657608755
auction_house = 1132321569427947730
shops = 1137651359978623066
mc_suggestions = 1133889335637311578
snugmc_suggestions = 1133889335637311578
clickmc_suggestions = 1135604021424566292
bot_suggestions = 1147018651862573116
solvable = [new_town_ideas, town_jobs, auction_house, mc_suggestions, shops, bot_suggestions]



async def solved_autocomplete(interaction: discord.Interaction, current: str):
    if interaction.user.id == me:
        exact_matches = []
        other_matches = []
        not_matches = []
        current = current.lower().strip()
        solved_tags = ["Solved", "Completed", "Sold", "Closed", "Approved", "Implemented"]
        solved_tags2 = []
        for tag in solved_tags: solved_tags2.append(tag.lower().strip())

        for tag in interaction.channel.parent.available_tags:
            tag_ = tag
            tag = tag.name.lower().strip()
            if tag.startswith(current.lower()):
                exact_matches.append(app_commands.Choice(name=tag, value=tag_))
            elif current.lower() in tag_:
                other_matches.append(app_commands.Choice(name=tag, value=tag_))
            else: not_matches.append(app_commands.Choice(name=tag, value=tag_))

            if len(exact_matches) + len(other_matches) >= 25:
                break
        
        exact_matches.extend(other_matches)
        exact_matches.extend(not_matches)

        return exact_matches



class ForumCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # @commands.command(name='solved',description="Mark a thread as solved.")
    # async def solved_cmd(self, interaction: discord.Interaction, ch: discord.Thread=None):
    #     if ch is None: ch = interaction.channel
    #     await interaction.response.defer(thinking=True)
        
    #     if type(ch) != discord.Thread:
    #         print(type(ch))
    #         await interaction.followup.send("This command can only be used in a thread.")
    #         return
        
    #     if ch.guild.id == 1122231942453141565:
    #         if ch.parent_id not in solvable:
    #             await interaction.followup.send(f"This command can only be used in a thread in <#{new_town_ideas}>, <#{town_jobs}>, <#{auction_house}>, <#{mc_suggestions}> or <#{shops}>..")
    #             return            
            
    #         if ch.owner_id != interaction.user.id and interaction.user.id != me:
    #             await interaction.followup.send("You are not the owner of this thread.")
    #             return
    #         try:
    #             await self.solved(ch, interaction)
    #         except:
    #             traceback.print_exc()

    @commands.hybrid_command(name='solved',description="Marks a thread as solved.",hidden=True,guilds=[discord.Object(x) for x in [1135603095385153696,1133473132418699366]])
    @app_commands.guilds(1133473132418699366,1029151630215618600)
    @app_commands.autocomplete(tag=solved_autocomplete)
    async def solved_cmd2(self, ctx: commands.Context, ch: discord.Thread=None, tag: str=None):
        if ch is None: ch = ctx.channel
        if type(ch) != discord.Thread:
            await ctx.reply("This command can only be used in a thread.")
            return

        #await ctx.message.add_reaction(emojidict.get("check"))
        await ctx.defer()

        if ch.guild.id == 1122231942453141565:

            if ch.parent_id not in solvable:
                await ctx.reply(f"This command can only be used in a thread in <#{new_town_ideas}>, <#{town_jobs}>, <#{auction_house}>, <#{mc_suggestions}> or <#{shops}>..")
                return            
            
            if ch.owner_id != ctx.author.id and ctx.author.id != me:
                await ctx.reply("You are not the owner of this thread.")
                return
            try:
                await self.solved(ch, ctx, tag)
            except:
                traceback.print_exc()

    async def solved(self, ch: discord.Thread, ctx: commands.Context | discord.Interaction=None, tag_: str=None):
       #await ctx.defer()

        if ch.guild.id == 1122231942453141565:
            
            new_town_ideas = 1130364285491626055
            town_jobs = 1130366266247491654
            suggestions = 1130644472657608755
            auction_house = 1132321569427947730
            snugmc_suggestions = 1133889335637311578
            clickmc_suggestions = 1135604021424566292
            bot_suggestions = 1147018651862573116
        #if type(ctx) == commands.Context:
            #await ctx.reply("Marking this thread as solved...")
        solved_tag = None
        for tag in ch.parent.available_tags:
            if tag_ != None:
                if tag.name.lower().strip() == tag_.lower().strip():
                    solved_tag = tag
                    break
            elif tag.name in ["Solved", "Completed", "Sold", "Closed", "Approved", "Implemented"]:
                solved_tag = tag
                break

        # if ch.parent_id == new_town_ideas:
        #     await ch.add_tags(solved_tag)
        # elif ch.parent_id == town_jobs:
        #     await ch.add_tags(solved_tag)
        # elif ch.parent_id == auction_house:
        #     await ch.add_tags(solved_tag)
        await ch.add_tags(solved_tag)
    
        if ctx.channel != ch:
            await ctx.reply(f"Marked {ch.mention} as solved/sold.")
            await ch.send("This thread has been marked as solved/sold. If you need to reopen it, please contact a moderator.")
        else:
            await ctx.reply("This thread has been marked as solved/sold. If you need to reopen it, please contact a moderator.")
        if type(ctx) == commands.Context:
            await ch.edit(archived=True, locked=True, reason=f"Thread marked as solved/sold by {ctx.author}")
        else:
            await ch.edit(archived=True, locked=True, reason=f"Thread marked as solved/sold by {self.bot.user}",)

        logger_forums.info(f"Thread {ch.name} ({ch.id}) marked as solved/sold by {ctx.author} in {ch.parent.name} ({ch.parent.id})")

    # @commands.command(name='unsolved',description='Unmarks a thread as solved.')
    # async def unsolved_cmd2(self, interaction: discord.Interaction, ch: discord.Thread=None):
    #     if ch is None: ch = interaction.channel
    #     await interaction.response.defer(thinking=True)
    #     if type(ch) != discord.Thread:
    #         await interaction.followup.send("This command can only be used in a thread.")
    #         return
    #     if interaction.user.id != me:
    #         await interaction.followup.send("This command is not for you.")
    #         return
        
    #     if ch.guild.id == 1122231942453141565:
    #         if ch.parent_id not in [new_town_ideas, town_jobs, auction_house, snugmc_suggestions, clickmc_suggestions]:
    #             await interaction.followup.send(f"This command can only be used in a thread in <#{new_town_ideas}>, <#{town_jobs}>, <#{auction_house}>, <#{snugmc_suggestions}> or <#{clickmc_suggestions}>.")
    #             return            
            
    #         if ch.owner_id != interaction.user.id and interaction.user.id != me:
    #             await interaction.followup.send("You are not the owner of this thread.")
    #             return
    #         try:
    #             await self.unsolved(ch, interaction)
    #         except:
    #             traceback.print_exc()

    @commands.hybrid_command(name='unsolved',description="Unmarks a thread as solved.",hidden=True,guilds=[discord.Object(x) for x in [1135603095385153696,1133473132418699366]])
    @app_commands.guilds(1133473132418699366,1029151630215618600)
    async def unsolved_cmd(self, ctx: commands.Context, ch: discord.Thread=None):
        if ch is None: ch = ctx.channel
        if type(ch) != discord.Thread:
            await ctx.send("This command can only be used in a thread.")
            return
        if ctx.author.id != me:
            await ctx.send("This command is not for you.")
            return
        
        #await ctx.message.add_reaction(emojidict.get("check"))
        await ctx.defer()
        
        if ch.guild.id == 1122231942453141565:
            new_town_ideas = 1130364285491626055
            town_jobs = 1130366266247491654
            suggestions = 1130644472657608755
            auction_house = 1132321569427947730
            mc_suggestions = 1133889335637311578

            if ch.parent_id not in solvable:
                await ctx.send(f"This command can only be used in a thread in <#{new_town_ideas}>, <#{town_jobs}>, <#{auction_house}>, <#{mc_suggestions}> or <#{shops}>..")
                return            
            
            if ch.owner_id != ctx.author.id and ctx.author.id != me:
                await ctx.send("You are not the owner of this thread.")
                return
            try:
                await self.unsolved(ch, ctx)
            except:
                traceback.print_exc()

    async def unsolved(self, ch: discord.Thread, ctx: commands.Context | discord.Interaction=None):
        #if ch.guild.id == 1122231942453141565:


        #if type(ctx) == commands.Context:
        #    await ctx.message.reply("Marking this thread as unsolved...")
        solved_tag = None
        for tag in ch.parent.available_tags:
            if tag.name in ["Solved", "Completed", "Sold", "Closed"]:
                solved_tag = tag
                break
        # if ch.parent_id == new_town_ideas:
        #     await ch.remove_tags(solved_tag)
        # elif ch.parent_id == town_jobs:
        #     await ch.remove_tags(solved_tag)
        # elif ch.parent_id == auction_house:
        #     await ch.remove_tags(solved_tag)
        await ch.remove_tags(solved_tag)
        if type(ctx) == discord.Interaction:
            if ctx.channel != ch:
                await ctx.followup.send(f"Unmarked {ch.mention} as solved/sold.")
                await ch.send("This thread has been unmarked as solved/sold.")
            else:
                await ctx.followup.send(f"This thread has been unmarked as solved/sold.")
        else:
            if ctx != None:
                if ctx.channel != ch:
                    await ctx.send(f"Unmarked {ch.mention} as solved/sold.")
                await ch.send("This thread has been unmarked as solved/sold.")
        if type(ctx) == commands.Context:
            await ch.edit(archived=False, locked=False, reason=f"Thread marked as unsolved/sold by {ctx.author}")
        elif type(ctx) == discord.Interaction:
            await ch.edit(archived=False, locked=False, reason=f"Thread marked as unsolved/sold by {ctx.user}")
        else:
            await ch.edit(archived=False, locked=False, reason=f"Thread marked as unsolved/sold by {self.bot.user}",)
    
    @commands.Cog.listener() # this means its an event when the a post is made in a forum channel
    async def on_thread_create(self, thread: discord.Thread): # this is the function that runs when a post is made in a forum channel
        # thread: discord.Thread means that its telling me what thread was made
        snugtown = 1122231942453141565 # the ID for the discord server

        if thread.guild.id == snugtown: # if the thread was made in my discord server
            new_town_ideas = 1130364285491626055
            town_jobs = 1130366266247491654
            suggestions = 1130644472657608755
            auction_house = 1132321569427947730
            bot_suggestions = 1147018651862573116

            if thread.parent_id in solvable:
                await thread.join() # bot joins the thread
                await thread.starter_message.pin(reason=f'Thread opened by {thread.owner}, automatic pin.') # pins the first message you send in there
                logger_forums.info(f"Thread {thread.id} created by {thread.owner} in {thread.parent.name} ({thread.parent.id})")



            # traffic = 842802366159257620
            # if thread.owner_id == traffic:
            #     await thread.send('fuck you trafic i can make as meany epl ing mistake as ai want')

            if thread.parent_id in [new_town_ideas, town_jobs] and thread.owner_id != me: 
                # if the thread was made in the new_town_ideas or town_jobs channel
                # and the owner of the thread is not me (@aidenpearce3066)

                tag_18 = None
                tag_20 = None
                tag_solved = None

                for tag in thread.parent.available_tags:
                    if tag.name == "1.18":
                        tag_18 = tag
                    elif tag.name == "1.20":
                        tag_20 = tag
                    elif tag.name in ["Solved", "Completed", "Sold", "Closed"]:
                        tag_solved = tag
                if tag_20 not in thread.applied_tags and tag_18 not in thread.applied_tags:
                    await thread.send("Your thread must have either the `1.18` or the `1.20` tag. I am adding the 1.20 tag for you. If your post was a 1.18 related matter, please delete this post and create a new one, giving it the `1.18` tag.")
                    await thread.add_tags(tag_20)
                if tag_20 in thread.applied_tags and tag_18 in thread.applied_tags:
                    await thread.send("Your thread cannot have both the `1.18` and the `1.20` tag. I am removing the 1.18 tag for you. If your post was a 1.18 related matter, please delete this post and create a new one, giving it the `1.18` tag.")
                    await thread.remove_tags(tag_18)
                if tag_solved in thread.applied_tags:
                    await thread.send("Your thread cannot have the `Solved` tag. I am removing it for you.")
                    await thread.remove_tags(tag_solved)

            if thread.parent_id == auction_house and thread.owner_id != me:

                tag_sold = None
                tag_from_owner = None
                tag_one_time = None
                tag_restocking = None
                tag_unique_item = None
                tag_common_item = None
                tag_rare_item = None
                tag_tools = None
                tag_gear = None
                tag_item = None
                tag_other = None

                for tag in thread.parent.available_tags:
                    if tag.name == "Sold":
                        tag_sold = tag
                    elif tag.name == "From the Owner":
                        tag_from_owner = tag
                    elif tag.name == "One-Time":
                        tag_one_time = tag
                    elif tag.name == "Restocking":
                        tag_restocking = tag
                    elif tag.name == "Unique Item":
                        tag_unique_item = tag
                    elif tag.name == "Rare Item":
                        tag_rare_item = tag
                    elif tag.name == "Common Item":
                        tag_common_item = tag
                    elif tag.name == "Tools":
                        tag_tools = tag
                    elif tag.name == "Gear":
                        tag_gear = tag
                    elif tag.name == "Item":
                        tag_item = tag
                    elif tag.name == "Other":
                        tag_other = tag

                tags = thread.applied_tags
                
                if tag_sold in tags:
                    await thread.send("Your thread cannot have the `Sold` tag. I am removing it for you.")
                    await thread.remove_tags(tag_sold)
                
                if tag_from_owner in tags and thread.owner_id != me:
                    await thread.send("Your thread cannot have the `From the Owner` tag. I am removing it for you.")
                    await thread.remove_tags(tag_from_owner)
                
                if tag_one_time in tags and tag_restocking in tags:
                    await thread.send("Your thread cannot have both the `One-Time` and the `Restocking` tags. Make a new post, picking __one__ between the `One-Time` and the `Restocking` tags.")
                    await self.solved(thread)
                    return

                hasunique = False
                hasrare = False
                hascommon = False

                for tag in tags:
                    if tag == tag_unique_item:
                        hasunique = True
                    elif tag == tag_rare_item:
                        hasrare = True
                    elif tag == tag_common_item:
                        hascommon = True
                
                if (hasunique and hasrare and hascommon) or (hasunique and hasrare) or (hasunique and hascommon) or (hasrare and hascommon):
                    await thread.send("Your thread cannot have more than 1 of the following tags: `Unique Item`, `Rare Item` and `Common Item` tags. Make a new post, picking __one__ between the `Unique Item`, `Rare Item` and `Common Item` tags.")
                    await self.solved(thread)
                    return
    


async def setup(bot):
    await bot.add_cog(ForumCog(bot)) # adds the cog to the bot
