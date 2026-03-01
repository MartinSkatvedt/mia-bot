import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot import database

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]

COGS = [
    "bot.cogs.tracking",
    "bot.cogs.commands",
]


class MiaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.presences = True
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        self.pool = await database.init_pool(DATABASE_URL)
        for cog in COGS:
            await self.load_extension(cog)

    async def close(self) -> None:
        await self.pool.close()
        await super().close()


async def main() -> None:
    bot = MiaBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
