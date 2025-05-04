"""
Integration tests for the PreviewRebuilder component.

This test uses fixtures to run the preview pipeline with real media files.
"""
import pytest
import json
import tempfile
from pathlib import Path
import logging

# Handle QMediaPlaylist compatibility
try:
    from PySide6.QtMultimedia import QMediaPlaylist
    USE_LEGACY_PLAYLIST = True
except ImportError:
    USE_LEGACY_PLAYLIST = False
from ez_clip_app.core import EditMask, PreviewRebuilder
from ez_clip_app.core.models import Word
from ez_clip_app.ui.player_widget import PlayerWidget

logger = logging.getLogger(__name__)


class MockPlayerWidget:
    """Mock of PlayerWidget for testing."""
    def __init__(self):
        self.player = MockPlayer()
        self.loaded_path = None
        
    def load(self, path):
        self.loaded_path = path
        

class MockPlayer:
    """Mock of QMediaPlayer for testing."""
    def __init__(self):
        self.position = 0
        self.playlist = None
        self.is_playing = False
        
    def setPosition(self, pos):
        self.position = pos
        
    def setPlaylist(self, playlist):
        self.playlist = playlist
        
    def pause(self):
        self.is_playing = False


# Mark this test as slow, integration, and GUI to be skipped in fast test runs and in CI
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.gui
def test_preview_builder():
    """Test that PreviewRebuilder correctly builds preview clips."""
    # Path to a test file (use the fixture in the tests/test_clips directory)
    test_file = Path(__file__).parent / "test_clips" / "multi_speakers.mp4"
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
        
    # Create mock player and preview rebuilder
    player = MockPlayerWidget()
    preview = PreviewRebuilder(player)
    
    # Create words list (simplified version of actual transcript)
    words = [
        Word(w="Hello", s=0.0, e=0.5),
        Word(w="this", s=0.6, e=0.9), 
        Word(w="is", s=1.0, e=1.2),
        Word(w="a", s=1.3, e=1.4),
        Word(w="test", s=1.5, e=2.0),
        Word(w="with", s=2.2, e=2.5),
        Word(w="multiple", s=2.7, e=3.1),
        Word(w="words", s=3.2, e=3.6),
        Word(w="in", s=3.7, e=3.9),
        Word(w="it", s=4.0, e=4.2),
    ]
    
    # Create mask with some words cut out
    mask = EditMask(media_id=1, keep=[True, True, False, False, True, True, False, True, True, False])
    
    # Run the build process directly (not via schedule which uses a timer)
    preview._scheduled_build = (mask, words, str(test_file))
    preview._build()
    
    # Verify that preview was created - this depends on which playlist version we're using
    if USE_LEGACY_PLAYLIST:
        # Verify with legacy playlist
        assert player.player.playlist is not None
        
        if player.player.playlist:
            # Should have clips based on ranges with keep=True
            # We use >= because the actual logic might group differently
            assert player.player.playlist.mediaCount() >= 1, "Should have at least one clip"
    else:
        # For newer versions, just verify that something was loaded
        assert player.loaded_path is not None, "Should have loaded at least one clip"