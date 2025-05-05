"""
Centralized event bus for the EZ CLIP application.

This module provides a singleton SignalBus class that acts as a central
event hub for communication between UI panels and controllers.
"""
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal

from ez_clip_app.core.pipeline import JobSettings

logger = logging.getLogger(__name__)


class SignalBus(QObject):
    """Centralized signal hub for the application.
    
    Provides typed signals for communication between components without
    requiring direct dependencies between them.
    """
    # ===== user-actions =====
    fileSelected = Signal(Path)                 # from FilePicker
    settingsChanged = Signal(JobSettings)       # from SettingsPanel
    enqueueJob = Signal(Path, JobSettings)      # composite
    segmentChosen = Signal(int)                 # segment_id
    wordChosen = Signal(float)                  # start_sec
    wordToggled = Signal(int, bool)             # idx, keep?

    # ===== pipeline feedback =====
    jobProgress = Signal(int, float)            # job_id, %
    jobFinished = Signal(int, int)              # job_id, transcript_id
    refreshLibrary = Signal()

    # ===== preview / player =====
    requestPreviewBuild = Signal(int)           # media_id


# Create a singleton instance for import by other modules
BUS = SignalBus()

# Export only the BUS instance for cleaner imports
__all__ = ["BUS"]