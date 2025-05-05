"""
Job queue panel for the EZ CLIP application.

This module provides a panel for monitoring active transcription jobs.
"""
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QPushButton
)

logger = logging.getLogger(__name__)


class JobQueuePanel(QWidget):
    """Panel for displaying and managing active jobs.
    
    Displays progress bars for all active transcription jobs.
    
    Signals:
        cancelJob: Emitted when a job is cancelled
    """
    cancelJob = Signal(int)
    
    def __init__(self, parent=None):
        """Initialize the job queue panel.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Create group
        self.group = QGroupBox("Active Jobs")
        self.jobs_layout = QVBoxLayout(self.group)
        
        # Set main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.group)
        
        # Store active jobs
        self.active_jobs = {}
    
    def add_job(self, job_id: int, media_path: Path) -> None:
        """Add a job to the queue.
        
        Args:
            job_id: Job ID
            media_path: Path to the media file
        """
        # Create job widget
        job_widget = QWidget()
        job_layout = QHBoxLayout(job_widget)
        job_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add filename label
        file_label = QLabel(f"{media_path.name}")
        job_layout.addWidget(file_label)
        
        # Add progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        job_layout.addWidget(progress_bar)
        
        # Add to jobs layout
        self.jobs_layout.addWidget(job_widget)
        
        # Store reference
        self.active_jobs[job_id] = {
            'progress_bar': progress_bar,
            'widget': job_widget,
            'file_path': str(media_path)
        }
    
    def update_progress(self, job_id: int, progress: float) -> None:
        """Update job progress.
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
        if job_id in self.active_jobs:
            self.active_jobs[job_id]['progress_bar'].setValue(int(progress))
    
    def remove_job(self, job_id: int) -> None:
        """Remove a job from the queue.
        
        Args:
            job_id: Job ID
        """
        if job_id in self.active_jobs:
            # Remove from layout
            job_widget = self.active_jobs[job_id]['widget']
            self.jobs_layout.removeWidget(job_widget)
            job_widget.deleteLater()
            
            # Remove from tracking dict
            del self.active_jobs[job_id]