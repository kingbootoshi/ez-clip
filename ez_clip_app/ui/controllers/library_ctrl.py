"""
Library controller for the EZ CLIP application.

This module manages operations related to the media library.
"""
import logging
from pathlib import Path

from ez_clip_app.data.database import DB
from ez_clip_app.core.models import TranscriptionResult
from ez_clip_app.ui.event_bus import BUS

logger = logging.getLogger(__name__)


class LibraryController:
    """Controller for library operations.
    
    Manages loading, deleting, and updating media entries in the library.
    """
    
    def __init__(self, db: DB):
        """Initialize the controller.
        
        Args:
            db: Database instance
        """
        self.db = db
        
        # Connect to event bus
        BUS.refreshLibrary.connect(self.refresh)
    
    def refresh(self) -> list:
        """Refresh the library.
        
        Returns:
            List of media metadata dictionaries
        """
        # Get all finished media files
        library_items = []
        for row in self.db.get_finished_media():
            path = Path(row["filepath"])
            library_items.append({
                "id": row["id"],
                "name": path.name,
                "path": path
            })
        
        logger.debug("Library refreshed, found %d items", len(library_items))
        return library_items
    
    def delete(self, media_id: int) -> None:
        """Delete a media file and its associated data.
        
        Args:
            media_id: Media ID to delete
        """
        # Get file path first for logging
        file_path = self.db.get_media_path(media_id)
        file_name = Path(file_path).name if file_path else f"ID:{media_id}"
        
        # Delete from database
        self.db.delete_media(media_id)
        
        logger.info("Deleted media %s (ID: %d)", file_name, media_id)
        
        # Signal library refresh
        BUS.refreshLibrary.emit()
    
    def get_transcript(self, media_id: int) -> TranscriptionResult:
        """Get the transcript for a media file.
        
        Args:
            media_id: Media ID
            
        Returns:
            TranscriptionResult object
        """
        return self.db.get_transcript(media_id)
        
    def rename_speaker(self, media_id: int, speaker_id: str, name: str) -> None:
        """Rename a speaker in the transcript.
        
        Args:
            media_id: Media ID
            speaker_id: Speaker ID
            name: New speaker name
        """
        self.db.set_speaker_name(media_id, speaker_id, name)
        logger.debug("Renamed speaker %s to %s for media ID %d", speaker_id, name, media_id)
        
    def update_word(self, segment_id: int, word_id: int, new_text: str) -> None:
        """Update a word in the transcript.
        
        Args:
            segment_id: Segment ID
            word_id: Word ID
            new_text: New word text
        """
        self.db.update_word(segment_id, word_id, new_text)
        logger.debug("Updated word ID %d in segment %d to '%s'", word_id, segment_id, new_text)