import discord
from discord import app_commands, ui
from discord.app_commands import Group
from discord.ext import commands, tasks
from main import emojidict, revemojidict, getorfetch_channel, me, guilds
import asyncio
import datetime
import traceback
from aidenlib.main import makeembed_bot, makeembed


async def autocomplete_biome(interaction: discord.Interaction, current: str):
    exact_matches = []
    other_matches = []

    for biome in biomes:
        if biome[1] != 1: continue
        biome = biome[0].lower().replace("_"," ").title()[:24]
        if biome.lower().startswith(current.lower()):
            exact_matches.append(app_commands.Choice(name=biome, value=biome))
        elif current.lower() in biome.lower():
            other_matches.append(app_commands.Choice(name=biome, value=biome))
        if len(exact_matches) + len(other_matches) >= 25:
            break

    exact_matches.extend(other_matches)

    return list(exact_matches)
    
class BiomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    biomes: list[tuple[str, int]] = [
        ("badlands", 1), 
        ("bamboo_jungle", 1), 
        ("basalt_deltas", 2), 
        ("beach", 1), 
        ("birch_forest", 1), 
        ("cherry_grove", 1), 
        ("cold_ocean", 1), 
        ("crimson_forest", 2), 
        ("dark_forest", 1), 
        ("deep_cold_ocean", 1), 
        ("deep_dark", 1), 
        ("deep_frozen_ocean", 1), 
        ("deep_lukewarm_ocean", 1), 
        ("deep_ocean", 1), 
        ("desert", 1), 
        ("dripstone_caves", 1), 
        ("end_barrens", 3), 
        ("end_highlands", 3), 
        ("end_midlands", 3), 
        ("eroded_badlands", 1), 
        ("flower_forest", 1), 
        ("forest", 1), 
        ("frozen_ocean", 1), 
        ("frozen_peaks", 1), 
        ("frozen_river", 1), 
        ("grove", 1), 
        ("ice_spikes", 1), 
        ("jagged_peaks", 1), 
        ("jungle", 1), 
        ("lukewarm_ocean", 1), 
        ("lush_caves", 1), 
        ("mangrove_swamp", 1), 
        ("meadow", 1), 
        ("mushroom_fields", 1), 
        ("nether_wastes", 2), 
        ("ocean", 1), 
        ("old_growth_birch_forest", 1), 
        ("old_growth_pine_taiga", 1), 
        ("old_growth_spruce_taiga", 1), 
        ("plains", 1), 
        ("river", 1), 
        ("savanna", 1), 
        ("savanna_plateau", 1), 
        ("small_end_islands", 3), 
        ("snowy_beach", 1), 
        ("snowy_plains", 1), 
        ("snowy_slopes", 1), 
        ("snowy_taiga", 1), 
        ("soul_sand_valley", 2), 
        ("sparse_jungle", 1), 
        ("stony_peaks", 1), 
        ("stony_shore", 1), 
        ("sunflower_plains", 1), 
        ("swamp", 1), 
        ("taiga", 1), 
        ("the_end", 3), 
        ("the_void", 3), 
        ("warm_ocean", 1), 
        ("warped_forest", 2), 
        ("windswept_forest", 1), 
        ("windswept_gravelly_hills", 1), 
        ("windswept_hills", 1), 
        ("windswept_savanna", 1), 
        ("wooded_badlands", 1)
    ]

    @commands.hybrid_command(name='biome_send', description="send shit", hidden=True, with_app_command=False)
    async def send_biomes(self, ctx: commands.Context):
        global biomes
        if ctx.author.id == me:
            await ctx.message.delete()
            for biome in biomes:
                if biome[1] == 1:
                    msg = await ctx.send(f"`{biome[0].replace('_',' ').title()}`")
                    await msg.add_reaction(emojidict.get(1))
                    await msg.add_reaction(emojidict.get(2))
                    await msg.add_reaction(emojidict.get(3))
                    await msg.add_reaction(emojidict.get(4))
                    await msg.add_reaction(emojidict.get(5))
                    await asyncio.sleep(1)

    msgs: list[discord.Message] = []
    embmsg: discord.Message = None
    counting: bool = False
    counts = []

    @commands.command(name='getvotes',description='Checks on how many votes a certain biome has.')
    @app_commands.autocomplete(biome=autocomplete_biome)
    @app_commands.guilds(*guilds)
    async def check_vote(self, interaction: discord.Interaction, biome: str):
        global msgs, counts
        biome_ = biome.lower().replace(" ","_")
        if (biome_,1) not in biomes and (biome_,2) not in biomes and (biome_, 3) not in biomes:
            await interaction.response.send_message("Not a valid biome. Try again.",ephemeral=True)
            return
        ind: int = None
        try:
            ind = biomes.index((biome_,1))
        except:
            try:
                ind = biomes.index((biome_,2))
            except:
                ind = biomes.index((biome_,3))
            
        if biomes[ind][1] != 1:
            await interaction.response.send_message("This biome cannot be voted on (Nether or End biome).",ephemeral=True)
            return
        counts2 = []
        await interaction.response.defer(thinking=True)
        if len(counts) != 0:
            for count in counts:
                if count[0].replace('`','') == biome:
                    await interaction.followup.send(f"`{biome.replace('_',' ').replace('`','').title()}` has `{count[1]}` votes.",ephemeral=True)
                    return
        elif len(msgs) != 0:
            for msg in msgs:
                if msg.content == biome:
                    for reaction in msg.reactions:
                        if reaction.emoji not in emojidict.values(): continue
                        count_ = 0
                        async for user in reaction.users(limit=50):
                            if user.id == self.bot.user.id: continue
                            # 1122233006501929110 is resident role, 1130613713565650944 honorary resident
                            if user.get_role(1122233006501929110) != None or user.get_role(1130613713565650944):
                                try:
                                    count_ += revemojidict.get(str(reaction.emoji))
                                except:
                                    print(f"Exception: {reaction.emoji}")
                        counts2.append((msg.content, count_))
                        counts[counts.index((msg.content, 1))] = (msg.content, count_)
            counts2.sort(key=lambda x: x[1])
            await interaction.followup.send(f"`{biome.replace('_',' ').replace('`','').title()}` has `{counts2[0][1]}` votes.",ephemeral=True)
            return
        else:
            await interaction.followup.send("No votes have been counted yet.",ephemeral=True)
            return

    @commands.hybrid_command(name='biome_countvotes',hidden=True, with_app_command=False)
    async def biome_countvotes(self, ctx: commands.Context):
        try:
            global msgs, embmsg, counting
            if ctx.author.id == me:
                await ctx.message.delete()
                if counting:
                    m = await ctx.send("Already counting votes.")
                    await asyncio.sleep(3)
                    await m.delete()
                    return
                else:
                    m = await ctx.send("Starting to count votes...")
                    await asyncio.sleep(3)
                    await m.delete()
                    await self.countvotes()
        except:
            traceback.print_exc()

# @tasks.loop(seconds=30)
# async def voteloop():
#     try:
#         global msgs, embmsg, counting
#         if datetime.datetime.now().minute % 15 != 0: return
#         await countvotes()
#     except:
#         traceback.print_exc()

    async def countvotes(self):
        global msgs, embmsg, counting, counts
        if counting: return
        counting = True
        a = datetime.datetime.now()
        ch = await getorfetch_channel(1130349822768062494)
        if len(msgs) == 0:
            # we need to count the msgs
            async for msg in ch.history(limit=100):
                if msg.author.id != self.bot.user.id: continue
                msgs.append(msg)
            msgs.reverse()
        counts = []
        for msg in msgs:
            count = 0
            if msg.id == 1130542924313145446: continue
            for reaction in msg.reactions:
                if reaction.emoji not in emojidict.values(): continue
                users = []
                async for user in reaction.users(limit=50):
                    if user.id == self.bot.user.id: continue
                    if user in users: continue
                    users.append(user)
                    # 1122233006501929110 is resident role
                    if user.get_role(1122233006501929110) != None:
                        try:
                            count += revemojidict.get(str(reaction.emoji))
                        except:
                            print(f"Exception: {reaction.emoji}")
            counts.append((msg.content, count))
            print(f"counted {msg.content.replace('`','')}")
        returnv = ""
        counts.sort(key=lambda x: x[1])
        #counts.reverse()
        for count in counts:
            returnv += f"{count[0].replace('`','')}: `{count[1]}` points\n"
        print(returnv)
        emb = makeembed_bot(title="Biome Votes", description=returnv, timestamp=datetime.datetime.now())
        try:
            await embmsg.edit(embed=emb)
        except:
            try:
                embmsg = await ch.fetch_message(1130542924313145446)
                if embmsg is None: raise Exception()
                else:
                    await embmsg.edit(embed=emb)
            except:
                embmsg = await ch.send(embed=emb)
        msg = await ch.send("<@&1130599557638672485>: counted votes.")
        b = datetime.datetime.now()
        print(f"counted votes in {b.timestamp()-a.timestamp()}s")
        await asyncio.sleep(3)
        await msg.delete()
        counting = False

async def setup(bot):
    await bot.add_cog(BiomeCog(bot))