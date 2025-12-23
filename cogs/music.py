import discord
from discord.ext import commands
import yt_dlp
import asyncio
import datetime

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.vc = {}
        self.queue = {}
        self.queue_index = {}
        self.is_playing = {}
        self.is_paused = {}

        self.YTDL_OPTIONS = {
            "format": "bestaudio/best",
            "quiet": True,
            "noplaylist": True
        }

        self.FFMPEG_OPTIONS = {
            "before_options": (
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 5 "
                "-protocol_whitelist file,http,https,tcp,tls"
            ),
            "options": "-vn -loglevel error"
        }


    # -------------------- COMMANDS --------------------

    @commands.command(name="join", aliases=["j"])
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("Вы должны быть в голосовом канале")

        channel = ctx.author.voice.channel
        self.vc[ctx.guild.id] = await channel.connect()
        await ctx.send(f"Подключился к **{channel.name}**")

    @commands.command(name="leave", aliases=["l", "disconnect"])
    async def leave(self, ctx):
        vc = self.vc.get(ctx.guild.id)
        if vc:
            await vc.disconnect()
            self.vc.pop(ctx.guild.id, None)
            self.queue.pop(ctx.guild.id, None)
            self.queue_index.pop(ctx.guild.id, None)
            self.is_playing.pop(ctx.guild.id, None)
            self.is_paused.pop(ctx.guild.id, None)
            await ctx.send("Отключился от голосового канала")

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query):
        print("PLAY COMMAND:", query)

        if not ctx.author.voice:
            return await ctx.send("Вы должны быть в голосовом канале")

        guild_id = ctx.guild.id

        if guild_id not in self.vc or not self.vc[guild_id].is_connected():
            self.vc[guild_id] = await ctx.author.voice.channel.connect()

        if guild_id not in self.queue:
            self.queue[guild_id] = []
            self.queue_index[guild_id] = 0
            self.is_playing[guild_id] = False
            self.is_paused[guild_id] = False

        song = await self.get_song(query)
        if not song:
            return await ctx.send("Не удалось получить аудио")

        self.queue[guild_id].append(song)
        await ctx.send(f"Добавлено в очередь: **{song['title']}**")

        if not self.is_playing[guild_id]:
            await self.play_next(ctx)

    @commands.command(name="skip", aliases=["s", "next"])
    async def skip(self, ctx):
        vc = self.vc.get(ctx.guild.id)
        if vc and vc.is_playing():
            vc.stop()
            await ctx.send("Трек пропущен")

    @commands.command(name="pause", aliases=["ps"])
    async def pause(self, ctx):
        vc = self.vc.get(ctx.guild.id)
        if vc and vc.is_playing():
            vc.pause()
            self.is_paused[ctx.guild.id] = True
            await ctx.send("Пауза")

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        vc = self.vc.get(ctx.guild.id)
        if vc and vc.is_paused():
            vc.resume()
            self.is_paused[ctx.guild.id] = False
            await ctx.send("Продолжено")

    @commands.command(name="previous", aliases=["prev"])
    async def previous(self, ctx):
        gid = ctx.guild.id
        if self.queue_index.get(gid, 0) > 0:
            self.queue_index[gid] -= 2
            self.vc[gid].stop()
            await ctx.send("Предыдущий трек")

    @commands.command(name="queue", aliases=["q"])
    async def queue_cmd(self, ctx):
        q = self.queue.get(ctx.guild.id)
        if not q:
            return await ctx.send("Очередь пуста")

        text = ""
        for i, song in enumerate(q[:10], start=1):
            text += f"{i}. {song['title']}\n"

        await ctx.send(f"**Очередь:**\n{text}")

    # -------------------- INTERNAL --------------------

    async def play_next(self, ctx):
        guild_id = ctx.guild.id

        if self.queue_index[guild_id] >= len(self.queue[guild_id]):
            self.is_playing[guild_id] = False
            return

        song = self.queue[guild_id][self.queue_index[guild_id]]
        self.is_playing[guild_id] = True

        print("STARTING PLAYBACK")
        print("AUDIO URL:", song["source"])

        def after_playing(error):
            if error:
                print("PLAYER ERROR:", error)

            fut = asyncio.run_coroutine_threadsafe(
                self.after_song(ctx),
                self.bot.loop
            )
            try:
                fut.result()
            except:
                pass

        self.vc[guild_id].play(
            discord.FFmpegPCMAudio(song["source"], **self.FFMPEG_OPTIONS),
            after=after_playing
        )

        await ctx.send(f"▶ Сейчас играет: **{song['title']}**")

    async def after_song(self, ctx):
        gid = ctx.guild.id
        self.queue_index[gid] += 1
        await self.play_next(ctx)

    async def get_song(self, query):
        try:
            with yt_dlp.YoutubeDL(self.YTDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)

                if "entries" in info:
                    info = info["entries"][0]

                formats = [f for f in info["formats"] if f.get("acodec") != "none"]
                audio_url = formats[0]["url"]

                return {
                    "title": info.get("title"),
                    "source": audio_url,
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail")
                }
        except Exception as e:
            print("YTDLP ERROR:", e)
            return None


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
