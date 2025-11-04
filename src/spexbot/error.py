from typing import Protocol

import sys

import discord
from discord import Client, User, Thread
from discord.abc import Messageable, GuildChannel, PrivateChannel

class Printable(Protocol):
    def __str__(self) -> str:
        ...

async def get_generic_messagable(client: Client, messagable_id: int) -> Messageable | None:
    """
    Gets a generic messagable (channel or user) from an ID.

    ## Parameters

    - `client` The instance of `discord.Client` running the application.

    - `id` The ID of the messagable.

    ## Returns

    Returns a handle to the messagable if found. Otherwise `None`.
    """ 

    target: User | GuildChannel | Thread | PrivateChannel | None 

    # Try a cashed channel
    target = client.get_channel(messagable_id)

    if target is not None and isinstance(target, Messageable):
        return target
    
    # Try fetching a channel
    try:
        target = await client.fetch_channel(messagable_id)
        if isinstance(target, Messageable):
            return target

    except (discord.NotFound, discord.Forbidden):
        pass

    # Try a cashed user
    target = client.get_user(messagable_id)

    if target is not None:
        return target
    
    # Try fetching a user

    try:
        target = await client.fetch_user(messagable_id)
        return target
    except (discord.NotFound, discord.Forbidden):
        pass

    return None

async def handle_error(client: Client, config: dict, error_message: Printable, *, apology_channel: Messageable | None = None) -> None:
    """
    A function for handeling of recoverable errors. 
    """

    error_recipient_id = config.get("error_recipient_id")

    # If the error recipient ID is specified and valid: send a message to it
    if error_recipient_id is not None:
        print("Hej!")
        error_recipient_id = int(error_recipient_id)

        error_recipient = await get_generic_messagable(client, error_recipient_id)

        if error_recipient is not None:
            await error_recipient.send(str(error_message))

    # If an apology channel is given: send a message indicating an error has occured
    if apology_channel is not None:
        await apology_channel.send("Ett fel har uppstått. Vänligen kontakta styret om detta.")

    # Print error to stderr
    print(f"A recoverable error has occured: {error_message}", file=sys.stderr)
    