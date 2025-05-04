"""
MediaPane widget for video playback with transport controls.

This module defines a widget that combines a PlayerWidget for video display
with a TransportBar for playback controls.
"""
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from .player_widget import PlayerWidget
from .transport_bar import TransportBar


class MediaPane(QWidget):
    """Combined video player and transport controls widget.
    
    Wraps a PlayerWidget and TransportBar, providing a unified API for
    media playback with controls.
    
    Signals:
        positionChanged: Emitted with position in seconds as media plays
    """
    positionChanged = Signal(float)  # seconds
    
    def __init__(self, parent=None):
        """Initialize the MediaPane.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create player widget
        self.player = PlayerWidget()
        layout.addWidget(self.player)
        
        # Create transport bar
        self.bar = TransportBar()
        layout.addWidget(self.bar)
        
        # Connect player signals to transport bar
        self.player.player.durationChanged.connect(self.bar.update_duration)
        self.player.player.positionChanged.connect(self._on_position_changed)
        
        # Connect transport bar signals to player
        self.bar.playClicked.connect(self.player.player.play)
        self.bar.pauseClicked.connect(self.player.player.pause)
        self.bar.seek.connect(lambda s: self.player.player.setPosition(int(s * 1000)))
    
    def _on_position_changed(self, position_ms):
        """Handle position change in the player.
        
        Args:
            position_ms: Current position in milliseconds
        """
        # Update the transport bar slider
        self.bar.update_position(position_ms)
        
        # Emit position in seconds for external connections
        self.positionChanged.emit(position_ms / 1000.0)
    
    def load(self, path: Path):
        """Load a media file.
        
        Args:
            path: Path to the media file
        """
        self.player.load(path)
        self.bar.set_playing(False)  # Reset play button state
    
    def play(self):
        """Start playback."""
        self.player.player.play()
        self.bar.set_playing(True)
    
    def pause(self):
        """Pause playback."""
        self.player.player.pause()
        self.bar.set_playing(False)
    
    def seek(self, position_sec: float):
        """Seek to a specific position.
        
        Args:
            position_sec: Position in seconds
        """
        self.player.seek(position_sec)