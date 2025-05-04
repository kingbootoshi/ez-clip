"""
Player widget for video and audio playback in the EZ CLIP app.
"""
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


class PlayerWidget(QWidget):
    """Media player widget for video and audio playback.
    
    Wraps the QMediaPlayer with a simpler API for seeking and positioning.
    Emits signals with positions in seconds rather than milliseconds.
    """
    positionChanged = Signal(float)  # seconds
    
    def __init__(self, parent=None):
        """Initialize the player widget.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create media player and audio output
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(QAudioOutput(self))
        
        # Create video widget
        self.video = QVideoWidget(self)
        self.player.setVideoOutput(self.video)
        
        # Connect position signal (convert ms to seconds)
        self.player.positionChanged.connect(
            lambda ms: self.positionChanged.emit(ms/1000.0)
        )
        
        # Set up layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.video)
    
    def load(self, path: Path):
        """Load media file from path.
        
        Args:
            path: Path to media file
        """
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.pause()  # Load but don't play initially
    
    def seek(self, sec: float):
        """Seek to position in seconds.
        
        Args:
            sec: Position in seconds
        """
        self.player.setPosition(int(sec * 1000))