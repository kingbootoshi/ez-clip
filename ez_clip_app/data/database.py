"""
SQLite database helpers for the WhisperX transcription app.
"""
import sqlite3
import json
import pathlib
import contextlib
import typing as t
from pathlib import Path
import logging

from ez_clip_app.config import DB_PATH, Status

logger = logging.getLogger(__name__)

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
        
        with self._get_connection() as conn:
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
                # Serialize the 'words' list (if present) into JSON for storage
                words_json = json.dumps(segment.get("words", []))
                # Execute the INSERT statement for the segment
                conn.execute(
                    """
                    INSERT INTO segments(
                        media_id, speaker, start_sec, end_sec, text, words_json
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        media_id,
                        # Use provided speaker or default to 'SPEAKER_UNKNOWN'
                        segment.get("speaker", "SPEAKER_UNKNOWN"),
                        segment["start"], # Start time of the segment
                        segment["end"],   # End time of the segment
                        segment["text"],  # Text content of the segment
                        words_json        # JSON string of word timings
                    )
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
    
    def get_transcript(self, media_id: int) -> t.Dict:
        """Get the most recent complete transcript with segments for a media file.
        
        Args:
            media_id: Media file ID
            
        Returns:
            Dictionary with transcript and segments, or None if not found.
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
            
            # Convert rows to dictionaries and parse words_json
            segments_list = []
            for seg in segments:
                segment_dict = dict(seg)
                if segment_dict["words_json"]:
                    segment_dict["words"] = json.loads(segment_dict["words_json"])
                segments_list.append(segment_dict)
            
            return {
                "transcript": dict(transcript),
                "segments": segments_list
            }
    
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