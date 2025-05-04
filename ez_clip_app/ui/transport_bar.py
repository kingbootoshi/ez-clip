"""
TransportBar widget for media playback controls.

This module defines a widget with play/pause button and position slider 
for controlling media playback.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QStyle


class TransportBar(QWidget):
    """Media player transport controls widget.
    
    Provides play/pause button and position slider for media playback control.
    
    Signals:
        playClicked: Emitted when the play button is clicked
        pauseClicked: Emitted when the pause button is clicked
        seek: Emitted with position in seconds when slider is released
    """
    playClicked = Signal()
    pauseClicked = Signal()
    seek = Signal(float)  # seconds
    
    def __init__(self, parent=None):
        """Initialize the TransportBar widget.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Set up layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Play/Pause button
        self.btn = QPushButton("▶")
        self.btn.setFixedWidth(40)
        self.btn.clicked.connect(self._toggle_play_pause)
        layout.addWidget(self.btn)
        
        # Position slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)  # Will be updated with actual duration
        self.slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.slider)
        
        # Flag to track play state
        self.is_playing = False
    
    def _toggle_play_pause(self):
        """Toggle between play and pause states."""
        if not self.is_playing:
            self.playClicked.emit()
            self.btn.setText("⏸")
            self.is_playing = True
        else:
            self.pauseClicked.emit()
            self.btn.setText("▶")
            self.is_playing = False
    
    def _on_slider_released(self):
        """Handle slider release event to seek to new position."""
        # Convert slider value (0-1000) to seconds
        position_ms = self.slider.value()
        self.seek.emit(position_ms / 1000.0)
    
    def update_position(self, position_ms):
        """Update the slider position without triggering signals.
        
        Args:
            position_ms: Current position in milliseconds
        """
        # Avoid recursive signal emission by blocking signals
        self.slider.blockSignals(True)
        self.slider.setValue(position_ms)
        self.slider.blockSignals(False)
    
    def update_duration(self, duration_ms):
        """Update the slider range based on media duration.
        
        Args:
            duration_ms: Media duration in milliseconds
        """
        self.slider.setRange(0, duration_ms)
    
    def set_playing(self, playing):
        """Set the playing state of the button.
        
        Args:
            playing: True if playing, False if paused
        """
        self.is_playing = playing
        self.btn.setText("⏸" if playing else "▶")