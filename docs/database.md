# Database Schema

EasyVid uses SQLite for storing transcription data. This document provides detailed information about the database schema, including tables, fields, relationships, and typical usage patterns.

## Overview

The database is located at `~/.ez_clip_app/transcripts.db` by default, and consists of four main tables:

1. `media_files` - Tracks media files and their processing status
2. `transcripts` - Stores whole-file transcription text
3. `segments` - Stores fine-grained segments with speakers and timestamps
4. `speakers` - Allows for custom speaker name overrides

## Entity Relationship Diagram

```
┌───────────────┐       ┌───────────────┐
│  media_files  │       │  transcripts  │
├───────────────┤       ├───────────────┤
│ id*           │──1────┤ id*           │
│ filepath      │       │ media_id* (FK)│
│ added_at      │       │ full_text     │
│ status        │       │ duration      │
│ progress      │       └───────────────┘
│ error_msg     │                 
└───────────────┘                 
        │                         
        │                         
        │1                        
        │                         
        ┼                         
        │                         
┌───────────────┐       ┌───────────────┐
│   segments    │       │   speakers    │
├───────────────┤       ├───────────────┤
│ id*           │       │ media_id* (FK)│
│ media_id* (FK)│       │ speaker*      │
│ speaker       │       │ name          │
│ start_sec     │       └───────────────┘
│ end_sec       │                
│ text          │                
│ words_json    │                
└───────────────┘                
```

## Table Definitions

### `media_files`

Tracks media files to be transcribed and their processing status.

| Column     | Type    | Description                             | Constraints        |
|------------|---------|----------------------------------------|--------------------|
| id         | INTEGER | Unique identifier                       | PRIMARY KEY        |
| filepath   | TEXT    | Path to the original media file         | UNIQUE, NOT NULL   |
| added_at   | TEXT    | Timestamp when file was added           | DEFAULT CURRENT_TIMESTAMP |
| status     | TEXT    | Processing status                       | DEFAULT 'queued'   |
| progress   | REAL    | Processing progress (0-100)             | DEFAULT 0.0        |
| error_msg  | TEXT    | Error message if processing failed      |                    |

**Status Values:**
- `queued` - File is queued for processing
- `running` - File is currently being processed
- `done` - Processing completed successfully
- `error` - Processing failed with an error

**Sample Query:**
```sql
-- Get all files with their status
SELECT id, filepath, status, progress FROM media_files ORDER BY added_at DESC;

-- Get files that need processing
SELECT * FROM media_files WHERE status = 'queued';

-- Get failed files
SELECT id, filepath, error_msg FROM media_files WHERE status = 'error';
```

### `transcripts`

Stores whole-file transcript information.

| Column    | Type    | Description                    | Constraints         |
|-----------|---------|--------------------------------|---------------------|
| id        | INTEGER | Unique identifier              | PRIMARY KEY         |
| media_id  | INTEGER | Reference to media_files.id    | FOREIGN KEY, CASCADE|
| full_text | TEXT    | Complete transcript text       |                     |
| duration  | REAL    | Media duration in seconds      |                     |

**Sample Query:**
```sql
-- Get transcript with media info
SELECT m.filepath, t.full_text, t.duration 
FROM transcripts t
JOIN media_files m ON t.media_id = m.id
WHERE m.id = ?;
```

### `segments`

Stores fine-grained segments with speaker information and timestamps.

| Column     | Type    | Description                       | Constraints         |
|------------|---------|-----------------------------------|---------------------|
| id         | INTEGER | Unique identifier                 | PRIMARY KEY         |
| media_id   | INTEGER | Reference to media_files.id       | FOREIGN KEY, CASCADE|
| speaker    | TEXT    | Speaker identifier (e.g., SPEAKER_1) |                  |
| start_sec  | REAL    | Start time in seconds             |                     |
| end_sec    | REAL    | End time in seconds               |                     |
| text       | TEXT    | Segment transcript text           |                     |
| words_json | TEXT    | JSON array of word-level timestamps |                   |

The `words_json` column stores word-level timing information in JSON format:
```json
[
  {"w": "Hello", "s": 1.23, "e": 1.50},
  {"w": "world", "s": 1.52, "e": 1.85}
]
```
Where:
- `w`: The word
- `s`: Start time in seconds
- `e`: End time in seconds

**Sample Query:**
```sql
-- Get all segments for a specific media file, ordered by start time
SELECT speaker, start_sec, end_sec, text 
FROM segments
WHERE media_id = ?
ORDER BY start_sec;

-- Get segments for a specific speaker
SELECT start_sec, end_sec, text 
FROM segments
WHERE media_id = ? AND speaker = ?
ORDER BY start_sec;
```

### `speakers`

Allows for custom speaker name overrides.

| Column   | Type    | Description                    | Constraints               |
|----------|---------|--------------------------------|---------------------------|
| media_id | INTEGER | Reference to media_files.id    | PRIMARY KEY (composite)   |
| speaker  | TEXT    | Speaker identifier (e.g., SPEAKER_1) | PRIMARY KEY (composite) |
| name     | TEXT    | Custom speaker name            |                           |

**Sample Query:**
```sql
-- Get all speaker mappings for a media file
SELECT speaker, name 
FROM speakers
WHERE media_id = ?;

-- Set a custom name for a speaker
INSERT OR REPLACE INTO speakers(media_id, speaker, name) 
VALUES(?, ?, ?);
```

## Foreign Key Relationships

The schema uses foreign keys with cascading deletes:

1. `transcripts.media_id` → `media_files.id`
   - If a media file is deleted, its transcript is also deleted.

2. `segments.media_id` → `media_files.id`
   - If a media file is deleted, all its segments are also deleted.

3. `speakers.media_id` → `media_files.id` (implicit)
   - This is an implicit relationship through the composite primary key.
   - If a media file is deleted, its speaker mappings should be manually removed.

## Usage Patterns

### Typical Workflow

1. Insert a new media file:
   ```sql
   INSERT INTO media_files(filepath) VALUES(?);
   ```

2. Update status to "running" and track progress:
   ```sql
   UPDATE media_files SET status = 'running' WHERE id = ?;
   UPDATE media_files SET progress = ? WHERE id = ?;
   ```

3. On success, store the transcript:
   ```sql
   INSERT INTO transcripts(media_id, full_text, duration) VALUES(?, ?, ?);
   ```

4. Store each segment:
   ```sql
   INSERT INTO segments(media_id, speaker, start_sec, end_sec, text, words_json) 
   VALUES(?, ?, ?, ?, ?, ?);
   ```

5. Update status to "done":
   ```sql
   UPDATE media_files SET status = 'done', progress = 100 WHERE id = ?;
   ```

### Error Handling

On error, update the status and store the error message:
```sql
UPDATE media_files SET status = 'error', error_msg = ? WHERE id = ?;
```

### Querying Results

Get a complete transcript with all segments:
```sql
-- Get the transcript
SELECT * FROM transcripts WHERE media_id = ?;

-- Get all segments
SELECT * FROM segments WHERE media_id = ? ORDER BY start_sec;

-- Get speaker name mappings
SELECT s.speaker, COALESCE(sp.name, s.speaker) AS display_name
FROM segments s
LEFT JOIN speakers sp ON s.media_id = sp.media_id AND s.speaker = sp.speaker
WHERE s.media_id = ?
GROUP BY s.speaker;
```

## Schema Migrations

The schema is initialized in the `data/schema.sql` file. For future schema migrations, consider using versioned SQL scripts and a migration function in the `DB` class.

Example migration approach:
```python
def _migrate_schema(self, current_version, target_version):
    """Apply schema migrations."""
    with self._get_connection() as conn:
        version = current_version
        while version < target_version:
            next_version = version + 1
            migration_path = Path(__file__).parent / f"migrations/v{version}_to_v{next_version}.sql"
            
            if not migration_path.exists():
                raise RuntimeError(f"Missing migration script: {migration_path}")
                
            with open(migration_path) as f:
                migration_sql = f.read()
                conn.executescript(migration_sql)
                
            version = next_version
        
        # Update schema version
        conn.execute("PRAGMA user_version = ?", (target_version,))
```

## Performance Considerations

For optimal performance:

1. Use indices for common query patterns:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_segments_media_start ON segments(media_id, start_sec);
   CREATE INDEX IF NOT EXISTS idx_media_status ON media_files(status);
   ```

2. Use transactions for batch inserts:
   ```python
   with self._get_connection() as conn:
       conn.execute("BEGIN TRANSACTION")
       try:
           for segment in segments:
               conn.execute("INSERT INTO segments(...) VALUES(...)", ...)
           conn.execute("COMMIT")
       except Exception:
           conn.execute("ROLLBACK")
           raise
   ```

3. Consider page size for large databases:
   ```sql
   PRAGMA page_size = 4096;
   VACUUM;
   ```

## Database Maintenance

Recommended maintenance tasks:

1. Regular vacuum:
   ```sql
   VACUUM;
   ```

2. Analyze for query optimization:
   ```sql
   ANALYZE;
   ```

3. Database integrity check:
   ```sql
   PRAGMA integrity_check;
   ```

4. Consider periodic cleanup of old records:
   ```sql
   DELETE FROM media_files 
   WHERE status = 'done' 
   AND added_at < datetime('now', '-90 days');
   ```