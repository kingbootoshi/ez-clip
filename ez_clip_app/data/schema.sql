-- ---------- MEDIA FILES ----------
CREATE TABLE media_files (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath  TEXT UNIQUE NOT NULL,
    added_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    status    TEXT DEFAULT 'queued',
    progress  REAL DEFAULT 0,
    error_msg TEXT,
    last_pos  REAL DEFAULT 0
);

-- ---------- TRANSCRIPTS ----------
CREATE TABLE transcripts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id  INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    full_text TEXT,
    duration  REAL
);

-- ---------- SEGMENTS ----------
CREATE TABLE segments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id   INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    speaker    TEXT,
    start_sec  REAL,
    end_sec    REAL,
    text       TEXT
);

-- ---------- WORDS ----------
CREATE TABLE words (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    segment_id INTEGER REFERENCES segments(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    start_sec  REAL NOT NULL,
    end_sec    REAL NOT NULL,
    score      REAL DEFAULT 0
);
CREATE INDEX words_seg_idx ON words(segment_id);

-- ---------- SPEAKERS ----------
CREATE TABLE speakers (
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    speaker  TEXT,
    name     TEXT,
    PRIMARY KEY(media_id, speaker)
);

-- ---------- EDIT MASKS ----------
CREATE TABLE IF NOT EXISTS edit_masks (
    media_id INTEGER PRIMARY KEY REFERENCES media_files(id) ON DELETE CASCADE,
    mask_json TEXT NOT NULL              -- {"kind":"mask-v1","remove":[[s,e],...]}
);

PRAGMA foreign_keys = ON;