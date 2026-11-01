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

    cursor.close()
    conn.commit()

    conn.close()
