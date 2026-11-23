-- ========================================================
--                      Forwarding
-- ========================================================

-- Create table to pair redirected message with its source
CREATE TABLE IF NOT EXISTS message_pairings (
    source_message_id   INTEGER,
    source_channel_id   INTEGER, 
    redirect_id         INTEGER PRIMARY KEY
);

-- Create table for custom nicknames
CREATE TABLE IF NOT EXISTS nicknames (
    user_id     INTEGER PRIMARY KEY,
    nickname    TEXT
);

-- ========================================================
--                      Scheduling
-- ========================================================

-- Create table for saving destination channels for scheduling
CREATE TABLE IF NOT EXISTS saved_destinations (
   channel_id      INTEGER PRIMARY KEY,
   guild_id        INTEGER NOT NULL,
   added_by        INTEGER NOT NULL,
   last_used_at    INTEGER NOT NULL     -- unix timestamp (UTC)
);

-- Create tables for scheduled messages
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id       INTEGER NOT NULL,
    content         TEXT    NOT NULL,
    dest_channel_id INTEGER NOT NULL,
    dest_guild_id   INTEGER NOT NULL,
    sent_at         INTEGER NOT NULL,   -- unix timestamp (UTC)
    status          TEXT    NOT NULL DEFAULT 'pending', -- pending / sending / sent / failed /cancelled
    created_at      INTEGER NOT NULL,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS idx_scheduled_due
    ON scheduled_messages (status, send_at);

CREATE TABLE IF NOT EXISTS scheduled_attatchments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id  INTEGER NOT NULL REFRERNCES scheduled_messages (id) ON DELETE CASCADE,
    filename    TEXT    NOT NULL,   -- name the file gets when posted
    local_path  TEXT    NOT NULL    -- where the file is stored on disk
);

CREATE INDEX IF NOT EXISTS idx_attatchments_message
    ON scheduled_attatchments (message_id);