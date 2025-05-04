"""
SQLite database helpers for the WhisperX transcription app.
"""
import sqlite3
import pathlib
import contextlib
import typing as t
from pathlib import Path
import logging

from ez_clip_app.config import DB_PATH, Status
from ez_clip_app.core.models import Segment, Word, TranscriptionResult
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)

# TypeAdapters for efficient validation
_seg_adapter = TypeAdapter(Segment)
_word_adapter = TypeAdapter(Word)

class DB:
    """Database interface for the WhisperX app."""
    
    def __init__(self, db_path: t.Union[str, Path] = DB_PATH):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database. Can be ":memory:" for in-memory testing.
        """
        self.db_path = Path(db_path)
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _ensure_tables(self):
        """Ensure all required tables exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path) as f:
            schema_sql = f.read()
        
        # Modify the schema to use "IF NOT EXISTS" to handle existing tables
        # This ensures that the script won't fail if tables already exist
        with self._get_connection() as conn:
            # First check if we already have the required tables
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            if tables:
                # Tables exist, just make sure foreign keys are enabled
                conn.execute("PRAGMA foreign_keys = ON")
                logger.info("Database tables already exist, skipping schema creation")
            else:
                # No tables, execute the full schema
                logger.info("Creating new database schema")
                conn.executescript(schema_sql)
    
    def insert_media(self, path: t.Union[str, Path]) -> int:
        """Insert a new media file or get existing ID.
        
        Args:
            path: Path to the media file
            
        Returns:
            The media file ID
        """
        path_str = str(path)
        with self._get_connection() as conn:
            # Try to insert new record
            cur = conn.execute(
                "INSERT OR IGNORE INTO media_files(filepath) VALUES(?)",
                (path_str,)
            )
            # If inserted, return new ID, otherwise look up existing ID
            if cur.rowcount > 0:
                return cur.lastrowid
            else:
                row = conn.execute(
                    "SELECT id FROM media_files WHERE filepath=?",
                    (path_str,)
                ).fetchone()
                return row["id"]
    
    def set_status(self, media_id: int, status: str):
        """Update the status of a media file.
        
        Args:
            media_id: Media file ID
            status: New status (queued, running, done, error)
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE media_files SET status = ? WHERE id = ?",
                (status, media_id)
            )
    
    def update_progress(self, media_id: int, progress: float):
        """Update the progress of a media file.
        
        Args:
            media_id: Media file ID
            progress: Progress percentage (0-100)
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE media_files SET progress = ? WHERE id = ?",
                (progress, media_id)
            )
    
    def set_error(self, media_id: int, error_msg: str):
        """Set error message and update status.
        
        Args:
            media_id: Media file ID
            error_msg: Error message
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE media_files SET status = ?, error_msg = ? WHERE id = ?",
                (Status.ERROR, error_msg, media_id)
            )
    
    def save_transcript(self, media_id: int, full_text: str, duration: float, segments: t.List[dict]) -> int:
        """Save transcript and segments. Ensures only one transcript row exists per media_id.
        
        Args:
            media_id: Media file ID
            full_text: Complete transcript text (potentially Markdown formatted)
            duration: Audio duration in seconds
            segments: List of segment dictionaries with speaker, timestamps, text, etc.
            
        Returns:
            Transcript ID
        """
        # Establish a connection and transaction context
        with self._get_connection() as conn:
            # Delete existing segments and the main transcript row for this media_id
            # to prevent duplicates and ensure only the latest data is stored.
            conn.execute("DELETE FROM segments WHERE media_id = ?", (media_id,))
            conn.execute("DELETE FROM transcripts WHERE media_id = ?", (media_id,))
            
            # Insert the main transcript record
            cur = conn.execute(
                "INSERT INTO transcripts(media_id, full_text, duration) VALUES(?, ?, ?)",
                (media_id, full_text, duration)
            )
            # Retrieve the ID of the inserted transcript row
            transcript_id = cur.lastrowid
            
            # Iterate through the provided segments and insert each one
            for segment in segments:
                # Insert the segment and get its ID
                cur = conn.execute(
                    """
                    INSERT INTO segments(
                        media_id, speaker, start_sec, end_sec, text
                    ) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        media_id,
                        # Use provided speaker or default to 'SPEAKER_UNKNOWN'
                        segment.get("speaker", "SPEAKER_UNKNOWN"),
                        segment["start"], # Start time of the segment
                        segment["end"],   # End time of the segment
                        segment["text"],  # Text content of the segment
                    )
                )
                segment_id = cur.lastrowid
                
                # Insert words with segment_id FK
                for w in segment.get("words", []):
                    conn.execute(
                        """INSERT INTO words
                           (segment_id, text, start_sec, end_sec, score)
                           VALUES (?,?,?,?,?)""",
                        (
                            segment_id,                    # FK to segments table
                            w["word"],
                            float(w["start"]),
                            float(w["end"]),
                            float(w.get("score", 0)),
                        ),
                    )
            
            # Return the ID of the main transcript record
            return transcript_id
    
    def get_active_jobs(self) -> t.List[sqlite3.Row]:
        """Get all active jobs for progress tracking.
        
        Returns:
            List of row objects with id, filepath, status, progress
        """
        with self._get_connection() as conn:
            return conn.execute(
                """
                SELECT id, filepath, status, progress
                FROM media_files
                WHERE status IN (?, ?)
                """,
                (Status.QUEUED, Status.RUNNING)
            ).fetchall()
    
    def get_transcript(self, media_id: int) -> TranscriptionResult:
        """Get the most recent complete transcript with segments for a media file.
        
        Args:
            media_id: Media file ID
            
        Returns:
            TranscriptionResult object with transcript and segments, or None if not found.
        """
        with self._get_connection() as conn:
            # Get the most recent transcript row for the given media_id
            transcript = conn.execute(
                """
                SELECT * FROM transcripts
                WHERE media_id = ?
                ORDER BY id DESC  -- Fetch the latest entry
                LIMIT 1           -- Only fetch one
                """,
                (media_id,)
            ).fetchone()

            # If no transcript record found, return None
            if not transcript:
                logger.warning(f"No transcript found for media_id {media_id}")
                return None

            # Get associated segments (still ordered by start time)
            segments = conn.execute(
                """
                SELECT * FROM segments
                WHERE media_id = ?
                ORDER BY start_sec
                """,
                (media_id,)
            ).fetchall()
            
            # Convert rows to dictionaries and fetch associated words
            segments_list = []
            for seg in segments:
                seg_dict = dict(seg)  # sqlite Row → dict
                # fetch words for this segment_id
                seg_words = conn.execute(
                    "SELECT * FROM words WHERE segment_id=? ORDER BY start_sec",
                    (seg_dict["id"],)
                ).fetchall()
                
                # Convert words to Word model instances
                word_models = []
                for w in seg_words:
                    word_dict = dict(w)
                    word = _word_adapter.validate_python({
                        "w": word_dict["text"],
                        "s": word_dict["start_sec"],
                        "e": word_dict["end_sec"],
                        "score": word_dict["score"]
                    })
                    word_models.append(word)
                
                # Create a Segment model instance
                segment = _seg_adapter.validate_python({
                    "id": seg_dict["id"],
                    "speaker": seg_dict["speaker"],
                    "start_sec": seg_dict["start_sec"],
                    "end_sec": seg_dict["end_sec"],
                    "text": seg_dict["text"],
                    "words": word_models
                })
                segments_list.append(segment)
            
            # Create and return TranscriptionResult
            return TranscriptionResult(
                segments=segments_list,
                duration=transcript["duration"],
                full_text=transcript["full_text"]
            )
    
    def get_media_path(self, media_id: int) -> str:
        """Get the file path for a media ID.
        
        Args:
            media_id: Media file ID
            
        Returns:
            File path string
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT filepath FROM media_files WHERE id = ?",
                (media_id,)
            ).fetchone()
            return row["filepath"] if row else None
            
    def get_finished_media(self) -> t.List[sqlite3.Row]:
        """Get all completed media files.
        
        Returns:
            List of row objects with id, filepath
        """
        with self._get_connection() as conn:
            return conn.execute(
                """
                SELECT id, filepath 
                FROM media_files 
                WHERE status = ? 
                ORDER BY added_at DESC
                """,
                (Status.DONE,)
            ).fetchall()
            
    def get_speaker_map(self, media_id: int) -> t.Dict[str, str]:
        """Get speaker name mapping for a media file.
        
        Args:
            media_id: Media file ID
            
        Returns:
            Dictionary mapping speaker IDs to names
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT speaker, name 
                FROM speakers 
                WHERE media_id = ?
                """,
                (media_id,)
            ).fetchall()
        return {row["speaker"]: row["name"] for row in rows}
        
    def set_speaker_name(self, media_id: int, speaker_id: str, name: str):
        """Set a speaker name.
        
        Args:
            media_id: Media file ID
            speaker_id: Speaker ID
            name: Speaker name
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO speakers(media_id, speaker, name) 
                VALUES(?, ?, ?)
                """,
                (media_id, speaker_id, name)
            )
            
    def update_transcript_text(self, media_id: int, new_text: str):
        """Overwrite full_text for latest transcript of media_id.
        
        Args:
            media_id: Media file ID
            new_text: New transcript text
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE transcripts
                SET full_text = ?
                WHERE media_id = ?
                  AND id = (SELECT id FROM transcripts
                            WHERE media_id = ? ORDER BY id DESC LIMIT 1)
                """,
                (new_text, media_id, media_id)
            )
            
    def delete_media(self, media_id: int):
        """Completely remove a media file and all its associated data."""
        with self._get_connection() as conn:
            # Delete speakers explicitly (belt and suspenders, normally handled by cascade)
            conn.execute("DELETE FROM speakers WHERE media_id = ?", (media_id,))
            # This will cascade delete related transcripts, segments, and words
            conn.execute("DELETE FROM media_files WHERE id = ?", (media_id,))
            
    def get_segment(self, segment_id: int) -> Segment:
        """Get a specific segment with its words.
        
        Args:
            segment_id: Segment ID
            
        Returns:
            Segment object with words
        """
        with self._get_connection() as conn:
            # Get the segment
            row = conn.execute(
                "SELECT * FROM segments WHERE id=?", 
                (segment_id,)
            ).fetchone()
            
            if not row:
                raise ValueError(f"Segment with ID {segment_id} not found")
            
            # Get all words for this segment
            words = conn.execute(
                "SELECT * FROM words WHERE segment_id=? ORDER BY start_sec",
                (segment_id,)
            ).fetchall()
            
            # Convert words to Word model instances
            word_models = []
            for w in words:
                word_dict = dict(w)
                word = _word_adapter.validate_python({
                    "w": word_dict["text"],
                    "s": word_dict["start_sec"],
                    "e": word_dict["end_sec"],
                    "score": word_dict["score"]
                })
                word_models.append(word)
            
            # Create a Segment model instance
            seg_dict = dict(row)
            segment = _seg_adapter.validate_python({
                "id": seg_dict["id"],
                "speaker": seg_dict["speaker"],
                "start_sec": seg_dict["start_sec"],
                "end_sec": seg_dict["end_sec"],
                "text": seg_dict["text"],
                "words": word_models
            })
            
            return segment
            
    def get_words_by_segment(self, segment_id: int) -> t.List[sqlite3.Row]:
        """Get words for a specific segment.
        
        Args:
            segment_id: Segment ID
            
        Returns:
            List of word rows sorted by start time
        """
        with self._get_connection() as conn:
            return conn.execute(
                "SELECT * FROM words WHERE segment_id=? ORDER BY start_sec",
                (segment_id,)
            ).fetchall()

    def update_word(self, segment_id: int, word_id: int, new_text: str):
        """Patch a single word & cascade text updates.
        
        Args:
            segment_id: Segment ID
            word_id: Word ID
            new_text: New word text
        """
        with self._get_connection() as conn:
            # Update the word text
            conn.execute(
                "UPDATE words SET text=? WHERE id=? AND segment_id=?", 
                (new_text, word_id, segment_id)
            )
            
            # Get the media_id from the segment
            row = conn.execute(
                "SELECT media_id FROM segments WHERE id=?", 
                (segment_id,)
            ).fetchone()
            
            if not row:
                return  # Segment not found
                
            media_id = row["media_id"]
            
            # Rebuild segment.text from all its words
            words = conn.execute(
                "SELECT text FROM words WHERE segment_id=? ORDER BY start_sec", 
                (segment_id,)
            ).fetchall()
            
            sentence = " ".join(w["text"] for w in words)
            conn.execute(
                "UPDATE segments SET text=? WHERE id=?",
                (sentence, segment_id)
            )
            
        # Finally regenerate full transcript via formatting util
        self._regenerate_full_text(media_id)

    def _regenerate_full_text(self, media_id: int):
        """Regenerate full markdown transcript from segments.
        
        Args:
            media_id: Media file ID
        """
        result = self.get_transcript(media_id)  # TranscriptionResult
        if result is None:
            logger.warning(f"Cannot regenerate full text: no transcript for media_id {media_id}")
            return
            
        # Convert segment models to dicts for formatting
        seg_dicts = [s.model_dump() for s in result.segments]
        speaker_map = self.get_speaker_map(media_id)
        
        from ez_clip_app.core.formatting import segments_to_markdown
        new_md = segments_to_markdown(seg_dicts, speaker_map)
        
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE transcripts SET full_text=? WHERE media_id=?",
                (new_md, media_id)
            )