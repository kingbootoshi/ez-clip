"""
Word table panel for the EZ CLIP application.

This module provides a panel for displaying and editing words within a segment.
"""
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
)

from ez_clip_app.core.models import Segment, Word

logger = logging.getLogger(__name__)


class WordTablePanel(QWidget):
    """Panel for displaying and editing words within a segment.
    
    Displays a table of words with start/end times and scores.
    
    Signals:
        wordClicked: Emitted when a word is clicked
        wordDoubleClicked: Emitted when a word is double-clicked
    """
    wordClicked = Signal(float)  # start_sec
    wordDoubleClicked = Signal(int, int, str)  # segment_id, word_id, word_text
    
    def __init__(self, parent=None):
        """Initialize the word table panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Current segment_id
        self.segment_id = None
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Word", "Start", "End", "Score"])
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Connect signals
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
    
    def _on_cell_clicked(self, row, col):
        """Handle cell click event.
        
        Args:
            row: Row index
            col: Column index
        """
        # Get start time directly from the table
        start_sec = float(self.table.item(row, 1).text())
        self.wordClicked.emit(start_sec)
    
    def _on_cell_double_clicked(self, row, col):
        """Handle cell double-click event.
        
        Args:
            row: Row index
            col: Column index
        """
        # Only handle double clicks on the word column
        if col != 0 or self.segment_id is None:
            return
        
        # Get word data
        word_item = self.table.item(row, 0)
        if word_item:
            word_id = word_item.data(Qt.UserRole)
            word_text = word_item.text()
            self.wordDoubleClicked.emit(self.segment_id, word_id, word_text)
    
    def set_words(self, segment_id: int, words: list) -> None:
        """Set the words to display.
        
        Args:
            segment_id: Segment ID
            words: List of Word objects
        """
        self.segment_id = segment_id
        
        # Set table rows
        self.table.setRowCount(len(words))
        
        for i, word in enumerate(words):
            # Word column
            word_item = QTableWidgetItem(word.w)
            word_item.setData(Qt.UserRole, i)  # Use index as word_id
            self.table.setItem(i, 0, word_item)
            
            # Start time column
            start_item = QTableWidgetItem(f"{word.s:.2f}")
            self.table.setItem(i, 1, start_item)
            
            # End time column
            end_item = QTableWidgetItem(f"{word.e:.2f}")
            self.table.setItem(i, 2, end_item)
            
            # Score column
            score_item = QTableWidgetItem(f"{word.score or 0:.2f}")
            self.table.setItem(i, 3, score_item)
        
        self.table.resizeColumnsToContents()
    
    def clear(self) -> None:
        """Clear the table."""
        self.table.setRowCount(0)
        self.segment_id = None