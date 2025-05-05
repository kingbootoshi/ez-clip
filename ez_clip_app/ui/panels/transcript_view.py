"""
Transcript view panel for the EZ CLIP application.

This module provides a panel for displaying the full transcript.
"""
import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit

logger = logging.getLogger(__name__)


class TranscriptViewPanel(QWidget):
    """Panel for displaying the full transcript.
    
    Displays the markdown-formatted transcript text.
    """
    
    def __init__(self, parent=None):
        """Initialize the transcript view panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create text widget
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)
    
    def set_text(self, markdown: str) -> None:
        """Set the transcript text.
        
        Args:
            markdown: Markdown-formatted transcript text
        """
        self.text.setMarkdown(markdown)
    
    def clear(self) -> None:
        """Clear the text."""
        self.text.clear()