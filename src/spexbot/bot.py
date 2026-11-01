import discord
from discord.ext import commands

EXTENSIONS = [
    "spexbot.cogs.forwarding",
]


class SpexBot(commands.Bot):
    """Bot subclass that carries shared state (config, DB path) for the cogs."""

    def __init__(self, config: dict, database_path: str):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

        self.config = config
        self.database_path = database_path

    async def setup_hook(self):
        for extension in EXTENSIONS:
            await self.load_extension(extension)

    async def on_ready(self):
        print(f"Login successful as {self.user}")