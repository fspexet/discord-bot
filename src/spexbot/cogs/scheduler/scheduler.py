import logging
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord

logger = logging.getLogger(__name__)

class ScheduleModal(discord.ui.Modal, title="Schemalägg meddelande"):
    when: discord.ui.TextInput = discord.ui.TextInput(
        label="Skicka den",
        placeholder="YYYY-MM-DD HH:MM",
        min_length=16,
        max_length=16
    )
    # TODO: Make this a Select instead
    channel: discord.ui.TextInput = discord.ui.TextInput(
        label="Destinationskanal",
        placeholder="Lämna blank för din standard",
        required=False,
    )

    def __init__(self, source: discord.Message, tz: str, default_channel_id: int | None):
        super().__init__()
        self.source = source
        self.tz = tz
        if default_channel_id is not None:
            self.channel.default = str(default_channel_id)

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
            return await interaction.response.send_message("Den angivna tiden är i det förflutna.")

        # Resolve and validate the destination channel
        channel_id = int(self.channel.value) if self.channel.value.strip().isdigit() else None
        destination = interaction.client.get_channel(channel_id) if channel_id else None
        if destination is None:
            return await interaction.response.send_message(
                "Okänd kanal, eller så kan botten inte skicka dit.", ephemeral=True
            )

        if not isinstance(destination, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message(
                "Okänd kanal, eller så kan botten inte skicka dit.", ephemeral=True
            )

        # Defer as attachment downloads can be slow
        await interaction.response.defer(ephemeral=True, thinking=True)

        saved = []
        for attatchment in self.source.attachments:
            path = Path(f"attatchments/{self.source.id}_{attatchment.filename}")
            await attatchment.save(path)
            saved.append((attatchment.filename, path))

        # TODO: insert into DB

        await interaction.followup.send(
            f"Schemalagd för <t:{int(send_at.timestamp())}:F> i {destination.mention} ({destination.guild.name})"
        )

    async def on_error( # type: ignore[override]
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        logger.exception("Schedule modal failed for user %s", interaction.user.id, exc_info=error)
        
        if interaction.response.is_done():
            await interaction.followup.send("Något gick fel.", ephemeral=True)
        else:
            await interaction.response.send_message("Något gick fel.", ephemeral=True)
        


        