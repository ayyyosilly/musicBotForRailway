import asyncio
import os
from discord.ext import commands
import discord

# Загружаем токен из переменной окружения
TOKEN = os.environ.get("DISCORD_TOKEN")

# Проверка токена
if not TOKEN:
    raise ValueError("DISCORD_TOKEN не задан! Задайте переменную окружения на Railway.")

# Настраиваем интенты
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.playing, name="Try !help")
    )
    print(f"{bot.user} онлайн и готов к работе!")

# Обработка текстовых команд
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"COG загружен: {filename}")
            except Exception as e:
                print(f"Не удалось загрузить {filename}: {e}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

HELP_DATA = {
    "Музыка": {
        "join": {"aliases": ["j"], "desc": "Бот подключается к вашему голосовому каналу"},
        "leave": {"aliases": ["l", "disconnect"], "desc": "Бот отключается от голосового канала"},
        "play": {"aliases": ["p"], "desc": "Воспроизводит трек или плейлист из SoundCloud"},
        "skip": {"aliases": ["s", "next"], "desc": "Пропускает текущий трек"},
        "pause": {"aliases": ["ps"], "desc": "Ставит текущий трек на паузу"},
        "resume": {"aliases": ["r"], "desc": "Возобновляет воспроизведение трека"},
        "previous": {"aliases": ["prev"], "desc": "Проигрывает предыдущий трек в очереди"},
        "queue": {"aliases": ["q"], "desc": "Показывает текущую очередь треков (максимум 10)"}
    },
    "Утилиты": {
        "ping": {"aliases": [], "desc": "Проверяет отклик бота"},
        "help": {"aliases": ["h", "помощь"], "desc": "Показывает справку по командам"}
    }
}

@bot.command(name="help", aliases=["h", "помощь"])
async def help_command(ctx, *, arg: str = None):
    embed = discord.Embed(color=discord.Color.blurple())
    try:
        if arg is None:
            embed.title = "Справка по боту"
            embed.description = (
                "Введите команду `!help <команда>` чтобы узнать больше о команде.\n"
                "Введите `!help <категория>` чтобы узнать больше о категории.\n\n"
                "**Категории команд:**"
            )
            for category in HELP_DATA:
                embed.add_field(name=category, value="\u200b", inline=False)
            await ctx.send(embed=embed)
            return

        for category, commands_dict in HELP_DATA.items():
            if arg.lower() == category.lower():
                embed.title = f"Категория: {category}"
                for cmd, info in commands_dict.items():
                    aliases = f" (aliases: {', '.join(info['aliases'])})" if info['aliases'] else ""
                    embed.add_field(name=f"`{cmd}`{aliases}", value=info['desc'], inline=False)
                await ctx.send(embed=embed)
                return

        for category, commands_dict in HELP_DATA.items():
            for cmd, info in commands_dict.items():
                if arg.lower() == cmd.lower() or arg.lower() in [a.lower() for a in info['aliases']]:
                    embed.title = f"Команда: {cmd}"
                    aliases = f" (aliases: {', '.join(info['aliases'])})" if info['aliases'] else ""
                    embed.add_field(name=f"{cmd}{aliases}", value=info['desc'], inline=False)
                    await ctx.send(embed=embed)
                    return

        embed.title = "Ошибка"
        embed.description = f"Команда или категория `{arg}` не найдена."
        await ctx.send(embed=embed)
    except Exception as e:
        embed.title = "Ошибка в help"
        embed.description = str(e)
        await ctx.send(embed=embed)

if __name__ == "__main__":
    asyncio.run(main())
