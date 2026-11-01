import hashlib
import logging
import sqlite3
from typing import cast

import discord
from discord import Client, Colour, Message, User
from discord.abc import Messageable

from spexbot.helpers.error import handle_error

logger = logging.getLogger(__name__)


async def get_nickname(client: Client, config: dict, author: User, db_path: str, nickname_guild_id: int | None = None) -> str | None:
    """
    A function that tries to get a nickname in one of two ways (in the following priority):

    1. The function checks if there is a nickname stored in the database for the user.

    2. If given a reference to a guild from where to fetch nicknames the function then tries that
    if a nickname was not found in the database.

    ## Parameters

    - `client` The instance of `discord.Client` running the application.

    - `author` A `discord.User` object for the user for which a nickname should be found.

    - `db` An instance of `sqlite3.Connection` connecting to the database where nicknames are stored.

    ### Optional parameters

    - `nickname_guild_id` The ID for a guild from which nicknames should be fetched (Default: `None`)

    ## Returns

    The function returns a `str` with the nickname if one is successfully found and `None` otherwise.
    """

    # Check if there is a registered username in the database
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT nickname FROM nicknames WHERE user_id = ?", [author.id])
        result = cursor.fetchall()
        cursor.close()

    except sqlite3.Error as err:
        await handle_error(client, config, f"Database error: {err}", exc_info=err)
        result = []

    finally:
        if conn is not None:
            conn.close()


    if len(result) != 0:
        # fetchall() returns rows as tuples, so take the first column of the first row
        return result[0][0]

    # Return None if there is no nickname in the database and no guild from which to fetch nicknames
    if nickname_guild_id is None:
        return None

    # Start with trying to find a cached guild
    nickname_guild = client.get_guild(nickname_guild_id)

    # If not found try fetching the guild
    if nickname_guild is None:
        try:
            nickname_guild = await client.fetch_guild(nickname_guild_id)
        except (discord.NotFound, discord.Forbidden) as err:
            await handle_error(client, config, "Nickname guild not able to be fetched.", exc_info=err)
            return None

    # Try to get a cashed member
    member = nickname_guild.get_member(author.id)

    # Otherwise try fetch
    if member is None:
        try:
            member = await nickname_guild.fetch_member(author.id)
        except (discord.NotFound, discord.Forbidden) as err:
            await handle_error(client, config, "Unable to access member from nickname guild.", exc_info=err)
            return None

    return member.display_name

def string_to_rgb(text: str) -> Colour:
    """
    A function that takes a string and generates an RGB colour
    from the MD5 hash of it.

    ## Parameters

    - `text` A string from which to genreate a colour.

    ## Returns

    The function returns an instance of `discord.Colour` based on the hash of
    the input string.
    """

    # Hash the ID
    hash_hex = hashlib.md5(text.encode()).hexdigest()

    # Exrtract RGB values from the hash
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)

    # Bit shift the components and combine them into an int which
    # is fed to the Colour constructor
    return Colour((r << 16) | (g << 8) | b)


async def redirect_message(client: Client, config: dict, db_path: str, message: Message, destination_channel_id: int, nickname_guild_id: int | None = None, create_embed: bool = True):
    """
    Redirects a recieved message to a specified destination channel.

    ## Parameters

    - `client` The instance of `discord.Client` running the application.

    - `config` Configuration object for the application.

    - `db` Path to the database.

    - `message` The `Message` object to be redirected.

    - `destination_channel_id`

    ### Optional parameters

    - `nickname_guil_id` The ID of a guild from which to fetch nicknames for users.
    """

    author = cast(User, message.author)

    # Try to get a nickname
    nickname = await get_nickname(client, config, author, db_path, nickname_guild_id)

    # If a nickname is found assing that as the display name
    # Otherwise assign the display name as the author's username
    if nickname is not None:
        display_name = nickname
    else:
        display_name = author.name

    # TODO: Check for if the author is replying to a message

    # Try to get the destination channel from cached channels
    destination_channel = client.get_channel(destination_channel_id)

    # Otherwise, fetch the destination channel
    if destination_channel is None:
        try:
            destination_channel = await client.fetch_channel(destination_channel_id)
        except (discord.NotFound, discord.Forbidden) as err:
            await handle_error(client, config, "Destination channel not found.", exc_info=err)
            return

    # Make sure the destination channel is of a type in which messages can be sent
    if not isinstance(destination_channel, Messageable):
        await handle_error(client, config, "Destination channel not a messagable channel.", apology_channel=message.channel)
        return

    # Log metadata only, not the message content
    logger.debug("Redirecting message %s from user %s to channel %s", message.id, author.id, destination_channel_id)

    if create_embed:
        # Hash the author id to get an RGB value
        colour = string_to_rgb(str(author.id))

        # Create an embed
        embed = discord.Embed(
            title=f"Meddelande från {display_name}",
            description=message.content,
            colour=colour
        ).set_thumbnail(url=author.display_avatar.url)

        # Send the redirected message
        redirect = await destination_channel.send(embed=embed)
    else:
        redirect = await destination_channel.send(content=message.content)

    logger.info("Redirected message %s to channel %s (redirect id %s)", message.id, destination_channel_id, redirect.id)

    # Write the relation between the messages in the database
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO message_pairings (source_message_id, source_channel_id, redirect_id) VALUES (?, ?, ?)", (message.id, message.channel.id, redirect.id))

        cursor.close()
        conn.commit()

    except sqlite3.Error as err:
        await handle_error(client, config, f"Database error: {err}", exc_info=err)
        if conn is not None:
            conn.rollback()

    finally:
        if conn is not None:
            conn.close()


async def get_source_message_of_redirect(client: Client, config: dict, db_path: str, message: Message) -> int | None:
    # Filter out messages that don't reference another message
    # This removes everything but replies and forwards
    if message.reference is None or message.reference.message_id is None:
        return None

    # Filter out forwards by filtering out messages pointing to different channels
    if message.reference.channel_id != message.channel.id:
        return None

    # Try fetching the referenced message
    try:
        replied_message = await message.channel.fetch_message(message.reference.message_id)
    except (discord.NotFound, discord.Forbidden) as err:
        await handle_error(client, config, f"Unable to fetch referenced message with ID '{message.reference.message_id}'", exc_info=err, apology_channel=message.channel)
        return None

    # If the author of the referenced message is not the bot it is not relevant
    if replied_message.author != client.user:
        return None

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        result = cursor.execute("SELECT source_message_id, source_channel_id FROM message_pairings WHERE redirect_id = ?", [replied_message.id]).fetchone()

        cursor.close()

    except sqlite3.Error as err:
        await handle_error(client, config, f"Database error: {err}", exc_info=err, apology_channel=message.channel)
        result = None

    finally:
        if conn is not None:
            conn.close()

    # If there exists no reference to this message then exit
    if result is None:
        return None

    _source_message_id, source_channel_id = result

    return source_channel_id