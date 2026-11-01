import logging
from typing import Protocol

import discord
from discord import Client, Thread, User
from discord.abc import GuildChannel, Messageable, PrivateChannel

logger = logging.getLogger(__name__)


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

    logger.warning("Could not find a channel or user with ID %s", messagable_id)
    return None

async def handle_error(
    client: Client,
    config: dict,
    error_message: Printable,
    *,
    exc_info: BaseException | None = None,
    apology_channel: Messageable | None = None,
) -> None:
    """
    A function for handeling of recoverable errors.

    The error is always logged (with a traceback if `exc_info` is given),
    and is then optionally sent to the configured error recipient and/or
    an apology is sent to `apology_channel`.
    """

    # Log first so the error is recorded even if sending a message below fails
    logger.error("A recoverable error has occurred: %s", error_message, exc_info=exc_info)

    error_recipient_id = config.get("error_recipient_id")

    # If the error recipient ID is specified and valid: send a message to it
    if error_recipient_id is not None:
        error_recipient_id = int(error_recipient_id)

        error_recipient = await get_generic_messagable(client, error_recipient_id)

        if error_recipient is not None:
            await error_recipient.send(str(error_message))

    # If an apology channel is given: send a message indicating an error has occured
    if apology_channel is not None:
        await apology_channel.send("Ett fel har uppstått. Vänligen kontakta styret om detta.")