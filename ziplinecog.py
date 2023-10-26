import aidenlib
from asqlite import C
import discord
from discord import Message, app_commands, Interaction, Embed, ui
from discord.ext import commands
from discord.ext.commands import BucketType
from typing_extensions import override
from collections import deque
from main import me, emojidict, guilds, logger_
import traceback
from typing import Optional, NamedTuple, Any, Union, List, Dict, Tuple, Literal
import tortoise
from tortoise import fields
from tortoise.models import Model
import aiohttp
import yaml
from PIL import Image
import io
from io import BytesIO
import asyncio
import pillow_heif
from settings import DBUserSettings
from exceptions import UsedPrefixCommandException

with open('zipline.yml','r') as f: ASSISTANTBOT_AUTHTOKEN = yaml.safe_load(f).get('assistantbot2')

API_BASE = "https://cdn.aidenpearce.space/api"  

class Base(Model):
    dbid = fields.BigIntField(pk=True)
    datelogged = fields.DatetimeField(auto_now_add=True)
    lastupdated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class ZiplineUser(Base):
    id = fields.BigIntField(unique=True)
    """The ID of the user"""
    username = fields.CharField(unique=True,max_length=32)
    """The username of the user"""
    avatar = fields.TextField()
    """A base64 encoded image of the users avatar"""
    token = fields.TextField()
    """The users auth token"""
    administrator = fields.BooleanField()
    """If the user is an administrator"""
    superAdmin = fields.BooleanField()
    """If the user is a super administrator"""
    systemTheme = fields.TextField()
    """The system theme of the user"""
    embedTitle = fields.TextField()
    """The embed title of the user"""
    embedColor = fields.TextField()
    """The embed color of the user"""
    embedSiteName = fields.TextField()
    """The embed site name of the user"""
    ratelimit = fields.DatetimeField()
    """The ratelimit of the user, if any"""
    totpSecret = fields.TextField()
    """The TOTP secret of the user"""
    domains = fields.JSONField()
    """A list of domains"""
    oauth = fields.JSONField()
    """A list of oauth providers"""

    class Meta:
        table = "Users"

class OAuthProvider(Base):
    """DISCORD, GITHUB, GOOGLE"""
    id = fields.BigIntField(unique=True)
    """The ID of the provider"""
    provider = fields.TextField()
    """The provider of the oauth"""
    userId = fields.BigIntField()
    """The ID of the user"""
    oauthId = fields.TextField()
    """The ID of the oauth user, NOT zipling"""
    username = fields.TextField()
    """The username of the oauth user, NOT zipline"""
    token = fields.TextField()
    """The access_token"""
    refresh = fields.TextField()
    """The refresh_token"""

    class Meta:
        table = "OAuthProvider"

class ZiplineAuthorizedUser(Base):
    id = fields.BigIntField(unique=True)
    """Basic zipline user ID"""
    discordid = fields.BigIntField(unique=True)
    """Discord ID"""
    discordusername = fields.TextField()
    """Discord Username"""
    discordtoken = fields.TextField()
    """OAuth Token (discord)."""
    refresh = fields.TextField()
    """Refresh for the OAuth Token (discord)."""
    ziplineid = fields.UUIDField(unique=True)
    """User ID on Zipline. Looks similar to a UUID."""
    ziplinetoken = fields.TextField()
    """Zipline user token."""
    provider = fields.TextField()
    """OAuth provider. Should always be DISCORD."""
    admin = fields.BooleanField(default=False)

    class Meta:
        table = "ZiplineAuthorizedUser"

class ArchivedZiplineAuthorizedUser(ZiplineAuthorizedUser):
    olddbid = fields.BigIntField()
    olddatelogged = fields.DatetimeField()
    oldlastupdated = fields.DatetimeField()

    class Meta:
        table = "ArchivedZiplineAuthorizedUser"

MAX_SESSIONS = 1

# named_sessions: Dict[str, aiohttp.ClientSession] = {}
# numbered_sessions: List[aiohttp.ClientSession] = []
# async def get_session(session_name: Optional[str]=None, session_num: Optional[int]=None, **kwargs) -> aiohttp.ClientSession:
#     global named_sessions, numbered_sessions
#     session: Optional[aiohttp.ClientSession] = None
#     if session_num is not None and (s := numbered_sessions[session_num]):
#         session = s
#     elif session_num is not None and session_num >= len(numbered_sessions):
#         numbered_sessions[session_num] = aiohttp.ClientSession(**kwargs)
#         session = numbered_sessions[session_num]
#     elif session_name is not None and (s := named_sessions.get(session_name,None)):
#         session = s
#     elif session_name is not None and session_name not in named_sessions.keys():
#         named_sessions[session_name] = aiohttp.ClientSession(**kwargs)
#         session = named_sessions.get(session_name)
#     if len(numbered_sessions) <= MAX_SESSIONS:
#         numbered_sessions.append(aiohttp.ClientSession(**kwargs))
#         session = numbered_sessions[-1]
#     if session is not None: return session
#     else:
#         numbered_sessions.append(aiohttp.ClientSession(**kwargs))
#     raise Exception("No session found")

sessions: List[aiohttp.ClientSession] = []
async def get_session(**kwargs):
    if len(sessions) > MAX_SESSIONS:
        session = sessions.pop(-1)
        await session.close()
    if len(sessions) == 0:
        sessions.append(aiohttp.ClientSession(**kwargs))
    return sessions[-1]

# async def close_session(session: Optional[aiohttp.ClientSession]=None, session_name: Optional[str]=None, session_num: Optional[int]=None) -> None:
#     global named_sessions, numbered_sessions
#     if session is None:
#         if session_num is not None:
#             session = numbered_sessions.pop(session_num)

#         elif session_name is not None:
#             session = named_sessions.pop(session_name)
#         else:
#             raise Exception("No session found")
#     await session.close()

async def close_session(session: Optional[aiohttp.ClientSession]=None, session_name: Optional[str]=None, session_num: Optional[int]=None) -> None:
    global sessions
    if session is None:
        if session_num is not None:
            session = sessions.pop(session_num)
        elif len(sessions) > 0:
            session = sessions.pop(-1)
        else:
            raise Exception("No session found")
    await session.close()

def ensure_prefix():
    async def predicate(ctx: commands.Context):
        if ctx.interaction is None: raise UsedPrefixCommandException("This command can only be used as a slash command.")
        return True
    return commands.check(predicate)

class ZiplineCog(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def getorfetch_dm(self, user: Union[discord.User, discord.Member, int]) -> discord.DMChannel:
        if isinstance(user, int):
            if self.bot.get_user(user) is None:
                user = await self.bot.fetch_user(user)
            else:
                user = self.bot.get_user(user) # type: ignore
            assert isinstance(user, discord.User) or isinstance(user, discord.Member)
        if user.dm_channel is None:
            return await user.create_dm()
        return user.dm_channel  
    
    @commands.hybrid_group(name='zipline',descriptoin='Commands related to Zipline.')
    async def zipline(self, ctx: commands.Context):
        pass

    @zipline.command('link',description='Link your Zipline account to your Discord account.')
    @ensure_prefix()
    @app_commands.describe(username='Your username on Zipline.', userid='Your user ID on Zipline.')
    @commands.cooldown(1, 15, BucketType.user)
    async def link(self, ctx: commands.Context, username: Optional[str]=None, userid: Optional[int]=None):
        """Link your Aiden's Zipline account to your Discord account. Required to use Zipline commands."""
        try:
            await ctx.defer(ephemeral=True)
            session = await get_session(headers={'Authorization': ASSISTANTBOT_AUTHTOKEN})
            if username is None and userid is not None:
                r = await session.get(f'{API_BASE}/user/{userid}',headers={'Authorization': ASSISTANTBOT_AUTHTOKEN})
                r = await r.json()
                rr = await session.get(f'{API_BASE}/user',headers={'Authorization': r.get('token')})
                rr = await rr.json()
                try:
                    oauth = rr.get('oauth')[0]
                    discordid = int(oauth.get('oauthId',0))
                    if len(oauth) == 0 or discordid != ctx.author.id:
                        return await ctx.reply('This account already has a Discord account linked to it.')
                    elif await ZiplineAuthorizedUser.filter(id=oauth.get('id')).exists():
                        print(oauth)
                        print(discordid)
                        print(ctx.author.id)
                        return await ctx.reply('This account is already linked to your Discord account.')
                    else: 
                        await ZiplineAuthorizedUser.create(
                            id=oauth.get('id'),discordid=discordid,
                            discordusername=oauth.get('username'),
                            provider=oauth.get("provider"),refresh=oauth.get('refresh'),
                            discordtoken=oauth.get('token'),ziplineid=oauth.get('userId'),
                            ziplinetoken=rr.get('token'),admin=rr.get('administrator'))
                        return await ctx.reply('Sucessfully linked your Discord account to your Zipline account.')
                except IndexError:
                    return await ctx.reply("This account cannot have a Discord account attached to it. Are you sure it's yours?")
                except:
                    traceback.print_exc()
                    return await ctx.reply('This account already has a Discord account linked to it.')
        except:
            traceback.print_exc()
            await ctx.reply('An error occured. Please try again later.')

    @zipline.command('unlink',description='Unlink your Zipline account from your Discord account.')
    @ensure_prefix()
    @commands.cooldown(1, 15, BucketType.user)
    async def unlink(self, ctx: commands.Context):
        """Unlink your Aiden's Zipline account from your Discord account. Removes ability to use Zipline commands."""
        try:
            await ctx.defer(ephemeral=True)
            if await ZiplineAuthorizedUser.filter(discordid=ctx.author.id).exists():
                d = dict(await ZiplineAuthorizedUser.get(discordid=ctx.author.id))
                d['olddbid'] = d.pop('dbid')
                d['olddatelogged'] = d.pop('datelogged')
                d['oldlastupdated'] = d.pop('lastupdated')
                await ArchivedZiplineAuthorizedUser.create(**d)
                await ZiplineAuthorizedUser.filter(discordid=ctx.author.id).delete()
                return await ctx.reply('Sucessfully unlinked your Discord account from your Zipline account.')
            else:
                return await ctx.reply('Your Discord account is not linked to a Zipline account.')
        except:
            traceback.print_exc()
            await ctx.reply('An error occured. Please try again later.')
    
    def convert_image(self, fp: Union[Image.Image,BytesIO,bytes,str], format: Literal["png", "jpg"], content_type: Optional[str]=None) -> io.BufferedIOBase:
        """Converts an image to RGB, then returns it.
        fp takes BytesIO or a file path.
        Blocking call."""
        if isinstance(fp, Image.Image):
            image = fp
        elif content_type == "image/heic":
            heif_file = pillow_heif.read_heif(fp)
            image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride, )
        else:
            image = Image.open(fp)
        image.convert("RGB")

        buffer: io.BytesIO = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        return buffer
        
    async def handle_file_upload(self, ctx: Union[discord.Message, commands.Context], attachments: Union[List[Optional[discord.Attachment]], discord.Attachment], user: ZiplineAuthorizedUser, session: Optional[aiohttp.ClientSession]=None) -> bool:
        if not isinstance(attachments, list): attachments = [attachments]
        if isinstance(ctx, commands.Context) and not ctx.interaction:
            await ctx.message.add_reaction(emojidict.get('loading'))
        elif isinstance(ctx, Message):
            await ctx.add_reaction(emojidict.get('loading'))

        images = []
        for image in attachments: 
            if not str(image.content_type).startswith('image'):
                break
        else: # doesn't run if break is called
            return await self.handle_image_upload(ctx, attachments, user, session)

        for tr, image in enumerate(attachments,start=1):
            content_type = ''
            filename = ''
            if not image: continue
            if str(image.content_type) == "image/heic":
                img = await asyncio.to_thread(self.convert_image, await image.read(), 'png',  image.content_type)
                content_type = 'image/png'
                filename = image.filename.replace('HEIC','png')
            else:
                img = await image.read()
            if not content_type: content_type = image.content_type
            if not filename: filename = image.filename
            images.append({'filename': filename, 'content_type': content_type, 'data': img})
        return await self.post_and_reply_with_urls(ctx, images, user, session)

    async def post_and_reply_with_urls(self, ctx: Union[discord.Message, commands.Context], 
    images: List, user: ZiplineAuthorizedUser, session: Optional[aiohttp.ClientSession]) -> bool:
        try:
            urls = await self.post_images(images, user, session)
            ran = urls is not None and len(urls) > 0
        except:
            traceback.print_exc()
            ran = False
        settings = await DBUserSettings.get(userid=ctx.author.id,id=3) # 3 is the DM on CDN upload
        if isinstance(ctx, commands.Context) and not ctx.interaction:
            await ctx.message.remove_reaction(emojidict.get('loading'), self.bot.user)
            if ran: await ctx.message.add_reaction(emojidict.get('check'))
            else:   await ctx.message.add_reaction(emojidict.get('x'))
        elif isinstance(ctx, Message):
            await ctx.remove_reaction(emojidict.get('loading'), self.bot.user)
            if ran: await ctx.add_reaction(emojidict.get('check'))
            else:   await ctx.add_reaction(emojidict.get('x'))
        if ran: content = f"""Hey {ctx.author.mention}, I uploaded your images to the CDN.\n""" + '\n'.join(urls)
        else:   content = "An error occured uploading these images to the CDN. Please try again."
        if settings.value == 'true' and ctx.guild is not None:
            await (await self.getorfetch_dm(ctx.author)).send(
                f"{ctx.jump_url if isinstance(ctx, Message) else ctx.message.jump_url}\n{content}")
        else:
            await ctx.reply(content)
        return ran
    
    async def handle_image_upload(self, ctx: Union[discord.Message, commands.Context], attachments: Union[List[Optional[discord.Attachment]], discord.Attachment], user: ZiplineAuthorizedUser, session: Optional[aiohttp.ClientSession]=None) -> bool:
        if not isinstance(attachments, list): attachments = [attachments]
        images = []
        for tr, image in enumerate(attachments,start=1):
            content_type = ''
            filename = ''
            if not image: continue
            if not image.content_type or not str(image.content_type).startswith('image'):
                return (await ctx.reply(f"You must provide an image file. (Image {tr} is not an image)"))
            elif image.content_type == "image/heic":
                img = await asyncio.to_thread(self.convert_image, await image.read(), 'png', image.content_type)
                content_type = 'image/png'
                filename = image.filename.replace('HEIC','png')
            else:
                img = await image.read()
            if not content_type: content_type = image.content_type
            if not filename: filename = image.filename
            images.append({'filename': filename, 'content_type': content_type, 'data': img})
        return await self.post_and_reply_with_urls(ctx, images, user, session)
        
    @zipline.command(name='convert',description='Converts an image.')
    @commands.cooldown(1, 20, BucketType.user)
    async def convert(self, ctx: commands.Context, image: discord.Attachment, format: Literal['png', 'jpg']):
        """Convert an image to png or jpg. Meant for HEIC images."""
        try:
            await ctx.defer(ephemeral=True)
            if not image or not image.content_type or not str(image.content_type).startswith('image'):
                return (await ctx.reply("You must provide an image."))
            img = await asyncio.to_thread(self.convert_image, await image.read(), format, image.content_type)
            await ctx.reply(file=discord.File(img,filename=image.filename))
        except:
            traceback.print_exc()
            await ctx.reply('An error occured. Please try again later.')

    # lord have mercy
    @zipline.command(name='upload',description='Upload files to your account.')
    @commands.cooldown(1, 15, BucketType.user)
    @app_commands.describe(file1='The file you want to upload.',
    file2='The file you want to upload.',file3='The file you want to upload.',file4='The file you want to upload.',
    file5='The file you want to upload.',file6='The file you want to upload.',file7='The file you want to upload.',
    file8='The file you want to upload.',file9='The file you want to upload.',file10='The file you want to upload.',
    file11='The file you want to upload.',file12='The file you want to upload.',file13='The file you want to upload.',
    file14='The file you want to upload.',file15='The file you want to upload.',file16='The file you want to upload.',
    file17='The file you want to upload.',file18='The file you want to upload.',file19='The file you want to upload.',
    file20='The file you want to upload.',file21='The file you want to upload.',file22='The file you want to upload.',
    file23='The file you want to upload.',file24='The file you want to upload.',file25='The file you want to upload.')
    async def zipline_upload(self, ctx: commands.Context, file1: discord.Attachment,      
    file2:  Optional[discord.Attachment]=None, file3:  Optional[discord.Attachment]=None, file4:  Optional[discord.Attachment]=None, 
    file5:  Optional[discord.Attachment]=None, file6:  Optional[discord.Attachment]=None, file7:  Optional[discord.Attachment]=None, 
    file8:  Optional[discord.Attachment]=None, file9:  Optional[discord.Attachment]=None, file10: Optional[discord.Attachment]=None, 
    file11: Optional[discord.Attachment]=None, file12: Optional[discord.Attachment]=None, file13: Optional[discord.Attachment]=None, 
    file14: Optional[discord.Attachment]=None, file15: Optional[discord.Attachment]=None, file16: Optional[discord.Attachment]=None, 
    file17: Optional[discord.Attachment]=None, file18: Optional[discord.Attachment]=None, file19: Optional[discord.Attachment]=None, 
    file20: Optional[discord.Attachment]=None, file21: Optional[discord.Attachment]=None, file22: Optional[discord.Attachment]=None, 
    file23: Optional[discord.Attachment]=None, file24: Optional[discord.Attachment]=None, file25: Optional[discord.Attachment]=None):
        """Upload file(s) to the Aiden Zipline CDN."""
        await ctx.defer(ephemeral=True)

        files: List[Optional[discord.Attachment]] = [file1, file2, file3, file4, file5, file6, file7, file8, file9, file10,
        file11, file12, file13, file14, file15, file16, file17, file18, file19, file20,
        file21, file22, file23, file24, file25]

        if not await ZiplineAuthorizedUser.filter(discordid=ctx.author.id).exists():
            return await ctx.reply("You must link your Zipline account to your Discord account first.")

        user = await ZiplineAuthorizedUser.get(discordid=ctx.author.id)
        sent = await self.handle_file_upload(ctx, files, user)
    
    async def post_images(self, images: List[Dict[str, str]], user: ZiplineAuthorizedUser, session: Optional[aiohttp.ClientSession]=None) -> Optional[List[str]]:
        """POSTs an image to the CDN. Returns a list of URLs.
        Images: {'data': BytesIO/bytes, 'filename': str, 'content_type': str}}"""
        if not session: session = await get_session()
        data = aiohttp.FormData()
        for image in images:
            data.add_field('file', image.get('data'), filename=image.get('filename'), content_type=image.get('content_type'))
        r = await session.post(f'{API_BASE}/upload',headers={'Authorization': user.ziplinetoken},data=data)
        if r.status == 200:
            urls: list = (await r.json()).get('files')
        else:
            print(r.status)
            print(await r.json())
            return
        return urls

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try:
            if len(msg.attachments) > 0:
                if await ZiplineAuthorizedUser.filter(discordid=msg.author.id).exists():
                    user = await ZiplineAuthorizedUser.get(discordid=msg.author.id)
                    try:
                        sent = await self.handle_file_upload(msg, msg.attachments, user) # type: ignore
                    except: pass
        except:
            traceback.print_exc()
    
async def setup(bot):
    try:
        cog = ZiplineCog(bot)
        await bot.add_cog(cog)
        await main()
    except:
        traceback.print_exc()

async def main():
    await tortoise.Tortoise.init(config_file='config.yml')
    await tortoise.Tortoise.generate_schemas()
    pillow_heif.register_heif_opener()
    #print('loaded DB')

