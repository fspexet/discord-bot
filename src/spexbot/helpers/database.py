import sqlite3


def setup(filename: str):
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()

    # Skapa tabell för att kunna svara på meddelanden
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS message_pairings" \
        "(source_message_id INTEGER, source_channel_id INTEGER, redirect_id INTEGER PRIMARY KEY)"               
    )

    # Skapa tabell för anpassningsbara smeknamn
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS nicknames" \
        "(user_id INTEGER PRIMARY KEY, nickname TEXT)"
    )

    # Skapa tabell för sparade kanaler
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS saved_destinations (" \
        "   channel_id      INTEGER PRIMARY KEY," \
        "   guild_id        INTEGER NOT NULL," \
        "   added_by        INTEGER NOT NULL," \
        "   last_used_at    INTEGER NOT NULL" \
        ")"
    )

    cursor.close()
    conn.commit()

    conn.close()
