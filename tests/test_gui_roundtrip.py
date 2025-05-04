"""
Regression tests for GUI-related functionality without requiring actual GUI widgets.
"""
import pytest
import sqlite3
from pathlib import Path

from ez_clip_app.data.database import DB
from ez_clip_app.core.models import Segment, Word, TranscriptionResult

@pytest.fixture
def test_db():
    """Create an in-memory database and initialize it with schema."""
    conn = sqlite3.connect(":memory:")
    
    # Set row factory
    conn.row_factory = sqlite3.Row
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Load schema
    schema_path = Path(__file__).parent.parent / "ez_clip_app" / "data" / "schema.sql"
    with open(schema_path) as f:
        schema_sql = f.read()
    
    # Create tables
    conn.executescript(schema_sql)
    
    # Create DB object
    db = DB(":memory:")
    
    # Monkey patch the connection method to return our pre-initialized connection
    original_get_connection = db._get_connection
    db._get_connection = lambda: conn
    
    yield db
    
    # Close connection
    conn.close()


def test_markdown_regen(test_db, fixture_data):
    """Test markdown regeneration after word edits with Pydantic models.
    
    Tests the flow:
    1. Insert a media entry with transcript
    2. Edit a word
    3. Verify the regenerated markdown contains the edited word
    
    This tests the functionality without requiring an actual GUI.
    """
    # Set up the test database with a media file and transcript
    media_id = test_db.insert_media("dummy.mp4")
    test_db.save_transcript(
        media_id=media_id,
        full_text=fixture_data["markdown"],
        duration=fixture_data["duration"],
        segments=fixture_data["segments"]
    )
    
    # Get a segment and word to edit
    result = test_db.get_transcript(media_id)
    assert isinstance(result, TranscriptionResult)
    assert len(result.segments) > 0
    
    # Get the segment ID and first word
    segment_id = result.segments[0].id
    word_rows = test_db.get_words_by_segment(segment_id)
    assert len(word_rows) > 0
    
    # Edit the first word
    word_id = word_rows[0]["id"]
    test_db.update_word(segment_id, word_id, "patched")
    
    # Get the updated transcript
    updated_result = test_db.get_transcript(media_id)
    assert isinstance(updated_result, TranscriptionResult)
    
    # Verify the edit is reflected in the markdown
    assert "patched" in updated_result.full_text
    
    # Verify the model has the updated word
    first_segment = updated_result.segments[0]
    assert isinstance(first_segment, Segment)
    
    # Check if any word in the segment has the "patched" text
    # It may not be the first word since the words might be re-ordered
    found_patched = False
    for word in first_segment.words:
        if word.w == "patched":
            found_patched = True
            break
    
    assert found_patched, "Edited word 'patched' not found in the segment words"