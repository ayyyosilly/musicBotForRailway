import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import datetime
import os

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc = {}
        self.queue = {}
        self.queue_index = {}
        self.is_playing = {}
        self.is_paused = {}
        self.now_playing_msg = {}
        self.elapsed = {}

        self.YTDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': True}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
            'executable': os.environ.get("FFMPEG_PATH", "ffmpeg")
        }

    # ---------------- Commands ----------------
    @commands.command(name="join", aliases=["j"])
    async def join(self, ctx):
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(description="Вы должны быть в голосовом канале!", color=discord.Color.red()))
            return
        channel = ctx.author.voice.channel
        guild_id = ctx.guild.id
        if guild_id not in self.vc or not self.vc[guild_id] or not self.vc[guild_id].is_connected():
            self.vc[guild_id] = await channel.connect()
        else:
            await self.vc[guild_id].move_to(channel)
        await ctx.send(embed=discord.Embed(description=f"Подключился к {channel.name}", color=discord.Color.green()))

    @commands.command(name="leave", aliases=["l", "disconnect"])
    async def leave(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.vc and self.vc[guild_id] and self.vc[guild_id].is_connected():
            await self.vc[guild_id].disconnect()
            self.vc[guild_id] = None
            self.queue[guild_id] = []
            self.queue_index[guild_id] = 0
            self.is_playing[guild_id] = False
            self.is_paused[guild_id] = False
            self.elapsed[guild_id] = 0
            await ctx.send(embed=discord.Embed(description="Отключился от голосового канала", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Я не подключен к голосовому каналу", color=discord.Color.red()))

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, search):
        guild_id = ctx.guild.id
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(description="Вы должны быть в голосовом канале!", color=discord.Color.red()))
            return
        if guild_id not in self.vc or not self.vc[guild_id] or not self.vc[guild_id].is_connected():
            self.vc[guild_id] = await ctx.author.voice.channel.connect()

        if guild_id not in self.queue:
            self.queue[guild_id] = []
            self.queue_index[guild_id] = 0
            self.is_playing[guild_id] = False
            self.is_paused[guild_id] = False
            self.elapsed[guild_id] = 0

        songs = await self.get_songs(search)
        if not songs:
            await ctx.send(embed=discord.Embed(description="Не удалось найти видео или плейлист", color=discord.Color.red()))
            return

        self.queue[guild_id].extend(songs)
        await ctx.send(embed=discord.Embed(description=f"Добавлено {len(songs)} треков в очередь", color=discord.Color.green()))

        if not self.is_playing[guild_id]:
            await self._play_next(ctx)

    @commands.command(name="skip", aliases=["s", "next"])
    async def skip(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.vc and self.vc[guild_id].is_playing():
            self.vc[guild_id].stop()
            await ctx.send(embed=discord.Embed(description="Пропущен текущий трек", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Сейчас ничего не играет", color=discord.Color.red()))

    @commands.command(name="pause", aliases=["ps"])
    async def pause(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.vc and self.vc[guild_id].is_playing():
            self.vc[guild_id].pause()
            self.is_paused[guild_id] = True
            self.is_playing[guild_id] = False
            await ctx.send(embed=discord.Embed(description="Пауза включена", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Сейчас ничего не играет", color=discord.Color.red()))

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.vc and self.is_paused.get(guild_id, False):
            self.vc[guild_id].resume()
            self.is_paused[guild_id] = False
            self.is_playing[guild_id] = True
            await ctx.send(embed=discord.Embed(description="Воспроизведение возобновлено", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Сейчас нет паузы", color=discord.Color.red()))

    @commands.command(name="previous", aliases=["prev"])
    async def previous(self, ctx):
        guild_id = ctx.guild.id
        if self.queue_index.get(guild_id, 0) > 1:
            self.queue_index[guild_id] -= 2
            self.vc[guild_id].stop()
            await ctx.send(embed=discord.Embed(description="Проигрывается предыдущий трек", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Предыдущего трека нет", color=discord.Color.red()))

    @commands.command(name="queue", aliases=["q"])
    async def queue_cmd(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.queue or not self.queue[guild_id]:
            await ctx.send(embed=discord.Embed(description="Очередь пуста", color=discord.Color.red()))
            return
        embed = discord.Embed(title="Очередь треков", color=discord.Color.green())
        for i, song in enumerate(self.queue[guild_id][self.queue_index[guild_id]:self.queue_index[guild_id]+10], start=1):
            embed.add_field(name=f"{i}. {song.get('title', 'Неизвестно')}", value=f"Автор: {song.get('uploader', 'Unknown')}", inline=False)
        await ctx.send(embed=embed)

    # ---------------- Internal ----------------
    async def _play_next(self, ctx):
        guild_id = ctx.guild.id
        if self.queue_index[guild_id] >= len(self.queue[guild_id]):
            self.is_playing[guild_id] = False
            self.elapsed[guild_id] = 0
            return

        # Удаляем старый embed
        try:
            if guild_id in self.now_playing_msg and self.now_playing_msg[guild_id]:
                await self.now_playing_msg[guild_id].delete()
        except:
            pass

        self.is_playing[guild_id] = True
        self.is_paused[guild_id] = False
        self.elapsed[guild_id] = 0
        song = self.queue[guild_id][self.queue_index[guild_id]]
        self.vc[guild_id].play(
            discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS),
            after=lambda e: self.bot.loop.create_task(self._after_song(ctx))
        )

        embed = discord.Embed(title=None, description=None, color=discord.Color.green())
        if 'thumbnail' in song:
            embed.set_image(url=song['thumbnail'])
        title = song.get('title', 'Неизвестно')
        author = song.get('uploader', 'Unknown')
        embed.add_field(name="Трек", value=f"**{title}** – {author}", inline=False)
        embed.add_field(name="Прогресс", value="0:00 ─+─────────────────── 0:00", inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="⏮ Previous", style=discord.ButtonStyle.secondary, custom_id="previous"))
        view.add_item(discord.ui.Button(label="⏯ Pause/Resume", style=discord.ButtonStyle.primary, custom_id="pause_resume"))
        view.add_item(discord.ui.Button(label="⏭ Skip", style=discord.ButtonStyle.success, custom_id="skip"))
        view.add_item(discord.ui.Button(label="⏹ Stop", style=discord.ButtonStyle.danger, custom_id="stop"))

        msg = await ctx.send(embed=embed, view=view)
        self.now_playing_msg[guild_id] = msg

        for button in view.children:
            async def button_callback(interaction: discord.Interaction, btn=button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Вы не можете управлять этой музыкой!", ephemeral=True)
                    return
                if btn.custom_id == "pause_resume":
                    if self.is_paused.get(guild_id, False):
                        self.vc[guild_id].resume()
                        self.is_paused[guild_id] = False
                        self.is_playing[guild_id] = True
                    else:
                        self.vc[guild_id].pause()
                        self.is_paused[guild_id] = True
                        self.is_playing[guild_id] = False
                elif btn.custom_id == "skip":
                    self.vc[guild_id].stop()
                elif btn.custom_id == "stop":
                    self.vc[guild_id].stop()
                    self.queue_index[guild_id] = len(self.queue[guild_id])
                elif btn.custom_id == "previous":
                    if self.queue_index[guild_id] > 0:
                        self.queue_index[guild_id] -= 2
                        self.vc[guild_id].stop()
                await interaction.response.defer()

            button.callback = button_callback

        asyncio.create_task(self.start_timer(ctx, guild_id, int(song.get('duration', 0))))

    async def start_timer(self, ctx, guild_id, duration):
        bar_length = 20
        msg = self.now_playing_msg[guild_id]
        embed = msg.embeds[0]
        prev_elapsed = -1
        while self.is_playing.get(guild_id, False) and self.queue_index[guild_id] < len(self.queue[guild_id]):
            if not self.is_paused.get(guild_id, False):
                self.elapsed[guild_id] += 0.25
                elapsed_sec = int(self.elapsed[guild_id])
                if elapsed_sec != prev_elapsed:
                    prev_elapsed = elapsed_sec
                    duration_sec = int(duration)
                    progress_ratio = min(self.elapsed[guild_id] / duration_sec, 1) if duration_sec > 0 else 0
                    progress_pos = int(progress_ratio * bar_length)
                    progress_bar = '─' * progress_pos + '+' + '─' * (bar_length - progress_pos - 1)

                    embed.set_field_at(1, name="Прогресс",
                                       value=f"{str(datetime.timedelta(seconds=elapsed_sec))} {progress_bar} {str(datetime.timedelta(seconds=duration_sec))}",
                                       inline=False)
                    try:
                        await msg.edit(embed=embed)
                    except:
                        pass
            await asyncio.sleep(0.25)

    async def _after_song(self, ctx):
        guild_id = ctx.guild.id
        self.queue_index[guild_id] += 1
        await self._play_next(ctx)

    async def get_songs(self, search):
        ydl_opts = self.YTDL_OPTIONS.copy()
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                if search.startswith("http"):
                    info = ydl.extract_info(search, download=False)
                    if "entries" in info:
                        return [{'source': track['formats'][0]['url'], 'title': track['title'], 'thumbnail': track.get('thumbnail'),
                                 'duration': track.get('duration'), 'uploader': track.get('uploader')} for track in info['entries']]
                    else:
                        return [{'source': info['formats'][0]['url'], 'title': info['title'], 'thumbnail': info.get('thumbnail'),
                                 'duration': info.get('duration'), 'uploader': info.get('uploader')}]
                else:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
                    return [{'source': info['formats'][0]['url'], 'title': info['title'], 'thumbnail': info.get('thumbnail'),
                             'duration': info.get('duration'), 'uploader': info.get('uploader')}]
            except Exception:
                return None

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
