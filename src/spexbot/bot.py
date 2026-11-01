import discord
from discord.ext import commands

from spexbot.helpers.validation import is_valid_snowflake

EXTENSIONS = [
    "spexbot.cogs.forwarding",
    "spexbot.cogs.scheduler"
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
        self.admin_guild_id = self._load_admin_guild_id()

    def _load_admin_guild_id(self) -> int:
        value = self.config.get("admin_guild_id")
        try:
            assert value is not None
            value = int(value)
            assert is_valid_snowflake(value)
        except (ValueError, TypeError, AssertionError):
            raise Exception(f"Value '{value}' of `admin_guild_id` in config is invalid or missing.")  # noqa: TRY002
        return value

    async def setup_hook(self):
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        await self.tree.sync(guild=discord.Object(id=self.admin_guild_id))

    async def on_ready(self):
        print(f"Login successful as {self.user}")