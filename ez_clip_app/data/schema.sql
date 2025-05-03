-- Database schema for the WhisperX transcription app

-- files to be transcribed
CREATE TABLE IF NOT EXISTS media_files (
    id          INTEGER PRIMARY KEY,
    filepath    TEXT UNIQUE NOT NULL,
    added_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    status      TEXT DEFAULT 'queued',   -- queued | running | done | error
    progress    REAL DEFAULT 0.0,        -- 0-100
    error_msg   TEXT
);

-- whole-file transcript
CREATE TABLE IF NOT EXISTS transcripts (
    id          INTEGER PRIMARY KEY,
    media_id    INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    full_text   TEXT,
    duration    REAL
);

-- fine-grained segments (speaker + timestamps)
CREATE TABLE IF NOT EXISTS segments (
    id          INTEGER PRIMARY KEY,
    media_id    INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    speaker     TEXT,
    start_sec   REAL,
    end_sec     REAL,
    text        TEXT,
    words_json  TEXT               -- [{"w":"Hello","s":1.23,"e":1.50}, ...]
);

-- optional speaker name overrides
CREATE TABLE IF NOT EXISTS speakers (
    media_id    INTEGER,
    speaker     TEXT,
    name        TEXT,
    PRIMARY KEY(media_id, speaker)
);

-- Enable foreign keys
PRAGMA foreign_keys = ON;