import discord
from discord import Message
from discord.ext import commands

from spexbot.bot import SpexBot
from spexbot.cogs.forwarding import dm
from spexbot.helpers.validation import is_valid_snowflake


class Forwarding(commands.Cog):
    """Redirects DMs to the destination channel and relays replies back to the sender."""

    def __init__(self, bot: SpexBot):
        self.bot = bot
        self.config = bot.config
        self.database_path = bot.database_path
        self.destination_channel_id = self._load_destination_channel_id()

    def _load_destination_channel_id(self) -> int:
        """Get the destination channel ID from the configuration and validate it."""
        value = self.config.get("destination_channel_id")

        if value is None:
            raise Exception("`destination_channel_id` key not set in config.")  # noqa: TRY002

        try:
            value = int(value)
            assert is_valid_snowflake(value)
        except (ValueError, TypeError, AssertionError):
            raise Exception(f"Value '{value}' of `destination_channel_id` in config is invalid.")  # noqa: TRY002

        return value

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # If the message is in a DM channel that is not the destination channel
        # and the author is not the bot, redirect the message.
        if (
            isinstance(message.channel, discord.DMChannel)
            and message.channel.id != self.destination_channel_id
            and message.author != self.bot.user
        ):
            return await dm.redirect_message(
                self.bot, self.config, self.database_path, message, self.destination_channel_id
            )

        # Check if the message is referencing another message
        if message.reference is not None and message.reference.message_id is not None:
            source_channel_id = await dm.get_source_message_of_redirect(
                self.bot, self.config, self.database_path, message
            )

            if source_channel_id is not None:
                return await dm.redirect_message(
                    self.bot, self.config, self.database_path, message,
                    source_channel_id, create_embed=False,
                )


async def setup(bot: SpexBot):
    await bot.add_cog(Forwarding(bot))