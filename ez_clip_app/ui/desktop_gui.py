"""
Desktop GUI for the WhisperX transcription app using PySide6.
"""
import sys
import logging
import threading
import typing as t
from pathlib import Path
from collections import deque
import importlib.resources as pkg_res

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog, QComboBox,
    QCheckBox, QSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QFormLayout, QMessageBox, QSplitter,
    QListWidget, QListWidgetItem, QInputDialog, QSystemTrayIcon
)
from PySide6.QtCore import QRunnable, QThreadPool, QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtGui import QIcon
from ez_clip_app.assets import ezclip_rc  # noqa: F401

from ..config import (
    DEFAULT_MODEL_SIZE, DEFAULT_LANGUAGE, DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS, POLL_INTERVAL_MS, Status, HF_TOKEN,
    MAX_CONCURRENT_JOBS
)
from ..data.database import DB
from ..core.pipeline import process_file, JobSettings, PipelineError
from ..core.formatting import segments_to_markdown
from ..core.models import Segment, Word, TranscriptionResult
from ..ui.player_widget import PlayerWidget

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
        
        # Job queue and state
        self.job_queue = deque()
        self.job_running = False
        
        # Set up the UI
        self.init_ui()
        
        # Set up timer for progress updates
        self.timer = QTimer()
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self.poll_progress)
        self.timer.start()
        
        # Track active jobs
        self.active_jobs = {}  # {job_id: progress_bar}
        
        # Track current media ID
        self.current_media_id = None
        
        # Tray icon (needed for showMessage on mac/Win)
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(":/ezclip_icon"))
        self.tray.setToolTip("EZ CLIP – ready")
        self.tray.setVisible(True)
        
        # Window-level icon (makes sure even secondary windows carry it)
        self.setWindowIcon(QIcon(":/ezclip_icon"))
        
        # Preload chime
        mp3_path = str(pkg_res.files("ez_clip_app.assets") / "finish.wav")
        self.done_sound = QSoundEffect()
        self.done_sound.setSource(QUrl.fromLocalFile(mp3_path))
        self.done_sound.setVolume(0.9)
        
        # Populate library with existing completed media files
        self.refresh_library()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("EZ CLIP")
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
        
        # Bottom section - Library and Results in a splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Player column (top-left)
        self.player = PlayerWidget()
        player_frame = QWidget()
        pf_layout = QVBoxLayout(player_frame)
        pf_layout.setContentsMargins(0, 0, 0, 0)
        pf_layout.addWidget(self.player)
        
        # Library sidebar on the left
        self.library = QListWidget()
        self.library.setMinimumWidth(200)
        self.library.itemSelectionChanged.connect(self.load_selected_media)
        
        # — Delete button under the library
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected_media)
        left_col = QVBoxLayout()          # wrap library + button
        left_col.addWidget(self.library, 1)
        left_col.addWidget(self.delete_btn, 0)
        left_container = QWidget()
        left_container.setLayout(left_col)
        
        # Build left-hand splitter: player over library
        left_split = QSplitter(Qt.Vertical)
        left_split.addWidget(player_frame)
        left_split.addWidget(left_container)
        splitter.insertWidget(0, left_split)
        
        # Results tabs on the right
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
        # Connect signals for interaction
        self.segments_table.cellDoubleClicked.connect(self.prompt_rename)
        self.segments_table.cellClicked.connect(self.on_segment_clicked)
        segments_layout.addWidget(self.segments_table)
        
        # Words tab – shows the words of the currently selected segment
        self.words_widget = QWidget()
        words_layout = QVBoxLayout(self.words_widget)
        self.words_table = QTableWidget()
        self.words_table.setColumnCount(4)
        self.words_table.setHorizontalHeaderLabels(
            ["Word", "Start", "End", "Score"]
        )
        self.words_table.horizontalHeader().setStretchLastSection(True)
        self.words_table.cellDoubleClicked.connect(self.edit_word)
        self.words_table.cellClicked.connect(self.on_word_clicked)
        words_layout.addWidget(self.words_table)
        
        # Add tabs
        self.results_tabs.addTab(self.transcript_widget, "Full Transcript")
        self.results_tabs.addTab(self.segments_widget, "Segments")
        self.results_tabs.addTab(self.words_widget, "Words")
        
        # Connect tab change signal to auto-select first row when Words tab is selected
        self.results_tabs.currentChanged.connect(self.on_tab_changed)
        
        # Add results_tabs to the splitter
        splitter.addWidget(self.results_tabs)
        
        # Set default sizes (30% for library, 70% for results)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
        
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
        """Open file dialog and start processing selected files."""
        file_dialog = QFileDialog()
        paths, _ = file_dialog.getOpenFileNames(
            self,
            "Select Media Files",
            str(Path.home()),
            "Media Files (*.mp4 *.mp3 *.wav *.avi *.mkv *.m4a *.flac);;All Files (*)"
        )
        
        if not paths:
            return
            
        for p in paths:
            self.enqueue_job(Path(p))
            
        self.start_next_job()
        
    def enqueue_job(self, media_path: Path):
        """Add a job to the queue."""
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
        
        # Add to queue
        self.job_queue.append((media_path, settings, job_id))
        self.statusBar().showMessage(f"Queued: {media_path.name}")
        
    def start_next_job(self):
        """Start the next job in the queue if not already running a job."""
        if self.job_running or not self.job_queue:
            return
            
        media_path, settings, job_id = self.job_queue.popleft()
        
        # Start processing in background thread
        worker = TranscriptionWorker(media_path, settings, self.db)
        worker.signals.progress.connect(lambda p: self.update_progress(job_id, p))
        worker.signals.finished.connect(lambda transcript_id: self.on_job_completed(job_id, transcript_id))
        worker.signals.error.connect(lambda msg: self.on_job_error(job_id, msg))
        
        self.threadpool.start(worker)
        self.job_running = True
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
                    self.refresh_library()
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
        self.job_running = False
        self.display_transcript(job_id)
        
        # Refresh the library to show the newly completed job
        self.refresh_library()
        
        # Notify user of completion
        file_name = Path(self.db.get_media_path(job_id)).name
        self._notify_done(file_name)
        
        # Start the next job in the queue
        self.start_next_job()
    
    def on_job_error(self, job_id, error_msg):
        """Handle job error."""
        self.job_running = False
        
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
        
        # Start the next job in the queue
        self.start_next_job()
        
    def _notify_done(self, fname: str):
        """Play a sound and show notification when job is complete."""
        # Always play sound
        self.done_sound.play()
        
        # Banner - keep if useful on mac; harmless on Win/Linux
        self.tray.showMessage(
            "EZ Clip – Job Finished",
            f"{fname} is ready!",
            QSystemTrayIcon.Information,
            5000
        )
        
    def delete_selected_media(self):
        item = self.library.currentItem()
        if not item:
            return

        media_id = item.data(Qt.UserRole)
        fname = item.text()

        reply = QMessageBox.question(
            self,
            "Delete Transcript",
            f"Delete all data for \"{fname}\"?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # DB removal
        self.db.delete_media(media_id)

        # If that transcript is on screen, clear panes
        if self.current_media_id == media_id:
            self.current_media_id = None
            self.transcript_text.clear()
            self.segments_table.setRowCount(0)

        # Refresh library list
        self.refresh_library()
        self.statusBar().showMessage(f"Deleted: {fname}", 3000)
    
    def refresh_library(self):
        """Refresh the library list with completed media files."""
        self.library.clear()
        for row in self.db.get_finished_media():
            item = QListWidgetItem(Path(row["filepath"]).name)
            item.setData(Qt.UserRole, row["id"])
            self.library.addItem(item)
    
    def load_selected_media(self):
        """Load the selected media file from the library."""
        item = self.library.currentItem()
        if not item:
            return
        
        media_id = item.data(Qt.UserRole)
        self.display_transcript(media_id)
    
    def prompt_rename(self, row, col):
        """Prompt to rename a speaker when double-clicking the speaker column."""
        # Only handle clicks on the speaker column (column 0)
        if col != 0:
            return
            
        speaker_id = self.segments_table.item(row, 0).text()
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Speaker", 
            f"New name for {speaker_id}:"
        )
        
        if not ok or not new_name.strip():
            return
            
        # Save the new speaker name to the database
        self.db.set_speaker_name(self.current_media_id, speaker_id, new_name.strip())
        
        # Reload the transcript to show the updated speaker names
        self.display_transcript(self.current_media_id)
    
    def display_transcript(self, job_id):
        """Display transcript and segments for completed job."""
        result: TranscriptionResult = self.db.get_transcript(job_id)
        
        if not result:
            logger.warning(f"No transcript found for job {job_id}")
            return
        
        # Store the current media ID
        self.current_media_id = job_id
        
        # Get speaker map for this media
        speaker_map = self.db.get_speaker_map(job_id)
        
        # Get segments as dicts for formatting (segments_to_markdown expects dicts)
        segments_dicts = [
            {
                "id": seg.id,
                "speaker": seg.speaker,
                "start": seg.start_sec,  # Map to expected key for formatter
                "end": seg.end_sec,      # Map to expected key for formatter
                "start_sec": seg.start_sec,
                "end_sec": seg.end_sec,
                "text": seg.text,
                "words": [w.model_dump() for w in seg.words]
            }
            for seg in result.segments
        ]
        
        # Always regenerate Markdown with current speaker names
        regenerated_markdown = segments_to_markdown(segments_dicts, speaker_map)
        
        # Display regenerated transcript
        self.transcript_text.setMarkdown(regenerated_markdown)
        
        # Update the DB to persist the regenerated Markdown
        self.db.update_transcript_text(job_id, regenerated_markdown)
        
        # Display segments in table
        self.segments_table.setRowCount(len(result.segments))
        
        for i, segment in enumerate(result.segments):
            # Get segment ID and store it for later use
            seg_id = segment.id
            
            # Speaker (use friendly name if available)
            speaker_id = segment.speaker
            display_name = speaker_map.get(speaker_id, speaker_id)
            speaker_item = QTableWidgetItem(display_name)
            # Store segment_id in UserRole data
            speaker_item.setData(Qt.UserRole, seg_id)
            self.segments_table.setItem(i, 0, speaker_item)
            
            # Start time (format as MM:SS.ms)
            start_secs = segment.start_sec
            start_formatted = f"{int(start_secs // 60):02d}:{start_secs % 60:05.2f}"
            start_item = QTableWidgetItem(start_formatted)
            self.segments_table.setItem(i, 1, start_item)
            
            # End time (format as MM:SS.ms)
            end_secs = segment.end_sec
            end_formatted = f"{int(end_secs // 60):02d}:{end_secs % 60:05.2f}"
            end_item = QTableWidgetItem(end_formatted)
            self.segments_table.setItem(i, 2, end_item)
            
            # Text
            text_item = QTableWidgetItem(segment.text)
            self.segments_table.setItem(i, 3, text_item)
        
        self.segments_table.resizeColumnsToContents()
        
        # Connect segment selection to word loading
        self.segments_table.cellClicked.connect(self.load_words_for_segment)
        
        # Auto-select the first row if segments exist
        if self.segments_table.rowCount() > 0:
            self.segments_table.selectRow(0)
            self.load_words_for_segment(0, 0)
        
        # Clean up UI for completed job
        if job_id in self.active_jobs:
            job_widget = self.active_jobs[job_id]['widget']
            self.jobs_layout.removeWidget(job_widget)
            job_widget.deleteLater()
            del self.active_jobs[job_id]
            
        # Auto-load media in player if available
        media_path = self.db.get_media_path(job_id)
        if media_path and Path(media_path).exists():
            self.player.load(Path(media_path))
            
    def load_words_for_segment(self, row, _col):
        """Load words for the selected segment.
        
        Args:
            row: The selected row index
            _col: The selected column index (ignored)
        """
        # Get segment_id from the UserRole data
        seg_item = self.segments_table.item(row, 0)
        segment_id = seg_item.data(Qt.UserRole)
        
        # Get segment using segment_id
        seg: Segment = self.db.get_segment(segment_id)
        
        self.words_table.setRowCount(len(seg.words))
        for i, w in enumerate(seg.words):
            word_item = QTableWidgetItem(w.w)
            # Store word index in UserRole data
            word_item.setData(Qt.UserRole, i)  # index within seg.words
            self.words_table.setItem(i, 0, word_item)
            
            self.words_table.setItem(i, 1, QTableWidgetItem(f"{w.s:.2f}"))
            self.words_table.setItem(i, 2, QTableWidgetItem(f"{w.e:.2f}"))
            self.words_table.setItem(i, 3, QTableWidgetItem(f"{w.score or 0:.2f}"))
        self.words_table.resizeColumnsToContents()
        
    def on_tab_changed(self, index):
        """Handle tab change events.
        
        Args:
            index: The index of the newly selected tab
        """
        # If Words tab is selected (index 2) and no segment is selected, auto-select first row
        if index == 2 and self.segments_table.currentRow() == -1 and self.segments_table.rowCount() > 0:
            self.segments_table.selectRow(0)
            self.load_words_for_segment(0, 0)
    
    def on_segment_clicked(self, row, _col):
        """Seek to the selected segment position.
        
        Args:
            row: The selected row index
            _col: The selected column index (ignored)
        """
        # Get segment_id from the UserRole data
        seg_item = self.segments_table.item(row, 0)
        segment_id = seg_item.data(Qt.UserRole)
        
        # Get segment using segment_id
        seg: Segment = self.db.get_segment(segment_id)
        
        # Seek to the segment start time
        self.player.seek(seg.start_sec)
    
    def on_word_clicked(self, row, _col):
        """Seek to the selected word position.
        
        Args:
            row: The selected row index
            _col: The selected column index (ignored) 
        """
        # Get start time directly from the table
        start_sec = float(self.words_table.item(row, 1).text())
        self.player.seek(start_sec)
            
    def edit_word(self, row, col):
        """Handle word editing.
        
        Args:
            row: The selected row index
            col: The selected column index
        """
        if col != 0:   # only text column editable
            return
            
        # Get the current segment row
        seg_row = self.segments_table.currentRow()
        
        # Get segment_id from the UserRole data
        seg_item = self.segments_table.item(seg_row, 0)
        segment_id = seg_item.data(Qt.UserRole)
        
        # Get word index from the UserRole data
        word_item = self.words_table.item(row, 0)
        word_index = word_item.data(Qt.UserRole)
        
        # Get segment and associated word ID
        seg: Segment = self.db.get_segment(segment_id)
        word_id = self.db.get_words_by_segment(segment_id)[word_index]["id"]
        
        # Get old text and prompt for new text
        old = word_item.text()
        new, ok = QInputDialog.getText(self, "Edit Word", "Correct word:", text=old)
        if not ok or new.strip() == old:
            return
            
        # Update DB with new text
        self.db.update_word(segment_id, word_id, new.strip())
        
        # Reload panes
        self.display_transcript(self.current_media_id)
        self.load_words_for_segment(seg_row, 0)