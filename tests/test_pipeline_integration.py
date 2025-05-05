"""
Heavy end-to-end run – disabled by default, mark as slow+integration.
Requires HF_TOKEN and enough GPU/CPU RAM.
"""
import pytest
import sqlite3
from pathlib import Path
from deepdiff import DeepDiff
from ez_clip_app.core.pipeline import process_file, JobSettings
from ez_clip_app.data.database import DB

CLIP = Path(__file__).parent / "test_clips" / "multi_speakers.mp4"

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

@pytest.mark.integration
@pytest.mark.slow
def test_real_pipeline_matches_fixture(test_db, tmp_path, fixture_data):
    transcript_id = process_file(
        CLIP,
        JobSettings(model_size="medium", language="en", diarize=True),
        db=test_db,
        progress_cb=lambda p: None,
    )
    
    # Get the processed transcript
    transcript_data = test_db.get_transcript(transcript_id)
    assert transcript_data is not None
    
    # Compare key metrics instead of exact data which can vary between runs
    real_segments = transcript_data.segments
    fixture_segments = fixture_data["segments"]
    
    # Check we have same number of segments (approximately)
    assert abs(len(real_segments) - len(fixture_segments)) <= 1, \
        f"Segment count mismatch: got {len(real_segments)}, expected {len(fixture_segments)}"
    
    # Check we have the same speakers
    real_speakers = {seg.speaker for seg in real_segments}
    fixture_speakers = {seg["speaker"] for seg in fixture_segments}
    assert len(real_speakers) >= len(fixture_speakers) - 1, \
        f"Speaker count mismatch: got {len(real_speakers)}, expected {len(fixture_speakers)}"
    
    # Check that the total text length is similar
    real_text_len = sum(len(seg.text) for seg in real_segments)
    fixture_text_len = sum(len(seg["text"]) for seg in fixture_segments)
    text_ratio = real_text_len / fixture_text_len if fixture_text_len > 0 else 0
    assert 0.8 <= text_ratio <= 1.2, \
        f"Text length ratio out of bounds: {text_ratio:.2f}"
    
    # Check that the total duration is similar
    real_duration = transcript_data.duration
    fixture_duration = fixture_data["duration"]
    if fixture_duration > 0:  # Only check if fixture has a duration
        duration_ratio = real_duration / fixture_duration
        assert 0.8 <= duration_ratio <= 1.2, \
            f"Duration ratio out of bounds: {duration_ratio:.2f}"
    
    # Success if we get here - output is close enough to fixture
    print(f"Integration test passed with {len(real_segments)} segments, {len(real_speakers)} speakers")
    print(f"Text ratio: {text_ratio:.2f}, Duration: {real_duration:.2f}s")