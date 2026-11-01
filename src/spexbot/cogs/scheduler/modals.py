import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord

from spexbot.helpers.validation import is_valid_snowflake

from ..scheduler import db

logger = logging.getLogger(__name__)


class ScheduleModal(discord.ui.Modal, title="Schemalägg meddelande"):
    def __init__(
        self,
        source: discord.Message,
        tz: str,
        destinations: list[discord.TextChannel | discord.Thread],
        default_channel_id: int | None,
        db_path: str,
    ):
        super().__init__()
        self.source = source
        self.tz = tz
        self.db_path = db_path

        # Modal time input
        self.when: discord.ui.TextInput = discord.ui.TextInput(
            placeholder="YYYY-MM-DD HH:MM",
            min_length=16,
            max_length=16,
        )
        self.add_item(discord.ui.Label(text="Tid", component=self.when))

        # Modal destination dropdown
        self.dest: discord.ui.Select | None = None
        if destinations:
            self.destination: discord.ui.Select = discord.ui.Select(
                placeholder="Välj kanal...",
                options=[
                    discord.SelectOption(
                        label=f"{c.guild.name} / #{c.name}"[:100],
                        value=str(c.id),
                        default=(c.id == default_channel_id),
                    )
                    for c in destinations
                ],
                max_values=1,
            )
            self.add_item(discord.ui.Label(text="Sparade kanaler", component=self.destination))

        # Modal new destination text input
        self.new_destination: discord.ui.TextInput = discord.ui.TextInput(
            placeholder="Kanal-ID eller länk (har företräde om ifyllt)",
            required=False,
            max_length=100,
        )
        self.add_item(discord.ui.Label(text="Ny kanal", component=self.new_destination))

    def _chosen_channel_id(self) -> int | None:
        """The pasted ID wins over the select menu. Returns `None` if neither is usable."""
        pasted = self.new_destination.value.strip()
        if pasted:
            # Either a pure ID or a channel link (.../channels/<guild>/<channel>)
            match = re.search(r"(\d+)/?$", pasted)
            candidate = int(match.group(1)) if match else None
        elif self.destination is not None and self.destination.values:
            candidate = int(self.destination.values[0])
        else:
            return None

        if candidate is None or not is_valid_snowflake(candidate):
            return None

        return candidate

    async def on_submit(self, interaction: discord.Interaction):
        # Parse the time in local time and store it as UTC
        try:
            local = datetime.strptime(self.when.value.strip(), "%Y-%m-%d %H:%M")
            send_at = local.replace(tzinfo=ZoneInfo(self.tz)).astimezone(UTC)
        except ValueError:
            return await interaction.response.send_message(
                "Kan inte tolka tiden. Använd YYYY-MM-DD HH:MM.", ephemeral=True
            )
        if send_at <= datetime.now(UTC):
            return await interaction.response.send_message(
                "Den angivna tiden är i det förflutna."
            )

        # Resolve and validate the destination channel
        channel_id = self._chosen_channel_id()
        if channel_id is None:
            return await interaction.response.send_message(
                "Välj en kanal i listan eller ange ett giltlig kanal.", ephemeral=True
            )

        destination = interaction.client.get_channel(channel_id)

        if destination is None:
            try:
                destination = await interaction.client.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden):
                return await interaction.response.send_message(
                    "Hittar inte kanalen, eller så saknar botten åtkomst.",
                    ephemeral=True,
                )

        if not isinstance(destination, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message(
                "Kanalen är inte av en typ som man kan skicka meddelanden i.",
                ephemeral=True,
            )

        me = destination.guild.me
        if not destination.permissions_for(me).send_messages:
            return await interaction.response.send_message(
                "Botten får inte skicka meddelanden i den kanalen."
            )

        # Defer as attachment downloads can be slow
        await interaction.response.defer(ephemeral=True, thinking=True)

        await db.save_destination(
            self.db_path, destination.id, destination.guild.id, interaction.user.id
        )

        saved = []
        for attatchment in self.source.attachments:
            path = Path(f"attatchments/{self.source.id}_{attatchment.filename}")
            await attatchment.save(path)
            saved.append((attatchment.filename, path))

        # TODO: insert into DB

        await interaction.followup.send(
            f"Schemalagd för <t:{int(send_at.timestamp())}:F> i {destination.mention} ({destination.guild.name})"
        )

    async def on_error(  # type: ignore[override]
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        logger.exception(
            "Schedule modal failed for user %s", interaction.user.id, exc_info=error
        )

        if interaction.response.is_done():
            await interaction.followup.send("Något gick fel.", ephemeral=True)
        else:
            await interaction.response.send_message("Något gick fel.", ephemeral=True)
