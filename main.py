import discord
from discord.ui import Button, View

import os
import yaml

CONFIG_PATH = os.path.join("./config.yaml")

with open(CONFIG_PATH) as config_file:
    config = yaml.load(config_file)

destination_channel_id = config['destination_channel_id']

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

class UnreadMessage(View):
    def __init__(self, dm_channel):
        super().__init__()

        self.dm_channel = dm_channel

    @discord.ui.button(label='Markera som läst', style=discord.ButtonStyle.primary)
    async def mark_as_read(self, interaction: discord.Interaction, button: Button):
        await self.dm_channel.send('Styret har sett ditt meddelande.')
        await interaction.response.edit_message(view=None)

        
        

@client.event
async def on_ready():
    print(f'Login successful as {client.user}')

@client.event
async def on_message(message):
    if not isinstance(message.channel, discord.DMChannel):
        return
    
    if message.author == client.user:
        return
    
    destination_channel = client.get_channel(config['destination_channel_id'])
    guild = client.get_guild(config['nickname_source_guild_id'])
    member = guild.get_member(message.author.id)

    embed = discord.Embed(
        title=f'Meddelande från {member.display_name}',
        description=message.content,
        color=discord.Color.green()
    )

    embed.set_thumbnail(url=message.author.avatar.url)

    view = UnreadMessage(message.channel)

    await destination_channel.send(embed=embed, view=view)

if __name__ == '__main__':
    client.run(config['token'])
