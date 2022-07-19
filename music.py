import os
import datetime as dt
import discord
from discord.ext import commands
import typing as t
from dotenv import load_dotenv
from lyrics_extractor import SongLyrics

from youtube_dl import YoutubeDL

load_dotenv()

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # All the music related stuff
        self.is_playing = False
        self.is_paused = False

        # For looping
        self.is_loop = False
        self.m_url = ""

        # For lyrics
        self.curr_title = ""

        # 2d array containing [song, channel]
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio', 'nonplaylist': 'True'}
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                               'options': '-vn'}

        self.vc = None

    # Searching the item on youtube
    def search_yt(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info("ytsearch:%s" % item, download=False)['entries'][0]
            except Exception:
                return False

        return {'source': info['formats'][0]['url'], 'title': info['title']}

    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True

            if self.is_loop is False:
                # Get the First URL
                self.m_url = self.music_queue[0][0]['source']
                self.curr_title = self.music_queue[0][0]['title']

                # Remove the first element as you are currently playing it
                self.music_queue.pop(0)

            self.vc.play(discord.FFmpegPCMAudio(
                source=self.m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        elif len(self.music_queue) == 0 and self.is_loop is True:
            self.is_playing = True

            self.vc.play(discord.FFmpegPCMAudio(
                source=self.m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    # Infinite loop checking
    async def play_music(self, ctx):
        if len(self.music_queue) > 0 and self.is_loop is False:
            self.is_playing = True
            self.m_url = self.music_queue[0][0]['source']
            self.curr_title = self.music_queue[0][0]['title']
            # the queue of songs contains a sub-queue(array) of len 2, containing the obj and the voice channel

            # trying to connect the bot to channel is the bot is not already connected to the voice channel
            # trying to call the bot to the specific voice channel (currently where users are)
            if self.vc is None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

            # if the bot fails to connect to the respective vc
            if self.vc is None:
                await ctx.send("The bot could not connect to the voice channel")
                return
            else:
                await self.vc.move_to(self.music_queue[0][1])

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)
            self.vc.play(discord.FFmpegPCMAudio(
                source=self.m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
            # print(type(self.m_url))
        else:
            self.is_playing = False

    def is_present(self, ctx):
        if ctx.author.voice is None:
            return True
        else:
            return False

    @commands.command(name="join", aliases=["j"], help="The bot joins the voice channel")
    async def join(self, ctx):
        if self.is_present(ctx) is True:
            await ctx.send("You're not connected to the voice channel to use these commands")
        else:
            voice_channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                self.vc = await voice_channel.connect()
            else:
                await self.vc.move_to(voice_channel)

    @commands.command(name="play", aliases=["p"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        if self.is_present(ctx) is True:
            await ctx.send("You're not connected to the voice channel to use these commands")
        else:
            query = " ".join(args)

            voice_channel = ctx.author.voice.channel

            if voice_channel is None:
                # you need to be connected so that the  bot knows where to go
                await ctx.send("Connect to a voice channel yar kaisa horay")
            elif self.is_paused and len(args) == 0:
                self.vc.resume()
            else:
                song = self.search_yt(query)
                if type(song) is type(True):
                    await ctx.send(
                        "Could not get the song. Incorrect format try another keyword. This could be due to playlist or a livestream format")
                else:
                    await ctx.send(song['title'])
                    self.music_queue.append([song, voice_channel])

                    if self.is_playing is False:
                        await self.play_music(ctx)

    @commands.command(name="pause", aliases=["ps"], help="Pauses the current song being played")
    async def pause(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            # if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            # elif self.is_paused:
            #     self.vc.resume()

    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            if self.is_paused:
                self.vc.resume()

    @commands.command(name="current", aliases=["curr"], help="Gets the current title of the song that is playing")
    async def current(self, ctx):
        if self.is_present(ctx) is True:
            await ctx.send("You're not connected to the vice channel to use these commands")
        else:
            if self.curr_title == "":
                await ctx.send("There are no tracks playing at the moment")
            else:
                await ctx.send("Currently Playing: " + self.curr_title)

    @commands.command(name="lyrics", help="Gets the lyrics of the given or current song")
    async def lyrics(self, ctx, name: t.Optional[str]):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            name = name or self.curr_title

            extract_lyrics = SongLyrics(os.getenv("LYRICS_API_KEY"), os.getenv("GCS_ENGINE_ID"))

            res = extract_lyrics.get_lyrics(name)

            embed = discord.Embed(
                title=res['title'],
                description=res['lyrics'],
                colour=ctx.author.color,
                timestamp=dt.datetime.utcnow()
            )
            await ctx.send(embed=embed)

    @commands.command(name="skip", aliases=["s"], help="Skips the current song begin played")
    async def skip(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            if self.vc is not None and self.vc:
                self.vc.stop()
                # Try to play next in the queue if it exists
                await self.play_music(ctx)

    @commands.command(name="remove", help="Removes the first track ")
    async def remove(self, ctx, position: t.Optional[int]):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            position = position or len(self.music_queue)
            self.music_queue.pop(position - 1)
            await ctx.send("Track at position {} removed!!".format(position))


    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            retval = "Songs in the queue are:\n"
            for i in range(0, len(self.music_queue)):
                # Display all songs
                retval += "{}) {}".format((i + 1), self.music_queue[i][0]['title']) + "\n"

            if len(self.music_queue) != 0:
                await ctx.send(retval)
            else:
                await ctx.send("No music in queue")

    @commands.command(name="loop", help="Loops the currently playing track")
    async def loop(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            self.is_loop = True
            await ctx.send("Looping the current song!")

    @commands.command(name="loop_off", aliases=["lo"], help="Loops the currently playing track")
    async def loopOff(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            self.is_loop = False
            await ctx.send("Looping disabled!")

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            if self.vc != None and self.is_playing:
                self.vc.stop()
            self.music_queue = []
            self.m_url = ""
            self.curr_title = ""
            await ctx.send("Music queue cleared")

    @commands.command(name="stop", aliases=["st"], help="Stops the music and clears the queue")
    async def stop(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            if self.vc != None and self.is_playing:
                self.vc.stop()
            self.music_queue = []
            self.m_url = ""
            self.curr_title = ""

    @commands.command(name="dc", aliases=["disconnect", "l", "d", "leave"], help="Kick the bot from the VC")
    async def dc(self, ctx):
        if self.is_present(ctx):
            await ctx.send("You are not connected to any voice channel!!!")
        else:
            self.is_playing = False
            self.is_paused = False
            await self.vc.disconnect()
