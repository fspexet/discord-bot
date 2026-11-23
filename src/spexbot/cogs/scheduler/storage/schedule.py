import shutil
import time
import uuid
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import aiosqlite
import discord


@dataclass(frozen=True)
class StoredAttatchment:
    filename: str
    local_path: str


@dataclass(frozen=True)
class ScheduledMessage:
    id: int
    author_id: int
    content: str
    dest_channel_id: int
    dest_guild_id: int
    send_at: int
    attatchments: list[StoredAttatchment]


@asynccontextmanager
async def _connection(db_path: str) -> AsyncGenerator[aiosqlite.Connection]:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


async def fail_interrupted(db_path: str) -> int:
    """
    Assume messages left in 'sending' over a restart or crash will have failed
    and mark them as such rather than risking posting them twice.

    ## Parameters

    - `db_path` The path to the sqlite database.

    ## Returns

    The number of messages affected.
    """
    async with _connection(db_path) as db:
        cursor = await db.execute("""
            UPDATE scheduled_messages SET 
                status = 'failed',
                error = 'Interrupted by a restart; it may or may not have been sent.'
            WHERE status = 'sending'
        """)
        await db.commit()
        return cursor.rowcount

# ==================================================
#                    Attachments
# ==================================================

async def save_attatchments(
    base_dir: str, attatchments: Sequence[discord.Attachment]
) -> tuple[Path | None, list[StoredAttatchment]]:
    """
    Download the attachments into a new folder created for this message.

    ## Parameters

    - `base_dir` The root folder for the attachments.

    ## Returns

    The folder and the stored files therein.
    """

    if not attatchments:
        return None, []

    folder = Path(base_dir) / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)

    stored: list[StoredAttatchment] = []
    try:
        for index, attatchment in enumerate(attatchments):
            safe_name = Path(attatchment.filename).name or f"file{index}"
            path = folder / f"{index}_{safe_name}"
            await attatchment.save(path)
            stored.append(StoredAttatchment(filename=safe_name, local_path=str(path)))
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

    return folder, stored

# ==================================================
#                     Messages
# ==================================================

async def create_scheduled_message(
        db_path: str,
        *,
        author_id: int,
        content: str,
        dest_channel_id: int,
        dest_guild_id: int,
        send_at: int,
        attachments: Sequence[StoredAttatchment],
) -> int:
    """
    Inserts a pending message and its attachments into one transaction.

    ## Returns

    The ID of the database entry.
    """
    async with _connection(db_path) as db:
        cursor = await db.execute("""
            INSERT INTO scheduled_messages (
                author_id, content, dest_channel_id, dest_guild_id, send_at, created at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (author_id, content, dest_channel_id, dest_guild_id, send_at, int(time.time()))
        )
        message_id = cursor.lastrowid
        assert message_id is not None

        await db.executemany(
            "INSERT INTO scheduled_attatchments (message_id, filename, local_path) VALUES (?, ?, ?)",
            [(message_id, a.filename, a.local_path) for a in attachments]
        )
        await db.commit()
        return message_id

async def claim_due(db_path: str, now: int, limit: int = 20) -> list[ScheduledMessage]:
    """
    Change due messages from 'pending' to 'sending'.

    ## Returns

    Due messages.
    """
    async with _connection(db_path) as db:
        cursor = await db.execute("""
            UPDATE scheduled_messages
            SET status = 'sending'
            WHERE id IN (
                SELECT id FROM scheduled_messages
                WHERE status = 'pending' AND send_at <= ?
                ORDER BY send_at
                LIMIT ?
            )
            RETURNING id, author_id, content, dest_channel_id, dest_guild_id, send_at
            """, (now, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        attachments_by_message: dict[int, list[StoredAttatchment]] = {}
        if rows:
            ids = [row[0] for row in rows]
            placeholders = ",".join("?" * len(ids))
            async with db.execute(
                f"SELECT message_id, filename, local_path FROM scheduled_attachments "
                f"WHERE message_id IN ({placeholders}) ORDER BY id",
                ids
            ) as attachment_cursor:
                async for message_id, filename, local_path in attachment_cursor:
                    attachments_by_message.setdefault(message_id, []).append(
                        StoredAttatchment(filename, local_path)
                    )

        await db.commit()

    messages = [
        ScheduledMessage(
            id=row[0],
            author_id=row[1],
            content=row[2],
            dest_channel_id=row[3],
            dest_guild_id=row[4],
            send_at=row[5],
            attatchments=attachments_by_message.get(row[0], []),
        )
        for row in rows
    ]
    return sorted(messages, key=lambda m: m.send_at)


async def mark_sent(db_path: str, message_id: int) -> None:
    async with _connection(db_path) as db:
        await db.execute(
            "UPDATE scheduled_messages SET status = 'sent', sent_at = ? WHERE id = ?",
            (int(time.time()), message_id),
        )
        await db.commit()
 
 
async def mark_failed(db_path: str, message_id: int, error: str) -> None:
    async with _connection(db_path) as db:
        await db.execute(
            "UPDATE scheduled_messages SET status = 'failed', error = ? WHERE id = ?",
            (error[:500], message_id),
        )
        await db.commit()
