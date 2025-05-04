"""
CRUD tests on the SQLite layer using an in-memory DB.
"""
import sqlite3
import pytest
from pathlib import Path
from ez_clip_app.config import Status
from ez_clip_app.data.database import DB

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

def test_insert_and_cascade(test_db, fixture_data):
    media_id = test_db.insert_media("dummy.mp4")
    test_db.set_status(media_id, Status.RUNNING)

    # save transcript (segments only)
    test_db.save_transcript(
        media_id,
        fixture_data["markdown"],
        fixture_data["duration"],
        fixture_data["segments"],
    )

    # assert segments persisted
    segs = test_db.get_transcript(media_id)["segments"]
    assert len(segs) == len(fixture_data["segments"])

    # delete media and ensure cascades
    test_db.delete_media(media_id)
    assert test_db.get_transcript(media_id) is None