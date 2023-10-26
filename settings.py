import discord
from discord import app_commands, guild
from discord.abc import Snowflake
from discord.app_commands import AppCommand, Command, Group
from discord.enums import AppCommandType
from discord.ext import commands, tasks
from discord.ext.commands import HybridGroup, UserInputError
from main import me, emojidict, logger, hyperlinkurlorip, guilds
import datetime
import traceback
import os
from enum import Enum
import tortoise
from tortoise import fields, Tortoise
from tortoise.models import Model
from aidenlib.main import makeembed_bot, makeembed
import asyncio
from typing import Any, Optional, Union, List, Dict, Literal
from dataclasses import dataclass
from exceptions import UsedPrefixCommandException
from mentionable_tree import MentionableTree

class SettingsCog(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        #assert isinstance(bot.tree, MentionableTree)
        self.tree: MentionableTree = bot.tree
    
    async def mention_command(self, command: Union[str, commands.Command]) -> Optional[str]:
        if isinstance(command, str):
            cmd = await self.get_command(command)
            if cmd is None: return None
        else:
            cmd = command
        return self.tree.get_mention_for(cmd)
    
    async def get_command(self, *args, **kwargs) -> Optional[Command]:
        """Gets a command from the MentionableTree. Only returns a Command, not a Group or context menu.
        If a group/context menu is found, returns None."""
        if cmd := (self.tree.get_command(*args, **kwargs)) is not None:
            if isinstance(cmd, Command):
                return cmd
            else:
                return None

    @commands.hybrid_group(name='settings',description='Settings for the bot.',fallback='view')
    async def settings(self, ctx: commands.Context):
        try: await ctx.reply(view=SettingsView(await Settings.all(), ctx.author))
        except: traceback.print_exc()

    @settings.command(name='add',description="Add a new setting to the database.")
    @commands.is_owner()
    @app_commands.describe(name="The name of the setting", 
    description="The description of the setting", emoji="The emoji to use for the setting", 
    valuetype="The type of value the setting should have. (bool, int, float, str)", settingtype="The type of setting (user or guild)",
    default='The default value for the setting.')
    async def add(self, ctx: commands.Context, name: str, description: str, settingtype: Literal['user', 'guild'], valuetype: Literal['bool','int','float','str'], default: str, emoji: Optional[str]=None):
        try:
            if valuetype == 'bool':
                if default not in ['true','false']:
                    return await ctx.reply("Invalid default value for bool.")
                default = default.lower()
            elif valuetype == 'int':
                try:
                    int(default)
                except:
                    return await ctx.reply("Invalid default value for int.")
            elif valuetype == 'float':
                try:
                    float(default)
                except:
                    return await ctx.reply("Invalid default value for float.")
            setting = await Settings(id=int(await Settings.all().count()),name=name,description=description,emoji=emoji,valuetype=valuetype,default=default,settingtype=settingtype)
            await setting.save()
            await ctx.reply("Added setting.")
        except: 
            traceback.print_exc()
            await ctx.reply("Failed to add setting.")

    @settings.command(name='all',description="View all settings in the database.")
    @commands.is_owner()
    async def all(self, ctx: commands.Context):
        try:
            await ctx.reply(embed=makeembed_bot(title="All Settings", description="\n".join([f"{s.name} (`{s.id}`) {s.description} (`{s.valuetype}`) default (`{s.default}`) {s.emoji}" for s in await Settings.all()])))
        except: 
            traceback.print_exc()
            await ctx.reply("Failed to get settings.")
    
    @settings.command(name='remove',description="Remove a setting from the database.")
    @commands.is_owner()
    async def remove(self, ctx: commands.Context, id: int):
        try:
            await Settings.filter(id=id).delete()
            await ctx.reply("Removed setting.")
        except: 
            traceback.print_exc()
            await ctx.reply("Failed to remove setting.")

class Base(Model):
    dbid = fields.IntField(pk=True)
    datelogged = fields.DatetimeField(auto_now_add=True)
    lastupdated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class Settings(Base):
    id = fields.BigIntField(unique=True)
    name = fields.TextField()
    description = fields.TextField()
    emoji = fields.TextField(null=True)
    default = fields.TextField(null=True)
    valuetype = fields.TextField()
    settingtype = fields.TextField() # user or guild

    class Meta:
        table = "Settings"
    
    def to_embed(self) -> discord.Embed:
        return makeembed_bot(title=self.name, description=f" > {self.description}\nCurrent value: {emojidict.get(self.default) if isinstance(self.default, bool) else ''} {'`'+self.default+'`' if not isinstance(self.default, bool) else ''}")

class DBUserSettings(Base):
    id = fields.BigIntField(unique=True)
    username = fields.TextField()
    userid = fields.BigIntField()
    value = fields.TextField()
    valuetype = fields.TextField()

    class Meta:
        table = "UserSettings"

class DBGuildSettings(Base):
    id = fields.BigIntField(unique=True)
    username = fields.TextField()
    guildid = fields.BigIntField()
    value = fields.TextField()
    valuetype = fields.TextField()

    class Meta:
        table = "GuildSettings"

class SettingsDropdown(discord.ui.Select):
    def __init__(self, settings: List[Settings], user: discord.User):
        options = [
            discord.SelectOption(label=s.name, description=s.description[:97]+('...' if len(s.description) >= 97 else ''), 
            value=str(s.id),emoji=s.emoji, default=False)
            for s in settings
        ]
        self.user = user
        self.settings = settings
        super().__init__(placeholder="Select a setting", min_values=1, max_values=1, custom_id='e', options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user.id: raise UserInputError
            setting_ = await Settings.get(id=int(self.values[0]))
            if not await DBUserSettings.filter(id=int(self.values[0]),userid=self.user.id).exists():
                new = DBUserSettings(id=setting_.id,userid=interaction.user.id,username=interaction.user.name,value=setting_.default,valuetype=setting_.valuetype)
                await new.save()
                setting = await DBUserSettings.get(id=setting_.id,userid=self.user.id)
                if setting_.valuetype == 'bool':
                    view = ChangeSettingsViewBool(setting_,setting,self.user)
                else:
                    view = ChangeSettingsView(setting_,setting,self.user)
                await interaction.response.edit_message(view=view,embed=view.to_embed())
        except UserInputError:
            await interaction.response.send_message("You can't use this! Use ", ephemeral=True)
        except:
            traceback.print_exc()

class SettingsView(discord.ui.View):
    def __init__(self, settings: List[Settings], user: discord.User):
        super().__init__()
        self.add_item(SettingsDropdown(settings,user))

# class ChangeSettingView(discord.ui.View):
#     value: Union[bool,int,str,float]
#     settings: Settings
#     user: discord.User
#     user_settings: DBUserSettings

#     def __init__(self, setting: Settings, user: discord.User):
#         super().__init__(timeout=60)
#         self.setting = setting
#         if setting.valuetype == "bool":
#             self.value = False
#             self.add_item(Boolean(self, self.value, False))
#             self.add_item(BooleanButton(self, not self.value, True))
#         elif setting.valuetype == "int":
#             self.value = 0
#         elif setting.valuetype == "str":
#             self.value = ""
#         elif setting.valuetype == 'float':
#             self.value = 0.0
#         self.user = user
    
#     async def callback(self, interaction: discord.Interaction, value: Union[bool,int,str,float]):
#         if interaction.user.id != self.user.id:
#             return
#         self.user_settings.__setattr__(self.setting.name, value)
#         await self.user_settings.save()
#         self.clear_items()
#         self.stop()
    
#     async def get_user_settings(self) -> Optional[DBUserSettings]:
#         return await DBUserSettings.get_or_none(id=self.user.id)
    
class ChangeSettingsViewBool(discord.ui.View):

    def __init__(self, setting: Settings, usersetting: DBUserSettings, user: discord.User, timeout: Optional[float]=None):
        super().__init__(timeout=timeout)
        self.setting = setting
        self.usersetting = usersetting
        self.user = user
        self.value = self.usersetting.value.lower() == "true"
        if self.value:
            self.disabled.disabled = False
            self.enabled.disabled = True
        else:
            self.disabled.disabled = True
            self.enabled.disabled = False
    
    def to_embed(self) -> discord.Embed:
        return makeembed_bot(title=f"Setting: {self.setting.name}", description=f" > {self.setting.description}\nCurrent value: {emojidict.get(self.usersetting.value == 'true') if self.usersetting.value in ['true','false'] else ''} {'`'+self.usersetting.value+'`' if not isinstance(self.usersetting.value, bool) else ''}")

    @discord.ui.button(label="Enabled", style=discord.ButtonStyle.green, custom_id="enabled",emoji=emojidict.get('check2'))
    async def enabled(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user.id:
                return
            self.value = True
            self.usersetting.value = "true"
            button.disabled = True
            self.disabled.disabled = False
            await self.usersetting.save()
            await interaction.response.edit_message(view=self,embed=self.to_embed())
        except:
            traceback.print_exc()

    @discord.ui.button(label="Disabled", style=discord.ButtonStyle.red,custom_id="disabled",emoji=emojidict.get('x2'))
    async def disabled(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user.id:
                return
            self.value = False
            self.usersetting.value = "false"
            button.disabled = True
            self.enabled.disabled = False
            await self.usersetting.save()
            await interaction.response.edit_message(view=self,embed=self.to_embed())
        except:
            traceback.print_exc()
    
    @discord.ui.button(label="Back", style=discord.ButtonStyle.blurple, custom_id="back",emoji=emojidict.get('back'))
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user.id:
                return
            await interaction.response.edit_message(view=SettingsView(await Settings.all(), self.user),embed=None)
            self.stop()
        except:
            traceback.print_exc()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, custom_id="cancel",emoji=emojidict.get('no'))
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user.id:
                return
            await interaction.response.edit_message(view=None)
            await interaction.message.delete()
        except:
            traceback.print_exc()

class ChangeSettingsView(discord.ui.View):
    def __init__(self, setting: Settings, usersetting: DBUserSettings, user: discord.User, timeout: Optional[float]=None):
        super().__init__(timeout=timeout)
        self.setting = setting
        self.usersetting = usersetting
        self.user = user
        self.value = self.usersetting.value
        self.isint = self.setting.valuetype == 'int'
        self.isfloat = self.setting.valuetype == 'float'
        self.isstr = self.setting.valuetype == 'str'
    
    def to_embed(self) -> discord.Embed:
        return makeembed_bot(title=f"Setting: {self.setting.name}", description=f" > {self.setting.description}\nCurrent value: `{self.usersetting.value}`")

    @discord.ui.button(label="Change Value", style=discord.ButtonStyle.gray, custom_id="enabled",emoji=emojidict.get('pencilpaper'))
    async def changenumber(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(ChangeSettingModal(self, int=self.isint, float=self.isfloat, str=self.isstr, min=None, max=None))
        except:
            traceback.print_exc()

    async def on_new_number(self, interaction: discord.Interaction, num: int):
        self.usersetting.value = str(num)
        await self.usersetting.save()
        await interaction.response.edit_message(view=self,embed=self.to_embed())

    @discord.ui.button(label="Back", style=discord.ButtonStyle.blurple, custom_id="back",emoji=emojidict.get('back'))
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user.id:
                return
            await interaction.response.edit_message(view=SettingsView(await Settings.all(), self.user),embed=None)
            self.stop()
        except:
            traceback.print_exc()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, custom_id="cancel",emoji=emojidict.get('no'))
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user.id:
                return
            await interaction.response.edit_message(view=None)
            await interaction.message.delete()
        except:
            traceback.print_exc()

class ChangeSettingModal(discord.ui.Modal):
    def __init__(self, view: ChangeSettingsView, title: str="Change Value", str: bool=True, int: bool=False, float: bool=False, 
    min: Optional[Union[int, float]]=None, max: Optional[Union[int, float]]=None, timeout: Optional[float]=None):
        super().__init__(title=title, timeout=timeout)
        self.view = view
        self.int = int
        self.float = float
        self.str = str
        self.min = min
        self.max = max

        if self.str:
            self.min = int(min) if min is not None else None
            self.max = int(max) if max is not None else None
            self.input = discord.ui.TextInput(label='Enter a value', min_length=self.min, max_length=self.max, placeholder="Enter a value", custom_id="text")
        else:
            self.input = discord.ui.TextInput(label='Enter a value',placeholder="Enter a value", custom_id="number")
        
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user.id:
            return
        if not self.input.value:
            return await interaction.response.send_message('You need to enter a value!', ephemeral=True)
        
        if self.int:
            int(self.input.value)
            if self.input.value.find('.') != -1:
                return await interaction.response.send_message('You need to enter an integer!', ephemeral=True)
        elif self.float:
            try:
                float(self.input.value)
            except:
                return await interaction.response.send_message('You need to enter a decimal!', ephemeral=True)
        if not self.str:
            if self.min is not None:
                if self.min > float(self.input.value):
                    return await interaction.response.send_message(f'You need to enter a number greater than {self.min}!', ephemeral=True)
            if self.max is not None:
                if self.max < float(self.input.value):
                    return await interaction.response.send_message(f'You need to enter a number less than {self.max}!', ephemeral=True)
        
        if self.int:
            returnv = int(self.input.value)
        elif self.float:
            returnv = float(self.input.value)
        else:
            returnv = self.input.value
        
        await self.view.on_new_number(interaction,returnv)
 

async def setup(bot: commands.Bot):
    await Tortoise.init(config_file="config.yml")
    await Tortoise.generate_schemas()
    cog = SettingsCog(bot)
    await bot.add_cog(cog)
