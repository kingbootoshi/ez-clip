-- media_files: unchanged
CREATE TABLE media_files (
    id INTEGER PRIMARY KEY,
    filepath TEXT UNIQUE NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'queued',
    progress REAL DEFAULT 0,
    error_msg TEXT
);

-- transcripts: unchanged
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    full_text TEXT,
    duration REAL
);

-- segments: one row per speaker turn
CREATE TABLE segments (
    id INTEGER PRIMARY KEY,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    speaker TEXT,
    start_sec REAL,
    end_sec REAL,
    text TEXT
);

-- words: one row per word **linked by segment_id**
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    segment_id INTEGER REFERENCES segments(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    score REAL DEFAULT 0
);
CREATE INDEX words_seg_idx ON words(segment_id);

-- optional speaker name overrides
CREATE TABLE speakers (
    media_id INTEGER,
    speaker  TEXT,
    name     TEXT,
    PRIMARY KEY(media_id, speaker)
);

PRAGMA foreign_keys = ON;