#!/usr/bin/env python3
"""
tools/ezclip_migrate.py  –  Upgrade pre-0.2 SQLite DB to new schema.
"""
import sqlite3, pathlib, argparse, textwrap, sys

DEFAULT_DB = pathlib.Path.home() / ".ez_clip_app" / "transcripts.db"

SQL = textwrap.dedent("""
PRAGMA foreign_keys = OFF;
/* --- media_files --- */
ALTER TABLE media_files RENAME TO _tmp_media;
CREATE TABLE media_files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT UNIQUE NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'queued',
    progress REAL DEFAULT 0,
    error_msg TEXT
);
INSERT INTO media_files SELECT * FROM _tmp_media;
DROP TABLE _tmp_media;
/* Repeat the pattern for transcripts, segments, words … */
-- transcripts
ALTER TABLE transcripts RENAME TO _tmp_transcripts;
CREATE TABLE transcripts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    full_text TEXT,
    duration REAL
);
INSERT INTO transcripts SELECT * FROM _tmp_transcripts;
DROP TABLE _tmp_transcripts;
-- segments
ALTER TABLE segments RENAME TO _tmp_segments;
CREATE TABLE segments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    speaker TEXT,
    start_sec REAL,
    end_sec REAL,
    text TEXT
);
INSERT INTO segments SELECT * FROM _tmp_segments;
DROP TABLE _tmp_segments;
-- words
ALTER TABLE words RENAME TO _tmp_words;
CREATE TABLE words(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    segment_id INTEGER REFERENCES segments(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    score REAL DEFAULT 0
);
INSERT INTO words SELECT * FROM _tmp_words;
DROP TABLE _tmp_words;
/* speakers */
CREATE TABLE IF NOT EXISTS speakers_new(
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    speaker  TEXT,
    name     TEXT,
    PRIMARY KEY(media_id, speaker)
);
INSERT OR IGNORE INTO speakers_new SELECT * FROM speakers;
DROP TABLE speakers;
ALTER TABLE speakers_new RENAME TO speakers;
PRAGMA foreign_keys = ON;
VACUUM;
""")

def migrate(db_path: pathlib.Path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SQL)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to transcripts.db")
    args = parser.parse_args()
    migrate(pathlib.Path(args.db).expanduser())
    print("Migration complete.")
    sys.exit(0)