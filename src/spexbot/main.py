import discord
from discord import Message

import os
import yaml

from spexbot import database, dm
from spexbot.validation import is_valid_snowflake

CONFIG_PATH = os.path.join("./config.yaml")
DATABASE_PATH = os.path.join("./data.db")

with open(CONFIG_PATH) as config_file:
    config = yaml.load(config_file, Loader=yaml.Loader)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)

# Set up the database
database.setup(DATABASE_PATH)

# Get value ID for the destination channel from the configuration and validate it
destination_channel_id = config.get("destination_channel_id")

if destination_channel_id is None:
    raise Exception("`destination_channel_id` key not set in config.")
else: 
    try:
        destination_channel_id = int(destination_channel_id)
        assert is_valid_snowflake(destination_channel_id)
    except (ValueError, TypeError, AssertionError):
        raise Exception(f"Value '{destination_channel_id}' of `destination_chanel_id`  in config is invalid.")


@client.event
async def on_ready():
    print(f'Login successful as {client.user}')


@client.event
async def on_message(message: Message):
    # If the message is in a DM channel that is not the destination channel and the author is not the bot redirect the message
    if isinstance(message.channel, discord.DMChannel) and message.channel.id != destination_channel_id and message.author != client.user:
        return await dm.redirect_message(client, config, DATABASE_PATH, message, destination_channel_id)

    # Check if the message is referencing another message
    if message.reference is not None and message.reference.message_id is not None:
        source_channel_id = await dm.get_source_message_of_redirect(client, config, DATABASE_PATH, message)

        if source_channel_id is not None:
            return await dm.redirect_message(client, config, DATABASE_PATH, message, source_channel_id, create_embed=False)
            

def main():
    print("Halloj!")
    client.run(config['token'])
