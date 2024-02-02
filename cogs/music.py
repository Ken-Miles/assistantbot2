from __future__ import annotations

import asyncio
import traceback
import re
import datetime
from collections import defaultdict
import os
from pathlib import Path

import discord
from discord import app_commands, guild
from discord.ext import commands
from discord.utils import get
import yt_dlp

from utils import CogU, ContextU, GUILDS, makeembed_bot, dchyperlink, emojidict

MUSIC_MAX_DURATION_MINS = 20
MUSIC_QUEUE_PER_PAGE = 10

class Queue(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_song = None
        self._skip_voters = []

    def next_song(self):
        self._current_song = self.pop(0)

        return self._current_song

    def clear(self):
        super().clear()
        self._current_song = None

    def add_skip_vote(self, voter: discord.Member):
        self._skip_voters.append(voter)

    def clear_skip_votes(self):
        self._skip_voters.clear()

    @property
    def skip_voters(self):
        return self._skip_voters

    @property
    def current_song(self):
        return self._current_song

    def get_embed(self, song_id: int):
        if song_id <= 0:
            song = self.current_song
        else:
            song = self[song_id-1]

        if len(song.description) > 300:
            song['description'] = f'{song.description[:300]}...'

        embed = makeembed_bot(title="Audio Info",color=None,url=song.url)
        embed.set_thumbnail(url=song.thumbnail)
        #embed.add_field(name='Song', value=dchyperlink(song.url,song.title), inline=True)
        embed.add_field(name='Song', value=song.title, inline=True)
        embed.add_field(name='Uploader', value=song.uploader, inline=True)
        embed.add_field(name='Duration', value=song.duration_formatted, inline=True)
        embed.add_field(name='Description', value=song.description, inline=True)
        embed.add_field(name='Upload Date', value=song.upload_date_formatted, inline=True)
        embed.add_field(name='Views', value=song.views, inline=True)
        embed.add_field(name='Likes', value=song.likes, inline=True)
        #embed.add_field(name='Dislikes', value=song.dislikes, inline=True)
        embed.add_field(name='Requested By', value=song.requested_by.mention, inline=True)

        return embed

class SongRequestError(Exception):
    pass

class Song(dict):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    def __init__(self, url: str, author: discord.Member):
        super().__init__()
        self.download_info(url, author)

        if self.duration_raw > MUSIC_MAX_DURATION_MINS*60 and not author.guild_permissions.administrator:
            raise SongRequestError(f'Your song was too long, keep it under {MUSIC_MAX_DURATION_MINS} mins')
        elif self.get('is_live', True):
            raise SongRequestError('Invalid video - either live stream or unsupported website.')
        elif self.url is None:
            raise SongRequestError('Invalid URL provided or no video found.')

    @property
    def url(self):
        return self.get('url', None)

    @property
    def title(self):
        return self.get('title', 'Unable To Fetch')

    @property
    def uploader(self):
        return self.get('uploader', 'Unable To Fetch')

    @property
    def duration_raw(self):
        return self.get('duration', 0)

    @property
    def duration_formatted(self):
        minutes, seconds = self.duration_raw // 60, self.duration_raw % 60
        return f'{minutes}m {seconds}s'
        

    @property
    def description(self):
        return self.get('description', 'Unable To Fetch')

    @property
    def upload_date_raw(self):
        return self.get('upload_date', '01011970')
        #return dctimestamp(datetime.datetime(self.get('upload_date')[:]))

    @property
    def upload_date_formatted(self):
        m, d, y = self.upload_date_raw[4:6], self.upload_date_raw[6:8], self.upload_date_raw[0:4]
        #return f'{m}/{d}/{y}'
        return dctimestamp(datetime.datetime(int(y),int(m),int(d)),"d")

    @property
    def views(self):
        #return self.get('view_count', 0)
        return "{:,}".format(self.get('view_count','0'))

    @property
    def likes(self):
        #return self.get('like_count', 0)
        return "{:,}".format(self.get('like_count','0'))

    @property
    def dislikes(self):
        return self.get('dislike_count', 0)

    @property
    def thumbnail(self):
        return self.get('thumbnail', 'http://i.imgur.com/dDTCO6e.png')

    @property
    def requested_by(self):
        return self.get('requested_by', None)

    def download_info(self, url: str, author: discord.Member):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            self.update(ydl.extract_info(url, download=False)) # type: ignore

            if not url.startswith('https'):
                self.update(ydl.extract_info(self['entries'][0]['webpage_url'], download=False)) # type: ignore

            self['url'] = url
            self['requested_by'] = author

def set_str_len(s: str, length: int):
    '''Adds whitespace or trims string to enforce a specific size'''

    return s.ljust(length)[:length]

class MusicCog(CogU, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        self.music_queues = defaultdict(Queue)

    @commands.hybrid_group(name='music',description="Music commands")
    @app_commands.guilds(*GUILDS)
    async def music(self, ctx: ContextU): pass

    @music.command(name='play')
    async def play(self, ctx: ContextU, *, urlorsong: str):
        '''Adds a song to the queue either by YouTube URL or YouTube Search.'''
        if ctx.guild is None: 
            await ctx.reply("This command can only be used in a server.",delete_after=5,ephemeral=True)
            return

        if not isinstance(ctx.author, discord.Member): return
        
        await ctx.defer()

        music_queue = self.music_queues[ctx.guild]
        voice = get(self.bot.voice_clients, guild=ctx.guild)

        url = urlorsong
    
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.reply("You're not connected to a voice channel.",delete_after=5,ephemeral=True)
            return

        if voice is not None and not self.client_in_same_channel(ctx.author, ctx.guild):
            await ctx.reply("You're not in my voice channel.",delete_after=5,ephemeral=True)
            return
        
        if not re.match("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",urlorsong):
            url = f'ytsearch1:{url} {" ".join(urlorsong)}'
        else:
            url = urlorsong

        try:
            song_ = await asyncio.to_thread(lambda: Song(url, author=ctx.author)) #type: ignore
        except SongRequestError as e:
            await ctx.reply(e.args[0],delete_after=5,ephemeral=True)
            return
        except Exception as e:
            await ctx.reply(f'An error occurred while processing this request. ({e})',delete_after=5,ephemeral=True)
            return

        music_queue.append(song_)
        emb = makeembed_bot(title="Song Queued",description=f"Sucessfully queued song: {dchyperlink(song_.url,song_.title)}",color=discord.Colour.green())
        await ctx.send(embed=emb)
        #logger_music.info(f"Queued song: {song_.title} | Queued by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id})")

        if voice is None or not voice.is_connected():
            await channel.connect()

        await self.play_all_songs(ctx.guild)

    @music.command(name='stop',description="Stops playback and clears the queue.")
    @commands.has_permissions(administrator=True)
    async def stop(self, ctx: ContextU):
        '''Admin command that stops playback of music and clears out the music queue.'''
        
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a server.",delete_after=5,ephemeral=True)
            return
        if not isinstance(ctx.author, discord.Member): return
        await ctx.defer()

        voice = get(self.bot.voice_clients, guild=ctx.guild)
        queue = self.music_queues.get(ctx.guild)

        if self.client_in_same_channel(ctx.author, ctx.guild) or ctx.author.guild_permissions.administrator or voice is not None:
            voice.stop()
            queue.clear()
            ch = ctx.author.voice.channel
            if ch is None and ctx.author.guild_permissions.administrator:
                ch = voice.channel
            if ch is None: # user not admin or in vc
                await ctx.reply("You're not in a voice channel with me.",delete_after=5,ephemeral=True)
                return
            #await set_voice_status(ch, None, [self.bot.session, self.bot.session2, self.bot.session3])
            await voice.disconnect()
            emb = makeembed_bot(title="Music Stopped",description="Stopped playback and cleared queue.",color=discord.Colour.red())
            await ctx.reply(embed=emb)
            ##logger_music.info(f"Stopped playback | Stopped by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id})")
        elif voice := get(self.bot.voice_clients, guild=guild) is not None:
            if voice.channel is not None and len(voice.channel.members) <= 0:
                await ctx.reply("You're not in my voice channel.",delete_after=5,ephemeral=True)
        else:
            await ctx.reply("You're not in my VC.")

    @music.command(name='skip',description="Puts in your vote to skip the currently playing song.")
    async def skip(self, ctx: ContextU):
        '''Puts in your vote to skip the currently played song.'''

        if ctx.guild is None: 
            await ctx.reply("This command can only be used in a server.",delete_after=5,ephemeral=True)
            return
        
        voice = get(self.bot.voice_clients, guild=ctx.guild)

        if not isinstance(ctx.author, discord.Member): return

        await ctx.defer(ephemeral=True)

        if ctx.author.guild_permissions.administrator:
            if not self.client_in_same_channel(ctx.author, ctx.guild):
                await ctx.reply("You're not in a voice channel with me.",delete_after=5,ephemeral=True)
            elif voice is None or not voice.is_playing():
                await ctx.reply("I'm not playing a song right now.",delete_after=5,ephemeral=True)
            else:
                await ctx.reply('Skipping song...')
                await ctx.send(f'Skipping song: {queue.current_song.title}')
                voice.stop()
                #logger_music.info(f"Skipped song: {self.music_queues.get(ctx.guild).current_song.title} | Skipped by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id}) (Admin)")
        else:
            queue = self.music_queues.get(ctx.guild)

            if not self.client_in_same_channel(ctx.author, ctx.guild):
                await ctx.reply("You're not in a voice channel with me.",delete_after=5,ephemeral=True)
                return

            if voice is None or not voice.is_playing():
                await ctx.reply("I'm not playing a song right now.",delete_after=5,ephemeral=True)
                return

            if ctx.author in queue.skip_voters:
                await ctx.reply("You've already voted to skip this song.",delete_after=5,ephemeral=True)
                return

            channel = ctx.author.voice.channel
            required_votes = round(len(channel.members) / 2)

            queue.add_skip_vote(ctx.author)

            if len(queue.skip_voters) >= required_votes:
                await ctx.reply('Skipping song after successful vote...')
                await ctx.send(f'Skipping song: {queue.current_song.title}')
                voice.stop()
                #logger_music.info(f"Skipped song: {self.music_queues.get(ctx.guild).current_song.title} | Skipped by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id}). ({len(queue.skip_voters)}/{required_votes})")
            else:
                await ctx.reply(f'You voted to skip this song. `{required_votes - len(queue.skip_voters)}` more votes are '
                                f'required.')
                #logger_music.info(f"Voted to skip song: {self.music_queues.get(ctx.guild).current_song.title} | Skipped by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id}) ({len(queue.skip_votes)}/{required_votes})")

    @music.command(name='songinfo',description="Print out more information on the song currently playing.")
    async def songinfo(self, ctx: ContextU, song_index: int = 0):
        '''Print out more information on the song currently playing.'''

        if ctx.guild is None:
            await ctx.reply("This command can only be used in a server.",delete_after=5,ephemeral=True)
            return
        if not isinstance(ctx.author, discord.Member): return
        await ctx.defer()

        queue = self.music_queues.get(ctx.guild)

        if song_index not in range(len(queue) + 1):
            await ctx.reply('A song does not exist at that index in the queue.',delete_after=5,ephemeral=True)
            return

        embed = queue.get_embed(song_index)
        await ctx.reply(embed=embed)
        #logger_music.info(f"Sent song info for {queue.current_song.title} | Requested by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id})")

    # combined admin skip into here
    @music.command(name='remove',description="Removes the last song you requested from the queue, or a specific song if queue position specified.")
    async def remove(self, ctx: ContextU, song_id: int = None):
        '''Removes the last song you requested from the queue, or a specific song if queue position specified.'''

        if ctx.guild is None:
            await ctx.reply("This command can only be used in a server.",delete_after=5,ephemeral=True)
            return
        
        if not isinstance(ctx.author, discord.Member): return
        
        await ctx.defer(ephemeral=True)

        if ctx.author.guild_permissions.administrator:
            queue = self.music_queues.get(ctx.guild)

            if not self.client_in_same_channel(ctx.author, ctx.guild):
                await ctx.reply("You're not in a voice channel with me.",delete_after=5,ephemeral=True)
                return

            if song_id is None or 0:
                await ctx.reply("You need to specify a song by it's queue index.",delete_after=5,ephemeral=True)
                return

            try:
                song = queue[song_id - 1]
            except IndexError:
                await ctx.reply('A song does not exist at this queue index.',delete_after=5,ephemeral=True)
                return

            queue.pop(song_id - 1)
            await ctx.reply(f'Removed {song.title} from the queue.')
            #logger_music.info(f"Removed song: {song.title} | Removed by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id}) (Admin)")
            return

        if not self.client_in_same_channel(ctx.author, ctx.guild):
            await ctx.reply("You're not in a voice channel with me.",delete_after=5,ephemeral=True)
            return

        if song_id is None:
            queue = self.music_queues.get(ctx.guild)

            for index, song in reversed(list(enumerate(queue))):
                if ctx.author.id == song.requested_by.id:
                    queue.pop(index)
                    await ctx.reply(f'Song "{song.title}" removed from queue.')
                    #logger_music.info(f"Removed song: {song.title} | Removed by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id})")
                    return
        else:
            queue = self.music_queues.get(ctx.guild)

            try:
                song = queue[song_id - 1]
            except IndexError:
                await ctx.reply('An invalid index was provided.',delete_after=5,ephemeral=True)
                return

            if ctx.author.id == song.requested_by.id:
                queue.pop(song_id - 1)
                await ctx.reply(f'Song {song.title} removed from queue.')
                #logger_music.info(f"Removed song: {song.title} | Removed by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id})")
            else:
                await ctx.reply('You cannot remove a song requested by someone else.',delete_after=5,ephemeral=True)

    @music.command(name="queue",description="Prints out a specified page of the music queue, defaults to first page.")
    async def queue(self, ctx: ContextU, page: app_commands.Range[int, 1, 100] = 1):
        '''Prints out a specified page of the music queue, defaults to first page.'''
        try:
            if ctx.guild is None: 
                await ctx.reply("This command can only be used in a server.",delete_after=5,ephemeral=True)
                return
            
            if not isinstance(ctx.author, discord.Member): return

            await ctx.defer()

            queue = self.music_queues.get(ctx.guild)

            if not self.client_in_same_channel(ctx.author, ctx.guild):
                await ctx.reply("You're not in a voice channel with me.",delete_after=5,ephemeral=True)
                return

            if not queue:
                await ctx.reply("I don't have anything in my queue right now.",delete_after=5,ephemeral=True)
                return

            if len(queue) < MUSIC_QUEUE_PER_PAGE * (page - 1):
                await ctx.reply("I don't have that many pages in my queue.",delete_after=5,ephemeral=True)
                return

            #to_send = f'```\n    {set_str_len("Song", 66)}{set_str_len("Uploader", 36)}Requested By\n'

            to_send = f"Queue position | {'Song':<30} | Uploader\n"

            for pos, song in enumerate(queue[:MUSIC_QUEUE_PER_PAGE * page], start=MUSIC_QUEUE_PER_PAGE * (page - 1)):
                #title = set_str_len(song.title, 65)
                #uploader = set_str_len(song.uploader, 35)
                #to_send += f'{set_str_len(f"{pos + 1})", 4)}{title}|{uploader}|{song.requested_by.display_name}\n'
                to_send += f"`{pos+1})` {(dchyperlink(song.url,song.title)):<30} | {song.requested_by.mention}\n"
            emb = makeembed_bot(title="Music Queue",description=to_send,color=None,footer=f"Page {page}/{len(queue)//MUSIC_QUEUE_PER_PAGE+1}")
            await ctx.reply(embed=emb)
            #logger_music.info(f"Sent queue | Requested by {ctx.author} ({ctx.author.id}) in {ctx.guild} ({ctx.guild.id})")
        except:
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: ContextU, error: commands.CommandError):
        logger_.error(traceback.format_exc()) 

    async def play_all_songs(self, guild: discord.Guild):
        queue = self.music_queues.get(guild)

        # Play next song until queue is empty
        while queue:
            await self.wait_for_end_of_song(guild)

            song = queue.next_song()

            status = f'{emojidict.get("headphones")} {song.title}'

            if song is None:
                status = f'{emojidict.get("headphones")} Nothing.'
            try:
                await set_voice_status(guild.voice_client.channel, status,[self.bot.session, self.bot.session2, self.bot.session3])
            except:
                logger_.error(traceback.format_exc())

            #if song is not None:
            await self.play_song(guild, song)
            if song is not None:
                #logger_music.info(f"Playing song: {song.title} | Requested by {song.requested_by} ({song.requested_by.id}) in {guild} ({guild.id})")
            else:
                #logger_music.info(f"Playing Nothing | {guild} ({guild.id})")
        # Disconnect after song queue is empty
        #logger_music.info(f"Inactivity Disconnect | {guild} ({guild.id})")
        await self.inactivity_disconnect(guild)

    async def play_song(self, guild: discord.Guild, song: Song):
        '''Downloads and starts playing a YouTube video's audio.'''

        audio_dir = os.path.join('.', 'audio')
        audio_path = os.path.join(audio_dir, f'{guild.id}.mp3').replace(".mp3.mp3",".mp3")
        voice = get(self.bot.voice_clients, guild=guild)

        queue = self.music_queues.get(guild)
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': audio_path
        }

        Path(audio_dir).mkdir(parents=True, exist_ok=True)

        try:
            os.remove(audio_path)
        except OSError:
            pass

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                await asyncio.to_thread(ydl.download,[f'{song.url}'])
            except:
                await self.play_all_songs(guild)
                #logger_music.error('Error downloading song. Skipping.')
                return
        
        for file in os.listdir('audio'):
            if ".mp3.mp3" in file:
                os.rename("audio/"+file,"audio/"+file.replace(".mp3.mp3",".mp3"))

        await asyncio.to_thread(voice.play, discord.FFmpegPCMAudio(audio_path))
        queue.clear_skip_votes()

    async def wait_for_end_of_song(self, guild: discord.Guild):
        voice = get(self.bot.voice_clients, guild=guild)
        while voice.is_playing():
            await asyncio.sleep(1)

    async def inactivity_disconnect(self, guild: discord.Guild):
        '''If a song is not played for 5 minutes, automatically disconnects bot from server.'''

        voice = get(self.bot.voice_clients, guild=guild)
        queue = self.music_queues.get(guild)
        last_song = queue.current_song

        while voice.is_playing():
            await asyncio.sleep(10)

        await asyncio.sleep(300)
        if queue.current_song == last_song:
            await set_voice_status(guild.voice_client.channel, None,[self.bot.session, self.bot.session2, self.bot.session3])
            await voice.disconnect()

    def client_in_same_channel(self, author: discord.Member, guild: discord.Guild):
        '''Checks to see if a client is in the same channel as the bot.'''

        voice = get(self.bot.voice_clients, guild=guild)

        try:
            channel = author.voice.channel
        except AttributeError:
            return False

        return voice is not None and voice.is_connected() and channel == voice.channel


async def setup(bot):
    await bot.add_cog(MusicCog(bot))