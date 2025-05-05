"""
File picker panel for the EZ CLIP application.

This module provides a simple file selection widget.
"""
import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFileDialog

logger = logging.getLogger(__name__)


class FilePickerPanel(QWidget):
    """Panel for selecting media files.
    
    Provides a button to open a file dialog and select media files.
    
    Signals:
        filePicked: Emitted when a file is selected with the file path
    """
    filePicked = Signal(Path)
    
    def __init__(self, parent=None):
        """Initialize the file picker panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create button
        self.select_btn = QPushButton("Select Media File")
        self.select_btn.clicked.connect(self._on_click)
        
        # Set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.select_btn)
    
    def _on_click(self):
        """Handle button click event."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open",
            str(Path.home()),
            "Media (*.mp4 *.mp3 *.wav *.mkv *.avi *.m4a *.flac);;All (*)"
        )
        
        if path:
            logger.info("User selected %s", path)
            self.filePicked.emit(Path(path))