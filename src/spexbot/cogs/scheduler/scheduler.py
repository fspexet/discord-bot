import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands.cog import _cog_special_method

from spexbot.bot import SpexBot

from . import db
from .modals import ScheduleModal

logger = logging.getLogger(__name__)


class Scheduler(commands.Cog):
    """Allows users to schedule messages cross channels and guilds"""

    def __init__(self, bot: SpexBot):
        self.bot = bot
        self.config = bot.config
        self.database_path = bot.database_path
        self.admin_guild = discord.Object(id=bot.admin_guild_id)

        self.schedule_ctx_menu = app_commands.ContextMenu(
            name="Schemalägg meddelande",   # max 32 characters
            callback=self.schedule_message,
        )

    @_cog_special_method
    async def cog_load(self):
        self.bot.tree.add_command(self.schedule_ctx_menu, guild=self.admin_guild)

    @_cog_special_method
    async def cog_unload(self):
        self.bot.tree.remove_command(
            self.schedule_ctx_menu.name,
            type=self.schedule_ctx_menu.type,
            guild=self.admin_guild
        )

    async def schedule_message(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        tz, default_channel_id = (
            "Europe/Stockholm",
            None,
        )  # TODO: Make this not hard coded

        ids = await db.get_saved_destination_ids(self.database_path)

        # Make sure the user's default channel is always offered, even if it isn't recent
        if default_channel_id is not None and default_channel_id not in ids:
            ids = [default_channel_id, *ids[:24]]

        destinations: list[discord.TextChannel | discord.Thread] = []
        for channel_id in ids:
            channel = self.bot.get_channel(channel_id)
            if (
                isinstance(channel, (discord.TextChannel, discord.Thread))
                and channel.permissions_for(channel.guild.me).send_messages
            ):
                destinations.append(channel)

        await interaction.response.send_modal(
            ScheduleModal(message, tz, destinations, default_channel_id, self.database_path)
        )


async def setup(bot: SpexBot):
    await bot.add_cog(Scheduler(bot))
