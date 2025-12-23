import discord
from discord.ext import commands
import random

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        embed = discord.Embed(
            title="Pong!",
            description=f"Задержка бота: {round(self.bot.latency * 1000)}ms",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="rand")
    async def rand(self, ctx):
        num = random.randint(1, 100)
        embed = discord.Embed(
            title="Случайное число",
            description=f"{num}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
