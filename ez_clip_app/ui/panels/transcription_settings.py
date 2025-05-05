"""
Transcription settings panel for the EZ CLIP application.

This module provides a panel for configuring transcription job settings.
"""
import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QGroupBox, QFormLayout, QComboBox, QCheckBox, 
    QSpinBox, QHBoxLayout, QLabel
)

from ez_clip_app.config import (
    DEFAULT_MODEL_SIZE, DEFAULT_LANGUAGE, DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS, HF_TOKEN
)
from ez_clip_app.core.pipeline import JobSettings

logger = logging.getLogger(__name__)


class TranscriptionSettingsPanel(QWidget):
    """Panel for configuring transcription settings.
    
    Provides UI controls for setting transcription parameters.
    
    Signals:
        settingsChanged: Emitted when settings are changed
    """
    settingsChanged = Signal(JobSettings)
    
    def __init__(self, parent=None):
        """Initialize the settings panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create group box
        self.group = QGroupBox("Transcription Settings")
        form_layout = QFormLayout(self.group)
        
        # Model dropdown
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v1", "large-v2", "turbo"])
        self.model_combo.setCurrentText(DEFAULT_MODEL_SIZE)
        self.model_combo.currentTextChanged.connect(self._emit_settings)
        form_layout.addRow("Model Size:", self.model_combo)
        
        # Language dropdown
        self.language_combo = QComboBox()
        self.language_combo.addItems(["en", "auto", "es", "fr", "de", "it", "pt", "nl", "ja", "zh"])
        self.language_combo.setCurrentText(DEFAULT_LANGUAGE)
        self.language_combo.currentTextChanged.connect(self._emit_settings)
        form_layout.addRow("Language:", self.language_combo)
        
        # Diarization checkbox
        self.diarize_checkbox = QCheckBox()
        self.diarize_checkbox.setChecked(True)
        self.diarize_checkbox.toggled.connect(self._on_diarize_toggled)
        form_layout.addRow("Enable Speaker Diarization:", self.diarize_checkbox)
        
        # Speaker settings
        self.speakers_layout = QHBoxLayout()
        
        self.min_speakers_spin = QSpinBox()
        self.min_speakers_spin.setRange(1, 10)
        self.min_speakers_spin.setValue(DEFAULT_MIN_SPEAKERS)
        self.min_speakers_spin.valueChanged.connect(self._emit_settings)
        
        self.max_speakers_spin = QSpinBox()
        self.max_speakers_spin.setRange(1, 10)
        self.max_speakers_spin.setValue(DEFAULT_MAX_SPEAKERS)
        self.max_speakers_spin.valueChanged.connect(self._emit_settings)
        
        self.speakers_layout.addWidget(QLabel("Min:"))
        self.speakers_layout.addWidget(self.min_speakers_spin)
        self.speakers_layout.addWidget(QLabel("Max:"))
        self.speakers_layout.addWidget(self.max_speakers_spin)
        
        form_layout.addRow("Speakers:", self.speakers_layout)
        
        # Set main layout
        main_layout = QFormLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.group)
        
        # Initial settings
        self._emit_settings()
    
    def _on_diarize_toggled(self, checked):
        """Enable/disable speaker settings based on diarization checkbox.
        
        Args:
            checked: Checkbox state
        """
        for i in range(self.speakers_layout.count()):
            widget = self.speakers_layout.itemAt(i).widget()
            if widget:
                widget.setEnabled(checked)
        
        self._emit_settings()
    
    def _emit_settings(self):
        """Emit current settings."""
        settings = JobSettings(
            model_size=self.model_combo.currentText(),
            language=self.language_combo.currentText(),
            diarize=self.diarize_checkbox.isChecked(),
            min_speakers=self.min_speakers_spin.value(),
            max_speakers=self.max_speakers_spin.value(),
            hf_token=HF_TOKEN
        )
        
        self.settingsChanged.emit(settings)
    
    def get_settings(self) -> JobSettings:
        """Get current settings.
        
        Returns:
            Current job settings
        """
        return JobSettings(
            model_size=self.model_combo.currentText(),
            language=self.language_combo.currentText(),
            diarize=self.diarize_checkbox.isChecked(),
            min_speakers=self.min_speakers_spin.value(),
            max_speakers=self.max_speakers_spin.value(),
            hf_token=HF_TOKEN
        )