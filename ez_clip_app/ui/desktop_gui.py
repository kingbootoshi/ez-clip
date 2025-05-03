"""
Desktop GUI for the WhisperX transcription app using PySide6.
"""
import sys
import logging
import threading
import typing as t
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog, QComboBox,
    QCheckBox, QSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QFormLayout, QMessageBox, QSplitter
)
from PySide6.QtCore import QRunnable, QThreadPool

from ..config import (
    DEFAULT_MODEL_SIZE, DEFAULT_LANGUAGE, DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS, POLL_INTERVAL_MS, Status, HF_TOKEN
)
from ..data.database import DB
from ..core.pipeline import process_file, JobSettings, PipelineError

# Set up logging
logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Signals for worker thread communication."""
    finished = Signal(int)  # Emits transcript ID on success
    error = Signal(str)     # Emits error message on failure
    progress = Signal(float)  # Emits progress percentage (0-100)


class TranscriptionWorker(QRunnable):
    """Worker thread for running transcription jobs."""
    
    def __init__(self, media_path: Path, settings: JobSettings, db: DB):
        super().__init__()
        self.media_path = media_path
        self.settings = settings
        self.db = db
        self.signals = WorkerSignals()
    
    @Slot()
    def run(self):
        """Process the file in a background thread."""
        try:
            transcript_id = process_file(
                self.media_path,
                self.settings,
                self.db,
                self.signals.progress.emit
            )
            self.signals.finished.emit(transcript_id)
        except PipelineError as e:
            logger.error(f"Pipeline error: {e}")
            self.signals.error.emit(str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.signals.error.emit(f"Unexpected error: {e}")


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize database
        self.db = DB()
        
        # Set up thread pool for background tasks
        self.threadpool = QThreadPool()
        logger.info(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")
        
        # Set up the UI
        self.init_ui()
        
        # Set up timer for progress updates
        self.timer = QTimer()
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self.poll_progress)
        self.timer.start()
        
        # Track active jobs
        self.active_jobs = {}  # {job_id: progress_bar}
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("EZ Clip")
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Top section - File selection and job controls
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # File selection button
        self.select_file_btn = QPushButton("Select Media File")
        self.select_file_btn.clicked.connect(self.on_select_file)
        top_layout.addWidget(self.select_file_btn)
        
        # Settings group
        settings_group = QGroupBox("Transcription Settings")
        settings_layout = QFormLayout(settings_group)
        
        # Model dropdown
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v1", "large-v2"])
        self.model_combo.setCurrentText(DEFAULT_MODEL_SIZE)
        settings_layout.addRow("Model Size:", self.model_combo)
        
        # Language dropdown
        self.language_combo = QComboBox()
        self.language_combo.addItems(["en", "auto", "es", "fr", "de", "it", "pt", "nl", "ja", "zh"])
        self.language_combo.setCurrentText(DEFAULT_LANGUAGE)
        settings_layout.addRow("Language:", self.language_combo)
        
        # Diarization checkbox
        self.diarize_checkbox = QCheckBox()
        self.diarize_checkbox.setChecked(True)
        self.diarize_checkbox.toggled.connect(self.on_diarize_toggled)
        settings_layout.addRow("Enable Speaker Diarization:", self.diarize_checkbox)
        
        # Speaker settings
        self.speakers_layout = QHBoxLayout()
        
        self.min_speakers_spin = QSpinBox()
        self.min_speakers_spin.setRange(1, 10)
        self.min_speakers_spin.setValue(DEFAULT_MIN_SPEAKERS)
        
        self.max_speakers_spin = QSpinBox()
        self.max_speakers_spin.setRange(1, 10)
        self.max_speakers_spin.setValue(DEFAULT_MAX_SPEAKERS)
        
        self.speakers_layout.addWidget(QLabel("Min:"))
        self.speakers_layout.addWidget(self.min_speakers_spin)
        self.speakers_layout.addWidget(QLabel("Max:"))
        self.speakers_layout.addWidget(self.max_speakers_spin)
        
        settings_layout.addRow("Speakers:", self.speakers_layout)
        
        top_layout.addWidget(settings_group)
        main_layout.addWidget(top_panel)
        
        # Middle section - Active jobs with progress bars
        self.jobs_group = QGroupBox("Active Jobs")
        self.jobs_layout = QVBoxLayout(self.jobs_group)
        main_layout.addWidget(self.jobs_group)
        
        # Bottom section - Results display
        self.results_tabs = QTabWidget()
        
        # Transcript tab
        self.transcript_widget = QWidget()
        transcript_layout = QVBoxLayout(self.transcript_widget)
        
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        transcript_layout.addWidget(self.transcript_text)
        
        # Segments tab
        self.segments_widget = QWidget()
        segments_layout = QVBoxLayout(self.segments_widget)
        
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(4)
        self.segments_table.setHorizontalHeaderLabels(["Speaker", "Start", "End", "Text"])
        self.segments_table.horizontalHeader().setStretchLastSection(True)
        segments_layout.addWidget(self.segments_table)
        
        # Add tabs
        self.results_tabs.addTab(self.transcript_widget, "Full Transcript")
        self.results_tabs.addTab(self.segments_widget, "Segments")
        
        main_layout.addWidget(self.results_tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Set central widget
        self.setCentralWidget(main_widget)
    
    def on_diarize_toggled(self, checked):
        """Enable/disable speaker settings based on diarization checkbox."""
        for i in range(self.speakers_layout.count()):
            widget = self.speakers_layout.itemAt(i).widget()
            if widget:
                widget.setEnabled(checked)
    
    def on_select_file(self):
        """Open file dialog and start processing selected file."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Select Media File",
            str(Path.home()),
            "Media Files (*.mp4 *.mp3 *.wav *.avi *.mkv *.m4a *.flac);;All Files (*)"
        )
        
        if not file_path:
            return
        
        media_path = Path(file_path)
        self.statusBar().showMessage(f"Selected file: {media_path.name}")
        
        # Create job settings
        settings = JobSettings(
            model_size=self.model_combo.currentText(),
            language=self.language_combo.currentText(),
            diarize=self.diarize_checkbox.isChecked(),
            min_speakers=self.min_speakers_spin.value(),
            max_speakers=self.max_speakers_spin.value(),
            hf_token=HF_TOKEN
        )
        
        # Add job to database
        job_id = self.db.insert_media(media_path)
        
        # Create progress bar for this job
        job_widget = QWidget()
        job_layout = QHBoxLayout(job_widget)
        job_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add file name label
        file_label = QLabel(f"{media_path.name}")
        job_layout.addWidget(file_label)
        
        # Add progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        job_layout.addWidget(progress_bar)
        
        # Add to jobs layout
        self.jobs_layout.addWidget(job_widget)
        
        # Track this job
        self.active_jobs[job_id] = {
            'progress_bar': progress_bar,
            'widget': job_widget,
            'file_path': str(media_path)
        }
        
        # Start processing in background thread
        worker = TranscriptionWorker(media_path, settings, self.db)
        worker.signals.progress.connect(lambda p: self.update_progress(job_id, p))
        worker.signals.finished.connect(lambda transcript_id: self.on_job_completed(job_id, transcript_id))
        worker.signals.error.connect(lambda msg: self.on_job_error(job_id, msg))
        
        self.threadpool.start(worker)
        self.statusBar().showMessage(f"Processing: {media_path.name}")
    
    def update_progress(self, job_id, progress):
        """Update progress bar for a specific job."""
        if job_id in self.active_jobs:
            self.active_jobs[job_id]['progress_bar'].setValue(int(progress))
    
    def poll_progress(self):
        """Poll database for progress updates on active jobs."""
        active_db_jobs = self.db.get_active_jobs()
        
        for row in active_db_jobs:
            job_id = row['id']
            status = row['status']
            progress = row['progress']
            
            # Update progress bar if we're tracking this job
            if job_id in self.active_jobs:
                self.update_progress(job_id, progress)
                
                # If job is done but we haven't processed it yet
                if status == Status.DONE:
                    self.display_transcript(job_id)
                    self.statusBar().showMessage(f"Transcription complete: {row['filepath']}")
                
                # If job has errored but we haven't processed it yet
                elif status == Status.ERROR:
                    media_path = Path(row['filepath']).name
                    QMessageBox.warning(
                        self,
                        "Transcription Error",
                        f"Error processing {media_path}. Check logs for details."
                    )
                    # Clean up UI for failed job
                    job_widget = self.active_jobs[job_id]['widget']
                    self.jobs_layout.removeWidget(job_widget)
                    job_widget.deleteLater()
                    del self.active_jobs[job_id]
    
    def on_job_completed(self, job_id, transcript_id):
        """Handle job completion."""
        self.display_transcript(job_id)
    
    def on_job_error(self, job_id, error_msg):
        """Handle job error."""
        media_path = Path(self.active_jobs[job_id]['file_path']).name
        QMessageBox.warning(
            self,
            "Transcription Error",
            f"Error processing {media_path}: {error_msg}"
        )
        # Clean up UI for failed job
        job_widget = self.active_jobs[job_id]['widget']
        self.jobs_layout.removeWidget(job_widget)
        job_widget.deleteLater()
        del self.active_jobs[job_id]
    
    def display_transcript(self, job_id):
        """Display transcript and segments for completed job."""
        result = self.db.get_transcript(job_id)
        
        if not result:
            logger.warning(f"No transcript found for job {job_id}")
            return
        
        # Display full transcript
        transcript_text = result["transcript"]["full_text"]
        self.transcript_text.setPlainText(transcript_text)
        
        # Display segments in table
        segments = result["segments"]
        self.segments_table.setRowCount(len(segments))
        
        for i, segment in enumerate(segments):
            # Speaker
            speaker_item = QTableWidgetItem(segment["speaker"])
            self.segments_table.setItem(i, 0, speaker_item)
            
            # Start time (format as MM:SS.ms)
            start_secs = segment["start_sec"]
            start_formatted = f"{int(start_secs // 60):02d}:{start_secs % 60:05.2f}"
            start_item = QTableWidgetItem(start_formatted)
            self.segments_table.setItem(i, 1, start_item)
            
            # End time (format as MM:SS.ms)
            end_secs = segment["end_sec"]
            end_formatted = f"{int(end_secs // 60):02d}:{end_secs % 60:05.2f}"
            end_item = QTableWidgetItem(end_formatted)
            self.segments_table.setItem(i, 2, end_item)
            
            # Text
            text_item = QTableWidgetItem(segment["text"])
            self.segments_table.setItem(i, 3, text_item)
        
        self.segments_table.resizeColumnsToContents()
        
        # Clean up UI for completed job
        if job_id in self.active_jobs:
            job_widget = self.active_jobs[job_id]['widget']
            self.jobs_layout.removeWidget(job_widget)
            job_widget.deleteLater()
            del self.active_jobs[job_id]