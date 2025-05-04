"""
Pytest configuration file for the ez-clip test suite.
"""

import json
import os
import sys
from pathlib import Path
import pytest

from ez_clip_app.data.database import DB
from ez_clip_app.core.transcribe import TranscriptionResult

# Add the parent directory to sys.path to allow imports from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define path to fixture data
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "multi_speakers_fixture.json"

@pytest.fixture(scope="session")
def fixture_data():
    """Load JSON fixture into a python dict."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

@pytest.fixture(scope="function")
def tmp_db(tmp_path):
    """Return an *in-memory* DB that is isolated per test."""
    # Create a temporary file-based SQLite database for testing
    db_path = tmp_path / "test.db"
    
    # Monkey patch the _ensure_tables method to force schema creation
    original_ensure_tables = DB._ensure_tables
    
    def force_create_tables(self):
        """Force table creation by always running the schema SQL."""
        schema_path = Path(__file__).parent.parent / "ez_clip_app" / "data" / "schema.sql"
        with open(schema_path) as f:
            schema_sql = f.read()
        
        with self._get_connection() as conn:
            conn.executescript(schema_sql)
    
    # Replace the method temporarily
    DB._ensure_tables = force_create_tables
    
    # Create the DB
    db = DB(":memory:")
    
    # Restore the original method
    DB._ensure_tables = original_ensure_tables
    
    return db

@pytest.fixture(scope="session")
def fixture_transcription(fixture_data):
    """Return a TranscriptionResult recreated from JSON."""
    return TranscriptionResult(
        segments=fixture_data["segments"],
        full_text=fixture_data["markdown"],
        duration=fixture_data["duration"],
    )

@pytest.fixture(autouse=False)
def patch_heavy_functions(mocker, fixture_transcription, fixture_data, tmp_path):
    """Disable heavy ML calls for unit tests."""
    # Mock the transcribe function
    mocker.patch(
        "ez_clip_app.core.transcribe.transcribe",
        return_value=fixture_transcription,
    )
    
    # Mock the diarize function
    mocker.patch(
        "ez_clip_app.core.diarize.diarize",
        side_effect=lambda *args, **kw: fixture_data["segments"],
    )
    
    # Mock extract_audio to avoid ffmpeg dependencies
    dummy_audio = tmp_path / "dummy.wav"
    dummy_audio.write_bytes(b"0")  # exists but content ignored
    mocker.patch(
        "ez_clip_app.core.transcribe.extract_audio",
        return_value=dummy_audio
    )

# Define custom markers for categorizing tests
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "optional: mark test as optional (may be skipped)")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow (may take longer to run)")
    config.addinivalue_line("markers", "gui: mark test as requiring a GUI environment")

    # Skip GUI tests in CI environment to avoid Qt-related errors
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        # Register a mark for skipping GUI tests in CI
        config.addinivalue_line("markers", 
                               "skip_in_ci: skip test when running in CI environment")
        
        # Apply the skip_in_ci marker to all gui tests
        config.option.markexpr = 'not gui'

# Setup logging for tests
@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for tests."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    yield
    # Teardown (if needed)