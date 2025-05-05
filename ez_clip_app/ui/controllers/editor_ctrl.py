"""
Editor controller for the EZ CLIP application.

This module handles operations related to the word-level editing functionality.
"""
import logging
import time
import tempfile
from pathlib import Path

from ez_clip_app.data.database import DB
from ez_clip_app.core import EditMask, PreviewRebuilder
from ez_clip_app.ui.event_bus import BUS

logger = logging.getLogger(__name__)


class EditorController:
    """Controller for word-level editing operations.
    
    Manages edit mask updates, preview generation, and clip export.
    """
    
    def __init__(self, db: DB, preview_rebuilder: PreviewRebuilder):
        """Initialize the controller.
        
        Args:
            db: Database instance
            preview_rebuilder: Preview rebuilder for clip generation
        """
        self.db = db
        self.preview_rebuilder = preview_rebuilder
        
        # Current media being edited
        self.current_media_id = None
        
        # Connect to event bus
        BUS.wordToggled.connect(self.toggle_word)
        BUS.requestPreviewBuild.connect(self.build_preview)
    
    def toggle_word(self, media_id: int, idx: int, keep: bool) -> None:
        """Toggle a word's keep/cut state in the edit mask.
        
        Args:
            media_id: Media ID
            idx: Word index
            keep: Whether to keep (True) or cut (False) the word
        """
        logger.debug("toggle_word: media=%d idx=%d keep=%s", media_id, idx, keep)
        
        # Update current media ID
        self.current_media_id = media_id
        
        # Get or create the edit mask
        edit_mask = self.db.get_edit_mask(media_id)
        if not edit_mask:
            # Get total words to create mask
            result = self.db.get_transcript(media_id)
            if not result:
                logger.error("No transcript found for media_id %d", media_id)
                return
                
            total_words = sum(len(seg.words) for seg in result.segments)
            edit_mask = EditMask(media_id, [True] * total_words)
        
        # Update the mask
        edit_mask.keep[idx] = keep
        
        # Save to database
        self.db.save_edit_mask(edit_mask)
        
        # Request preview rebuild
        BUS.requestPreviewBuild.emit(media_id)
    
    def build_preview(self, media_id: int) -> None:
        """Build a preview for the current edit mask.
        
        Args:
            media_id: Media ID
        """
        start_time = time.time()
        
        # Get the edit mask
        edit_mask = self.db.get_edit_mask(media_id)
        if not edit_mask:
            logger.warning("No edit mask found for media_id %d", media_id)
            return
            
        # Get all words
        all_words = []
        result = self.db.get_transcript(media_id)
        if not result:
            logger.error("No transcript found for media_id %d", media_id)
            return
            
        for segment in result.segments:
            for word in segment.words:
                all_words.append(word)
                
        # Get media path
        media_path = self.db.get_media_path(media_id)
        if not media_path or not Path(media_path).exists():
            logger.error("Media file not found: %s", media_path)
            return
            
        # Schedule the rebuild
        self.preview_rebuilder.schedule(edit_mask, all_words, media_path)
        
        elapsed = time.time() - start_time
        logger.info("Preview rebuilt in %.2fs", elapsed)
    
    def export_clip(self, media_id: int, dest_path: Path) -> None:
        """Export the current edit to a file.
        
        Args:
            media_id: Media ID
            dest_path: Destination path
        """
        from ez_clip_app.core.video_edit import extract_clip, concat_clips
        
        # Get the edit mask
        edit_mask = self.db.get_edit_mask(media_id)
        if not edit_mask:
            raise ValueError("No edit mask found")
            
        # Get all words
        all_words = []
        result = self.db.get_transcript(media_id)
        if not result:
            raise ValueError("No transcript found")
            
        for segment in result.segments:
            for word in segment.words:
                all_words.append(word)
                
        # Get media path
        media_path = self.db.get_media_path(media_id)
        if not media_path or not Path(media_path).exists():
            raise ValueError(f"Media file not found: {media_path}")
            
        # Calculate time ranges
        ranges = edit_mask.build_ranges(all_words)
        
        # Use temporary directory for intermediate clips
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            clips = []
            
            # Extract each clip
            for i, (start, end) in enumerate(ranges):
                clip_path = tmp_path / f"{i:03d}.mp4"
                clips.append(clip_path)
                extract_clip(Path(media_path), clip_path, start, end)
                
            # Concatenate all clips
            if clips:
                concat_clips(clips, dest_path)
            else:
                raise ValueError("No clip ranges to export")
                
        # Write SRT file
        self._write_srt(all_words, edit_mask, dest_path.with_suffix('.srt'))
        
        logger.info("Exported clip to %s", dest_path)
    
    def _write_srt(self, words, edit_mask, srt_path):
        """Write an SRT file with the kept words.
        
        Args:
            words: List of Word objects
            edit_mask: Edit mask
            srt_path: Path where to save the SRT file
        """
        if not words or not edit_mask:
            return
            
        # Filter kept words
        kept_words = [w for w, k in zip(words, edit_mask.keep) if k]
        if not kept_words:
            return
            
        with open(srt_path, 'w') as f:
            # Group words into sentences
            groups = []
            current_group = []
            last_end = 0
            
            for word in kept_words:
                # If there's a gap of more than 1 second, start new group
                if current_group and (word.s - last_end) > 1.0:
                    groups.append(current_group)
                    current_group = []
                
                current_group.append(word)
                last_end = word.e
                
            # Add the last group
            if current_group:
                groups.append(current_group)
                
            # Write SRT entries
            for i, group in enumerate(groups):
                # Calculate start/end times
                start = group[0].s
                end = group[-1].e
                
                # Format timestamps for SRT (HH:MM:SS,mmm)
                start_h = int(start // 3600)
                start_m = int((start % 3600) // 60)
                start_s = int(start % 60)
                start_ms = int((start % 1) * 1000)
                
                end_h = int(end // 3600)
                end_m = int((end % 3600) // 60)
                end_s = int(end % 60)
                end_ms = int((end % 1) * 1000)
                
                # Write entry
                f.write(f"{i+1}\n")
                f.write(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> ")
                f.write(f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n")
                f.write(" ".join(w.w for w in group))
                f.write("\n\n")