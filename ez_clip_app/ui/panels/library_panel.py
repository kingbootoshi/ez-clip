"""
Library panel for the EZ CLIP application.

This module provides a panel for browsing and selecting media files.
"""
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton
)

logger = logging.getLogger(__name__)


class LibraryPanel(QWidget):
    """Panel for displaying and selecting media files.
    
    Displays a list of available transcribed media files.
    
    Signals:
        mediaSelected: Emitted when a media file is selected
        deleteRequested: Emitted when a media file is deleted
    """
    mediaSelected = Signal(int)  # media_id
    deleteRequested = Signal(int)  # media_id
    
    def __init__(self, parent=None):
        """Initialize the library panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create list widget
        self.list = QListWidget()
        self.list.setMinimumWidth(200)
        self.list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Delete button
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.delete_btn, 0)
    
    def _on_selection_changed(self):
        """Handle selection change event."""
        item = self.list.currentItem()
        if item:
            media_id = item.data(Qt.UserRole)
            self.mediaSelected.emit(media_id)
    
    def _on_delete_clicked(self):
        """Handle delete button click event."""
        item = self.list.currentItem()
        if item:
            media_id = item.data(Qt.UserRole)
            self.deleteRequested.emit(media_id)
    
    def refresh(self, items: list) -> None:
        """Refresh the library list.
        
        Args:
            items: List of media items with id, name, path
        """
        # Remember current selection
        current_id = None
        item = self.list.currentItem()
        if item:
            current_id = item.data(Qt.UserRole)
        
        # Clear and rebuild list
        self.list.clear()
        for item in items:
            list_item = QListWidgetItem(item["name"])
            list_item.setData(Qt.UserRole, item["id"])
            self.list.addItem(list_item)
        
        # Restore selection if item still exists
        if current_id:
            for i in range(self.list.count()):
                item = self.list.item(i)
                if item.data(Qt.UserRole) == current_id:
                    self.list.setCurrentItem(item)
                    break