from logging import Logger
import discord
from discord import DMChannel, app_commands, Interaction, Embed, ui
from collections import deque
from discord.ext import commands
from aidenlib.main import dchyperlink, getorfetch_user, makeembed, dctimestamp
import datetime
import traceback
import pkgutil
import os
from typing import Optional, NamedTuple, Any, Union, List, Collection
from discord.utils import _URL_REGEX
import tortoise
from tortoise import fields
from tortoise.models import Model
import asyncio
import re

_IP_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
_IPPORT_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(:([6][0-5]{2}[0-3][0-5]|[1-5][1-9]{4}|[1-9][0-9]{0,3}))?$"
IP_REGEX = re.compile(_IP_REGEX)
URL_REGEX = re.compile(_URL_REGEX)
IPPORT_REGEX = re.compile(_IPPORT_REGEX)

class Base(Model):
    dbid = fields.BigIntField(pk=True,unique=True,generated=True)
    datelogged = fields.DatetimeField(auto_now_add=True)
    lastupdated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class GuildServers(Base):
    guildid = fields.BigIntField()
    serverip = fields.TextField(null=False) # ip:port
    ip = fields.TextField(null=False)
    port = fields.IntField(null=False,default=25565)
    name = fields.TextField(null=True)

    class Meta:
        table = "GuildServers"

class GuildDynmaps(Base):
    guildid = fields.BigIntField()
    url = fields.TextField(null=False) # ip:port
    name = fields.TextField(null=True)

    class Meta:
        table = "GuildDynmaps"

async def autocomplete_ip(interaction: discord.Interaction, current: str):
        if interaction.guild is None: return []
        if current.strip() == "":
            matches = [app_commands.Choice(name=s,value=s) for s in await GuildServers.filter(guildid=interaction.guild.id).values_list('name',flat=True)]
            if len(matches) >= 25:
                return matches[:25]
        matches = []
        partial_matches = []
        try:
            current = current.lower()
            for server in await GuildServers.filter(guildid=interaction.guild.id).values_list('name',flat=True):
                if server is None: continue
                server_ = str(server)
                server = str(server).lower()
                if server.lower() == current.lower():
                    matches.append(app_commands.Choice(name=server_,value=server_))
                elif current in server:
                    partial_matches.append(app_commands.Choice(name=server_,value=server_))
                if len(matches) + len(partial_matches) >= 25:
                    break
        except:
            return []
        matches.extend(partial_matches)
        return matches

async def autocomplete_dynmap(interaction: discord.Interaction, current: str):
        if interaction.guild is None: return []
        if current.strip() == "":
            matches = [app_commands.Choice(name=s,value=s) for s in await GuildDynmaps.filter(guildid=interaction.guild.id).values_list('url',flat=True)]
            if len(matches) >= 25:
                return matches[:25]
        matches = []
        partial_matches = []
        try:
            current = current.lower()
            for server in await GuildDynmaps.filter(guildid=interaction.guild.id).values_list('url',flat=True):
                if server is None: continue
                server_ = str(server)
                server = str(server).lower()
                if server.lower() == current.lower():
                    matches.append(app_commands.Choice(name=server_,value=server_))
                elif current in server:
                    partial_matches.append(app_commands.Choice(name=server_,value=server_))
                if len(matches) + len(partial_matches) >= 25:
                    break
        except:
            return []
        matches.extend(partial_matches)
        return matches

def admin_or_owner():
    async def check(interaction: discord.Interaction | commands.Context):
        a = None
        bot = None
        try:
            bot = interaction.bot
        except AttributeError:
            bot = interaction.client
        try:
            a = interaction.author
        except AttributeError:
            a = interaction.user
        # guild specific
        if interaction.guild.id == 867978433077080165:
            return await bot.is_owner(a)
        return await bot.is_owner(a) or a.guild_permissions.manage_guild
    return app_commands.check(check)


class MinecraftCog(commands.Cog):
    bot: commands.Bot
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name='ip',description="Get the Server IP for your server.",fallback='get')
    @app_commands.guild_only()
    @app_commands.describe(servername="The name of the server to get the IP for.")
    @app_commands.autocomplete(servername=autocomplete_ip)
    @commands.cooldown(1,5,commands.BucketType.user)
    async def ip(self, interaction: commands.Context, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildServers.filter(guildid=interaction.guild.id,name=servername).first()
            if item is None: raise Exception()
        except:
            await interaction.reply("A server with that name does not exist, or the server owner has not set up the IP for that server yet. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await interaction.reply(f"The IP for {f'Server `{item.name}`' if item.name else 'the Minecraft Server'} is `{item.serverip}`.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
        await asyncio.sleep(30)
        await interaction.message.delete()


    @ip.command(name='set',description="Set the Server IP for your server.")
    @admin_or_owner()
    @app_commands.autocomplete(servername=autocomplete_ip)
    @app_commands.describe(ip="The IP to set for the server", port="The port to set for the server. Not required.", servername="The name of the server to set the IP for.")
    @commands.cooldown(1,5,commands.BucketType.user)
    async def ip_set(self, interaction: commands.Context, ip: str, port: int=25565, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildServers.filter(guildid=interaction.guild.id,name=servername).first()
            if item is not None: raise Exception()
        except:
            await interaction.reply(traceback.format_exc())
            await interaction.reply("A server with this name exists already, or you haven't set a name and have more than one server. Try again.\nIf you are the owner, you can update this IP via </ip update:1159187766148616282>.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        if ":" in ip and port != 25565:
            ip,port = ip.split(":")
            try:
                port = int(port)
            except:
                await interaction.reply("Invalid port. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
                return
        serverip = f"{ip}{f':{port}' if port not in [None, 25565] else ''}"
        await GuildServers.create(guildid=interaction.guild.id,serverip=serverip,ip=ip,port=port,name=servername)
        await interaction.reply(f"The IP for {f'server `{servername}`' if servername else 'the Minecraft Server'} has been set as `{serverip}`.",ephemeral=True,delete_after=(30.0 if interaction.interaction else None))
        await asyncio.sleep(30)
        await interaction.message.delete()

    @ip.command(name='update',description="Update the Server IP for your server.")
    @admin_or_owner()
    @app_commands.describe(newip="The new IP to set for the server", newport="The new port to set for the server. Not required.", servername="The name of the server to update the IP for.")
    @app_commands.autocomplete(servername=autocomplete_ip)
    @commands.cooldown(1,5,commands.BucketType.user)
    async def ip_update(self, interaction: commands.Context, newip: str, newport: Optional[int]=25565, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildServers.filter(guildid=interaction.guild.id,name=servername).first()
            if item is None: raise Exception()
        except:
            await interaction.reply("A server with this name does not exist, or you haven't set a name and have more than one server. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        if ":" in newip and newport != 25565:
            newip,newport = newip.split(":")
            try:
                newport = int(newport)
            except:
                await interaction.reply("Invalid port. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
                return
        serverip = f"{newip}{f':{newport}' if newport not in [None, 25565] else ''}"
        if item.serverip == serverip:
            await interaction.reply(f"The IP for {f'`{servername}`' if servername else 'the Minecraft Server'} is already `{serverip}`.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await GuildServers.filter(guildid=interaction.guild.id,name=servername).update(serverip=serverip,ip=newip,port=newport)
        await interaction.reply(f"The IP for {f'`{servername}`' if servername else 'the Minecraft Server'} was changed from `{item.serverip}` to `{serverip}`.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
        await asyncio.sleep(30)
        await interaction.message.delete()

    @ip.command(name='delete',description="Remove the Server IP for your server.")
    @admin_or_owner()
    @app_commands.describe(servername="The name of the server to remove the IP for.")
    @app_commands.autocomplete(servername=autocomplete_ip)
    @commands.cooldown(1,5,commands.BucketType.user)
    async def ip_delete(self, interaction: commands.Context, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildServers.filter(guildid=interaction.guild.id,name=servername).first()
            if item is None: raise Exception()
        except:
            await interaction.reply("A server with this name does not exist, or you haven't set a name and have more than one server. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await GuildServers.filter(guildid=interaction.guild.id,name=servername).delete()
        await interaction.reply(f"The IP for {f'server `{servername}`' if servername else 'the Minecraft Server'} was removed.",ephemeral=True)
        await asyncio.sleep(30)
        await interaction.message.delete()

    @commands.hybrid_group(name='dynmap',description="Get the Dynmap URL for a server.",fallback='get')
    @app_commands.guild_only()
    @app_commands.describe(servername="The name of the server to get the dynmap for.")
    @app_commands.autocomplete(servername=autocomplete_dynmap)
    @commands.cooldown(1,5,commands.BucketType.user)
    async def dynmap(self, interaction: commands.Context, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildDynmaps.filter(guildid=interaction.guild.id,name=servername).first()
            if item is None: raise Exception()
        except:
            await interaction.reply("A Dynmap with that name does not exist, or the server owner has not set up the URL for that server yet. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await interaction.reply(f"The Dynmap URL for `{item.name}` is {dchyperlink(item.url,'here','See the Dynmap!')}.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
        await asyncio.sleep(30)
        await interaction.message.delete()

    @dynmap.command(name='set',description="Set the Dynmap URL for your server.")
    @admin_or_owner()
    @app_commands.autocomplete(servername=autocomplete_dynmap)
    @app_commands.describe(url="The Dynmap URL to set for the server.", servername="The name of the server to set the Dynmap URL for.")
    @commands.cooldown(1,5,commands.BucketType.user)
    async def dynmap_set(self, interaction: commands.Context, url: str, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildDynmaps.filter(guildid=interaction.guild.id,name=servername).first()
            if item is not None: raise Exception()
        except:
            await interaction.reply("A server with this name exists already, or you haven't set a name and have more than one server. Try again.\nIf you are the owner, you can update this via </dynmap update:1159204313952960633>.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        if IPPORT_REGEX.match(url):
            url = f"http://{url}/"
        if not URL_REGEX.match(url) and not IPPORT_REGEX.match(url):
            await interaction.reply("Invalid URL. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await GuildDynmaps.create(guildid=interaction.guild.id,url=url,name=servername)
        await interaction.reply(f"The Dynmap URL for {f'`{servername}' if servername else 'the Minecraft Server'} has been set to `{dchyperlink(item.url,'this','See the Dynmap!')}`.",ephemeral=True,delete_after=(30.0 if interaction.interaction else None))
        await asyncio.sleep(30)
        await interaction.message.delete()

    @dynmap.command(name='update',description="Update the Dynmap URL for your server.")
    @admin_or_owner()
    @app_commands.describe(newurl="The new Dynmap URL to set for the server.",servername="The name of the server to update the IP for.")
    @app_commands.autocomplete(servername=autocomplete_dynmap)
    @commands.cooldown(1,5,commands.BucketType.user)
    async def dynmap_update(self, interaction: commands.Context, newurl: str, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildDynmaps.filter(guildid=interaction.guild.id,name=servername).first()
            if item is None: raise Exception()
        except:
            await interaction.reply("A Dynmap URL with this name does not exist, or you haven't set a name and have more than one server. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        if IP_REGEX.match(newurl):
            newurl = f"http://{newurl}/"
        if not URL_REGEX.match(newurl) and not IP_REGEX.match(newurl):
            await interaction.reply("Invalid URL. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        if item.url == newurl:
            await interaction.reply(f"The Dynmap URL for {f'`{servername}`' if servername else 'the Minecraft Server'} is already {dchyperlink(item.url,'this','See the Dynmap!')}.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await GuildDynmaps.filter(guildid=interaction.guild.id,name=servername).update(url=newurl)
        await interaction.reply(f"The Dynmap URL for {f'`{servername}`' if servername else 'the Minecraft Server'} was changed from `{item.url}` to `{serverip}`.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
        await asyncio.sleep(30)
        await interaction.message.delete()

    @dynmap.command(name='delete',description="Remove the Dynmap URL for your server.")
    @admin_or_owner()
    @app_commands.describe(servername="The name of the server to remove the Dynmap URL for.")
    @app_commands.autocomplete(servername=autocomplete_dynmap)
    @commands.cooldown(1,5,commands.BucketType.user)
    async def dynmap_delete(self, interaction: commands.Context, servername: str=""):
        await interaction.defer(ephemeral=True)
        if servername.strip() == "": servername = None
        try:
            item = await GuildDynmaps.filter(guildid=interaction.guild.id,name=servername).first()
            if item is None: raise Exception()
        except:
            await interaction.reply("A Dynmap URL with this name does not exist, or you haven't set a name and have more than one server. Try again.",ephemeral=True,delete_after=(30.0 if not interaction.interaction else None))
            return
        await GuildDynmaps.filter(guildid=interaction.guild.id,name=servername).delete()
        await interaction.reply(f"The Dynmap URL for {f'`{servername}`' if servername else 'the server'} was removed.",ephemeral=True)
        await asyncio.sleep(30)
        await interaction.message.delete()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        delete_after: Optional[float] = 10.0 if not ctx.interaction else None
        if isinstance(error, commands.NotOwner):
            return await ctx.reply(f"You aren't my father (well owner).",ephemeral=True,delete_after=delete_after)
        else:
            return await ctx.reply(str(error),ephemeral=True,delete_after=delete_after)  
        

async def setup(bot):
    try:
        cog = MinecraftCog(bot)
        await bot.add_cog(cog)
        await tortoise.Tortoise.init(config_file='config.yml')
        #await tortoise.Tortoise.generate_schemas()
    except:
        traceback.print_exc()

async def main():
    await tortoise.Tortoise.init(config_file='config.yml')
    await tortoise.Tortoise.generate_schemas()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())