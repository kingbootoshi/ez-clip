"""
Drive process_file() with heavy functions patched → should finish instantly.
"""
import sqlite3
from pathlib import Path
import pytest
from ez_clip_app.core.pipeline import process_file, JobSettings
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

@pytest.mark.usefixtures("patch_heavy_functions")
def test_process_file_fast(test_db, fixture_data, tmp_path):
    dummy_video = tmp_path / "dummy.mp4"
    dummy_video.write_bytes(b"0")  # exists but content ignored

    settings = JobSettings(model_size="medium", language="en", diarize=True)

    transcript_id = process_file(
        media_path=dummy_video,
        settings=settings,
        db=test_db,
        progress_cb=lambda p: None,
    )

    # Verify that the status has been set correctly
    # For direct verification, let's query the status directly
    with test_db._get_connection() as conn:
        status = conn.execute(
            "SELECT status FROM media_files WHERE id=?", (1,)
        ).fetchone()["status"]
        assert status == Status.DONE
    
    # Verify transcript identical to fixture
    transcript_data = test_db.get_transcript(1)
    assert transcript_data is not None
    md = transcript_data["transcript"]["full_text"]
    assert md == fixture_data["markdown"]