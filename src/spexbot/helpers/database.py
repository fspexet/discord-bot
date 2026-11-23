import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parents[4] / "schema.sql"

def setup(filename: str):
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(filename)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.executescript(schema)

    cursor.close()
    conn.commit()

    conn.close()
