"""
Word editor panel for the EZ CLIP application.

This module provides a panel for toggling words in a transcript.
"""
import logging
from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from ez_clip_app.ui.word_toggle_view import WordToggleView
from ez_clip_app.core import EditMask
from ez_clip_app.core.models import Word

logger = logging.getLogger(__name__)


class WordEditorPanel(QWidget):
    """Panel for toggling words in a transcript.
    
    Wraps a WordToggleView to provide word-level editing functionality.
    
    Signals:
        wordToggled: Emitted when a word is toggled
    """
    wordToggled = Signal(int, int, bool)  # media_id, idx, keep
    
    def __init__(self, parent=None):
        """Initialize the word editor panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Current media ID
        self.media_id = None
        
        # Create word toggle view
        self.word_toggle = WordToggleView()
        self.word_toggle.wordToggled.connect(self._on_word_toggled)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.word_toggle)
    
    def _on_word_toggled(self, idx: int, keep: bool):
        """Handle word toggle event.
        
        Args:
            idx: Word index
            keep: Keep state
        """
        if self.media_id is not None:
            self.wordToggled.emit(self.media_id, idx, keep)
    
    def set_media(self, media_id: int, words: List[Word], mask: EditMask) -> None:
        """Set the media and words to display.
        
        Args:
            media_id: Media ID
            words: List of Word objects
            mask: Edit mask
        """
        self.media_id = media_id
        self.word_toggle.set_words(words)
        self.word_toggle.set_mask(mask)
    
    def clear(self) -> None:
        """Clear the panel."""
        self.media_id = None
        self.word_toggle.set_words([])
        self.word_toggle.document().clear()