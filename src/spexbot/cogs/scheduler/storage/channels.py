import time

import aiosqlite


async def get_saved_destination_ids(db_path: str, limit: int = 25) -> list[int]:
    async with (
        aiosqlite.connect(db_path) as db,
        db.execute(
            "SELECT channel_id FROM saved_destinations ORDER BY last_used_at DESC LIMIT ?",
            (limit,),
        ) as cursor,
    ):
        rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def save_destination(
    db_path: str, channel_id: int, guild_id: int, user_id: int
) -> None:
    """Add a destination, or just bump its last used time if already present."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO saved_destinations (channel_id, guild_id, added_by, last_used_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET last_used_at = excluded.last_used_at
            """,
            (channel_id, guild_id, user_id, int(time.time())),
        )
        await db.commit()


async def remove_destination(db_path: str, channel_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "DELETE FROM saved_destinations WHERE channel_id = ?", (channel_id,)
        )
        await db.commit()
