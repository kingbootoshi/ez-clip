"""
Segment table panel for the EZ CLIP application.

This module provides a panel for displaying and interacting with transcript segments.
"""
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
)

from ez_clip_app.core.models import Segment

logger = logging.getLogger(__name__)


class SegmentTablePanel(QWidget):
    """Panel for displaying and interacting with transcript segments.
    
    Displays a table of segments with speaker, start/end times, and text.
    
    Signals:
        segmentClicked: Emitted when a segment is clicked
        segmentDoubleClicked: Emitted when a segment is double-clicked
    """
    segmentClicked = Signal(int)  # segment_id
    segmentDoubleClicked = Signal(int, str)  # segment_id, speaker_id
    
    def __init__(self, parent=None):
        """Initialize the segment table panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Speaker", "Start", "End", "Text"])
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
        # Get segment_id from the first column's UserRole data
        seg_item = self.table.item(row, 0)
        if seg_item:
            segment_id = seg_item.data(Qt.UserRole)
            self.segmentClicked.emit(segment_id)
    
    def _on_cell_double_clicked(self, row, col):
        """Handle cell double-click event.
        
        Args:
            row: Row index
            col: Column index
        """
        # Only emit for clicks on the speaker column
        if col != 0:
            return
            
        seg_item = self.table.item(row, 0)
        if seg_item:
            segment_id = seg_item.data(Qt.UserRole)
            speaker_id = seg_item.data(Qt.UserRole + 1)  # Store speaker_id in UserRole+1
            self.segmentDoubleClicked.emit(segment_id, speaker_id)
    
    def set_segments(self, segments: list, speaker_map: dict = None) -> None:
        """Set the segments to display.
        
        Args:
            segments: List of Segment objects
            speaker_map: Dictionary mapping speaker IDs to names
        """
        speaker_map = speaker_map or {}
        
        # Set table rows
        self.table.setRowCount(len(segments))
        
        for i, segment in enumerate(segments):
            # Speaker column
            speaker_id = segment.speaker
            display_name = speaker_map.get(speaker_id, speaker_id)
            speaker_item = QTableWidgetItem(display_name)
            speaker_item.setData(Qt.UserRole, segment.id)
            speaker_item.setData(Qt.UserRole + 1, speaker_id)
            self.table.setItem(i, 0, speaker_item)
            
            # Start time column (format as MM:SS.ms)
            start_secs = segment.start_sec
            start_formatted = f"{int(start_secs // 60):02d}:{start_secs % 60:05.2f}"
            start_item = QTableWidgetItem(start_formatted)
            self.table.setItem(i, 1, start_item)
            
            # End time column (format as MM:SS.ms)
            end_secs = segment.end_sec
            end_formatted = f"{int(end_secs // 60):02d}:{end_secs % 60:05.2f}"
            end_item = QTableWidgetItem(end_formatted)
            self.table.setItem(i, 2, end_item)
            
            # Text column
            text_item = QTableWidgetItem(segment.text)
            self.table.setItem(i, 3, text_item)
        
        self.table.resizeColumnsToContents()
        
        # Auto-select first row if any rows exist
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self._on_cell_clicked(0, 0)
    
    def clear(self) -> None:
        """Clear the table."""
        self.table.setRowCount(0)