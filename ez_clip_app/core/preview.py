"""
PreviewRebuilder for clip generation and preview.

This module handles creating clip segments and building a playlist for preview
based on the current edit mask.
"""
import weakref
import logging
from pathlib import Path
from typing import List, Tuple

import ffmpeg
from PySide6.QtCore import QUrl, QTimer
# In newer PySide6 versions, QMediaPlaylist was removed and playlists are handled differently
try:
    from PySide6.QtMultimedia import QMediaPlaylist
    USE_LEGACY_PLAYLIST = True
except ImportError:
    from PySide6.QtCore import QObject
    USE_LEGACY_PLAYLIST = False

from slugify import slugify

logger = logging.getLogger(__name__)


class PreviewRebuilder:
    """Manages preview clip generation and playback.
    
    Takes an EditMask and generates temporary clips for each kept segment,
    then builds a QMediaPlaylist for preview.
    """
    
    def __init__(self, player_widget):
        """Initialize the PreviewRebuilder.
        
        Args:
            player_widget: The PlayerWidget to update with previews
        """
        # Keep weak reference to avoid circular references
        self.player = weakref.ref(player_widget)
        self._timer = None
        self._scheduled_build = None
    
    def schedule(self, mask, words, media_path):
        """Schedule a preview rebuild after a short delay.
        
        This debounces rapid edits to avoid excessive rebuilding.
        
        Args:
            mask: The EditMask to use for building ranges
            words: List of Word objects to build ranges from
            media_path: Path to the source media file
        """
        # Cancel any existing timer
        if self._timer and self._timer.isActive():
            self._timer.stop()
        
        # Store parameters for later
        self._scheduled_build = (mask, words, media_path)
        
        # Create new timer
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._build)
        self._timer.start(300)  # 300ms debounce
    
    def _build(self):
        """Build preview clips and playlist.
        
        Uses the scheduled parameters to build ranges, extract clips,
        and create a playlist for preview.
        """
        if not self._scheduled_build:
            return
            
        mask, words, media_path = self._scheduled_build
        
        # Get player widget (might be gone if UI was closed)
        player = self.player()
        if not player:
            return
            
        # Build time ranges from mask
        ranges = mask.build_ranges(words)
        
        # If mask is trivial (all words kept), just load the original media
        if mask.is_trivial():
            player.load(Path(media_path))
            return
            
        # Create cache folder
        cache_dir = Path.home() / ".ez_clip_app" / "cache" / str(mask.media_id)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate clips for each range
        clips = []
        for idx, (start, end) in enumerate(ranges):
            out_file = cache_dir / f"{idx:03d}.mp4"
            clips.append(out_file)
            
            # Skip if clip already exists
            if out_file.exists():
                continue
                
            try:
                # Extract clip with copy codec (no re-encode)
                logger.info(f"Extracting clip {idx} [{start:.2f}-{end:.2f}]")
                (
                    ffmpeg
                    .input(str(media_path), ss=start, to=end)
                    .output(str(out_file), c="copy")
                    .overwrite_output()
                    .run(quiet=True)
                )
            except ffmpeg.Error as e:
                logger.error(f"FFmpeg error: {e}")
        
        player = self.player()
        if player is None:
            return
            
        if USE_LEGACY_PLAYLIST:
            # Use legacy QMediaPlaylist
            playlist = QMediaPlaylist()
            for clip in clips:
                playlist.addMedia(QUrl.fromLocalFile(str(clip)))
            
            # Set playlist to player and reset position
            player.player.setPlaylist(playlist)
        else:
            # In newer versions, we need to handle playlists differently
            if clips:
                # Just load the first clip for now
                # For a complete solution, we'd need to implement playlist management at the MainWindow level
                player.load(clips[0])
                logger.info(f"Loaded first clip: {clips[0]}")
        
        player.player.setPosition(0)
        player.player.pause()