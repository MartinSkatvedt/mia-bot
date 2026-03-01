import discord
from discord.ext import commands

from bot import database

OFFLINE_STATUSES = {discord.Status.offline, discord.Status.invisible}
ONLINE_STATUSES = {discord.Status.online, discord.Status.idle, discord.Status.dnd}


class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            return
        await database.upsert_last_message(
            self.bot.pool, message.guild.id, message.author.id
        )

    @commands.Cog.listener()
    async def on_presence_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        # Record last online when member transitions from online → offline
        if before.status in ONLINE_STATUSES and after.status in OFFLINE_STATUSES:
            await database.upsert_last_online(
                self.bot.pool, after.guild.id, after.id
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Seed last_online for members already offline when bot starts
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot and member.status in OFFLINE_STATUSES:
                    await database.upsert_last_online(
                        self.bot.pool, guild.id, member.id
                    )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tracking(bot))
