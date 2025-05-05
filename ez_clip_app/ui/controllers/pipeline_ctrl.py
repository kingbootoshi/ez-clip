"""
Pipeline controller for the EZ CLIP application.

This module handles media file transcription pipeline orchestration.
"""
import logging
import threading
from pathlib import Path
from collections import deque

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ez_clip_app.config import Status, MAX_CONCURRENT_JOBS
from ez_clip_app.data.database import DB
from ez_clip_app.core.pipeline import JobSettings, process_file, PipelineError
from ez_clip_app.ui.event_bus import BUS

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Signals for worker thread communication."""
    finished = Signal(int, int)  # job_id, transcript_id
    error = Signal(int, str)     # job_id, error_message
    progress = Signal(int, float)  # job_id, progress_percentage


class TranscriptionWorker(QRunnable):
    """Worker thread for running transcription jobs."""
    
    def __init__(self, job_id: int, media_path: Path, settings: JobSettings, db: DB):
        super().__init__()
        self.job_id = job_id
        self.media_path = media_path
        self.settings = settings
        self.db = db
        self.signals = WorkerSignals()
    
    @Slot()
    def run(self):
        """Process the file in a background thread."""
        try:
            def progress_callback(prog):
                # Debug log progress every 5%
                if int(prog) % 5 == 0:
                    logger.debug("Job %d progress: %.1f%%", self.job_id, prog)
                self.signals.progress.emit(self.job_id, prog)
                
            transcript_id = process_file(
                self.media_path,
                self.settings,
                self.db,
                progress_callback
            )
            self.signals.finished.emit(self.job_id, transcript_id)
        except PipelineError as e:
            logger.error("Pipeline error for job %d: %s", self.job_id, str(e), exc_info=True)
            self.signals.error.emit(self.job_id, str(e))
        except Exception as e:
            logger.error("Unexpected error for job %d: %s", self.job_id, str(e), exc_info=True)
            self.signals.error.emit(self.job_id, f"Unexpected error: {e}")


class PipelineController:
    """Controller for transcription pipeline operations.
    
    Manages a queue of jobs and processes them using worker threads.
    """
    
    def __init__(self, db: DB):
        """Initialize the controller.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.job_queue = deque()
        self.running_jobs = set()  # Track running job IDs
        self.threadpool = QThreadPool()
        
        # Connect to event bus
        BUS.fileSelected.connect(self.enqueue)
        BUS.enqueueJob.connect(self.enqueue)
        
        # Log thread pool configuration
        logger.info("Pipeline controller initialized with %d worker threads", 
                   self.threadpool.maxThreadCount())
    
    def enqueue(self, path: Path, settings: JobSettings = None) -> int:
        """Add a job to the queue.
        
        Args:
            path: Path to the media file
            settings: Optional job settings, uses defaults if not provided
            
        Returns:
            Job ID
        """
        # If settings not provided, use the defaults from JobSettings
        if settings is None:
            settings = JobSettings()
        
        # Add to database
        job_id = self.db.insert_media(path)
        
        # Add to queue
        self.job_queue.append((job_id, path, settings))
        
        logger.info("Enqueued %s as job %d", path.name, job_id)
        
        # Start processing if possible
        self.start_next()
        
        return job_id
    
    def start_next(self):
        """Start the next job in the queue if worker slots available."""
        # Check if we can start another job
        if len(self.running_jobs) >= MAX_CONCURRENT_JOBS or not self.job_queue:
            return
            
        # Get next job
        job_id, media_path, settings = self.job_queue.popleft()
        
        # Create worker
        worker = TranscriptionWorker(job_id, media_path, settings, self.db)
        
        # Connect signals
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_job_finished)
        worker.signals.error.connect(self._on_job_error)
        
        # Add to running set
        self.running_jobs.add(job_id)
        
        # Start worker
        self.threadpool.start(worker)
        
        # Update job status
        self.db.set_status(job_id, Status.RUNNING)
        
    def _on_progress(self, job_id: int, progress: float):
        """Handle job progress updates.
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
        # Update progress in DB
        self.db.update_progress(job_id, progress)
        
        # Forward to event bus
        BUS.jobProgress.emit(job_id, progress)
    
    def _on_job_finished(self, job_id: int, transcript_id: int):
        """Handle job completion.
        
        Args:
            job_id: Job ID
            transcript_id: Transcript ID
        """
        # Remove from running set
        self.running_jobs.remove(job_id)
        
        # Forward to event bus
        BUS.jobFinished.emit(job_id, transcript_id)
        BUS.refreshLibrary.emit()
        
        # Log success
        logger.info("Job %d completed successfully", job_id)
        
        # Start next job if available
        self.start_next()
    
    def _on_job_error(self, job_id: int, error_msg: str):
        """Handle job errors.
        
        Args:
            job_id: Job ID
            error_msg: Error message
        """
        # Remove from running set
        self.running_jobs.remove(job_id)
        
        # Update DB with error status
        self.db.set_error(job_id, error_msg)
        
        # Log error
        logger.error("Job %d failed: %s", job_id, error_msg)
        
        # Start next job if available
        self.start_next()