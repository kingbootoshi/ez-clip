"""
Main window for the EZ CLIP application.

This module ties together all panels and controllers into a coherent UI.

Note: While we have a general rule to keep files under 250 LOC, this one
file is exempted as it serves as the "composition root" that initializes
and wires together all the UI components. It contains minimal business logic,
mostly focusing on setup, initialization, and simple event handlers that
forward to appropriate controllers.
"""
import logging
import threading
import importlib.resources as pkg_res
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QStackedWidget, QMessageBox, 
    QSystemTrayIcon, QInputDialog, QFileDialog
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtMultimedia import QSoundEffect

from ez_clip_app.config import POLL_INTERVAL_MS, Status
from ez_clip_app.data.database import DB
from ez_clip_app.core import EditMask, PreviewRebuilder

# Import event bus
from ez_clip_app.ui.event_bus import BUS

# Import controllers
from ez_clip_app.ui.controllers.pipeline_ctrl import PipelineController
from ez_clip_app.ui.controllers.library_ctrl import LibraryController
from ez_clip_app.ui.controllers.editor_ctrl import EditorController

# Import panels
from ez_clip_app.ui.panels.file_picker import FilePickerPanel
from ez_clip_app.ui.panels.transcription_settings import TranscriptionSettingsPanel
from ez_clip_app.ui.panels.job_queue import JobQueuePanel
from ez_clip_app.ui.panels.library_panel import LibraryPanel
from ez_clip_app.ui.panels.transcript_view import TranscriptViewPanel
from ez_clip_app.ui.panels.segment_table import SegmentTablePanel
from ez_clip_app.ui.panels.word_table import WordTablePanel
from ez_clip_app.ui.panels.word_editor import WordEditorPanel

# Import media components
from ez_clip_app.ui.media_pane import MediaPane
from ez_clip_app.assets import ezclip_rc  # noqa: F401

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window.
    
    Orchestrates panels and controllers according to the MVC pattern.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("EZ CLIP")
        self.setMinimumSize(800, 600)
        self.setWindowIcon(QIcon(":/ezclip_icon"))
        
        # Initialize database
        self.db = DB()
        
        # Media ID being displayed currently
        self.current_media_id = None
        
        # Initialize UI components
        self._init_ui()
        
        # Initialize controllers
        self._init_controllers()
        
        # Set up event bus connections
        self._init_connections()
        
        # Set up timer for progress updates
        self.timer = QTimer()
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self._poll_progress)
        self.timer.start()
        
        # Tray icon
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(":/ezclip_icon"))
        self.tray.setToolTip("EZ CLIP – ready")
        self.tray.setVisible(True)
        
        # Preload notification sound
        mp3_path = str(pkg_res.files("ez_clip_app.assets") / "finish.wav")
        self.done_sound = QSoundEffect()
        self.done_sound.setSource(QUrl.fromLocalFile(mp3_path))
        self.done_sound.setVolume(0.9)
        
        # Initialize the library
        BUS.refreshLibrary.emit()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Add menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        # Export action
        export_action = QAction("Export Clip...", self)
        export_action.triggered.connect(self._on_export_clip)
        file_menu.addAction(export_action)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Top section - File selection and settings
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # Header stacked widget - contains either select button or player
        self.header_stack = QStackedWidget()
        
        # Page 0: File picker panel
        self.file_picker = FilePickerPanel()
        self.header_stack.addWidget(self.file_picker)
        
        # Page 1: Media pane
        self.media_pane = MediaPane()
        self.header_stack.addWidget(self.media_pane)
        
        # Add header stack to layout
        top_layout.addWidget(self.header_stack)
        
        # Settings panel
        self.settings_panel = TranscriptionSettingsPanel()
        top_layout.addWidget(self.settings_panel)
        
        # Add top panel to main layout
        main_layout.addWidget(top_panel)
        
        # Job queue panel
        self.job_queue = JobQueuePanel()
        main_layout.addWidget(self.job_queue)
        
        # Bottom section - Library and Results in a splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Library panel on the left
        self.library_panel = LibraryPanel()
        
        # Left side layout
        left_split = QSplitter(Qt.Vertical)
        left_split.addWidget(self.library_panel)
        splitter.addWidget(left_split)
        
        # Results tabs on the right
        self.results_tabs = QTabWidget()
        
        # Transcript tab
        self.transcript_panel = TranscriptViewPanel()
        self.results_tabs.addTab(self.transcript_panel, "Full Transcript")
        
        # Segments tab
        self.segments_panel = SegmentTablePanel()
        self.results_tabs.addTab(self.segments_panel, "Segments")
        
        # Words tab
        self.words_panel = WordTablePanel()
        self.results_tabs.addTab(self.words_panel, "Words")
        
        # Editor tab
        self.editor_panel = WordEditorPanel()
        self.results_tabs.addTab(self.editor_panel, "Editor")
        
        # Connect tab change signal
        self.results_tabs.currentChanged.connect(self._on_tab_changed)
        
        # Add results tabs to splitter
        splitter.addWidget(self.results_tabs)
        
        # Set default sizes (30% for library, 70% for results)
        splitter.setSizes([300, 700])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Set central widget
        self.setCentralWidget(main_widget)
    
    def _init_controllers(self):
        """Initialize the controllers."""
        # Create preview rebuilder
        self.preview_rebuilder = PreviewRebuilder(self.media_pane.player)
        
        # Initialize controllers
        self.pipeline_ctrl = PipelineController(self.db)
        self.library_ctrl = LibraryController(self.db)
        self.editor_ctrl = EditorController(self.db, self.preview_rebuilder)
    
    def _init_connections(self):
        """Initialize connections between components via the event bus."""
        # Connect file picker to event bus
        self.file_picker.filePicked.connect(BUS.fileSelected.emit)
        
        # Connect settings panel to event bus
        self.settings_panel.settingsChanged.connect(BUS.settingsChanged.emit)
        
        # Connect library panel to load media
        self.library_panel.mediaSelected.connect(self._on_media_selected)
        self.library_panel.deleteRequested.connect(self._on_delete_requested)
        
        # Connect segment panel
        self.segments_panel.segmentClicked.connect(self._on_segment_clicked)
        self.segments_panel.segmentDoubleClicked.connect(self._on_segment_double_clicked)
        
        # Connect word panel
        self.words_panel.wordClicked.connect(self._on_word_clicked)
        self.words_panel.wordDoubleClicked.connect(self._on_word_double_clicked)
        
        # Connect editor panel
        self.editor_panel.wordToggled.connect(BUS.wordToggled.emit)
        
        # Connect media pane
        self.media_pane.positionChanged.connect(self._on_player_position_changed)
        
        # Event bus connections
        BUS.refreshLibrary.connect(self._on_refresh_library)
        BUS.jobProgress.connect(self._on_job_progress)
        BUS.jobFinished.connect(self._on_job_finished)
        BUS.fileSelected.connect(self._on_file_selected)
        BUS.enqueueJob.connect(self._on_enqueue_job)
    
    def _poll_progress(self):
        """Poll database for progress updates on active jobs."""
        active_jobs = self.db.get_active_jobs()
        
        for row in active_jobs:
            job_id = row['id']
            status = row['status']
            progress = row['progress']
            
            # Update job queue
            self.job_queue.update_progress(job_id, progress)
            
            # If job is done but we haven't processed it yet
            if status == Status.DONE:
                # Emit job finished signal
                transcript = self.db.get_transcript(job_id)
                if transcript:
                    transcript_id = 0  # We don't actually need this, just emit job_id
                    BUS.jobFinished.emit(job_id, transcript_id)
    
    def _on_file_selected(self, path: Path):
        """Handle file selection.
        
        Args:
            path: Selected file path
        """
        # Get current settings
        settings = self.settings_panel.get_settings()
        
        # Use composite signal to ensure both path and settings are passed together
        BUS.enqueueJob.emit(path, settings)
    
    def _on_enqueue_job(self, path: Path, settings):
        """Handle job enqueued.
        
        Args:
            path: File path
            settings: Job settings
        """
        # Add to job queue panel
        job_id = self.pipeline_ctrl.enqueue(path, settings)
        self.job_queue.add_job(job_id, path)
    
    def _on_job_progress(self, job_id: int, progress: float):
        """Handle job progress update.
        
        Args:
            job_id: Job ID
            progress: Progress percentage
        """
        self.job_queue.update_progress(job_id, progress)
    
    def _on_job_finished(self, job_id: int, transcript_id: int):
        """Handle job completion.
        
        Args:
            job_id: Job ID
            transcript_id: Transcript ID
        """
        # Show notification
        file_name = Path(self.db.get_media_path(job_id)).name
        self._notify_done(file_name)
        
        # Remove from job queue
        self.job_queue.remove_job(job_id)
        
        # Refresh library to show the new item
        BUS.refreshLibrary.emit()
    
    def _on_refresh_library(self):
        """Handle library refresh event."""
        items = self.library_ctrl.refresh()
        self.library_panel.refresh(items)
    
    def _on_media_selected(self, media_id: int):
        """Handle media selection from library.
        
        Args:
            media_id: Media ID
        """
        self.current_media_id = media_id
        
        # Get transcript
        result = self.library_ctrl.get_transcript(media_id)
        if not result:
            logger.warning("No transcript found for media_id %d", media_id)
            return
        
        # Get speaker map
        speaker_map = self.db.get_speaker_map(media_id)
        
        # Update transcript panel
        self.transcript_panel.set_text(result.full_text)
        
        # Update segments panel
        self.segments_panel.set_segments(result.segments, speaker_map)
        
        # Initialize editor panel
        all_words = []
        for segment in result.segments:
            all_words.extend(segment.words)
        
        # Get or create edit mask
        edit_mask = self.db.get_edit_mask(media_id)
        if not edit_mask:
            edit_mask = EditMask(media_id, [True] * len(all_words))
            self.db.save_edit_mask(edit_mask)
        
        # Set up editor panel
        self.editor_panel.set_media(media_id, all_words, edit_mask)
        
        # Load media in player
        media_path = self.db.get_media_path(media_id)
        if media_path:
            path = Path(media_path)
            if path.exists():
                self.media_pane.load(path)
                self.header_stack.setCurrentIndex(1)  # Switch to player
            else:
                self._prompt_for_missing_file(media_id, path)
    
    def _prompt_for_missing_file(self, media_id: int, path: Path):
        """Prompt for missing media file.
        
        Args:
            media_id: Media ID
            path: Missing file path
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(f"Media file not found: {path}")
        msg_box.setInformativeText("Would you like to locate it?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        if msg_box.exec() == QMessageBox.Yes:
            new_path, _ = QFileDialog.getOpenFileName(
                self,
                "Locate Media File",
                str(Path.home()),
                "Media Files (*.mp4 *.mp3 *.wav *.avi *.mkv *.m4a *.flac);;All Files (*)"
            )
            
            if new_path:
                self.db.update_media_path(media_id, new_path)
                self.media_pane.load(Path(new_path))
                self.header_stack.setCurrentIndex(1)  # Switch to player
    
    def _on_delete_requested(self, media_id: int):
        """Handle media deletion request.
        
        Args:
            media_id: Media ID
        """
        file_name = Path(self.db.get_media_path(media_id)).name
        
        reply = QMessageBox.question(
            self,
            "Delete Transcript",
            f"Delete all data for \"{file_name}\"?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # If that transcript is on screen, clear panes
        if self.current_media_id == media_id:
            self.current_media_id = None
            self.transcript_panel.clear()
            self.segments_panel.clear()
            self.words_panel.clear()
            self.editor_panel.clear()
        
        # Delete the media
        self.library_ctrl.delete(media_id)
        
        # Update status
        self.statusBar().showMessage(f"Deleted: {file_name}", 3000)
    
    def _on_segment_clicked(self, segment_id: int):
        """Handle segment selection.
        
        Args:
            segment_id: Segment ID
        """
        # Get the segment
        segment = self.db.get_segment(segment_id)
        
        # Update word panel
        self.words_panel.set_words(segment_id, segment.words)
        
        # Seek to segment start
        self.media_pane.seek(segment.start_sec)
    
    def _on_segment_double_clicked(self, segment_id: int, speaker_id: str):
        """Handle segment rename request.
        
        Args:
            segment_id: Segment ID
            speaker_id: Speaker ID
        """
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Speaker", 
            f"New name for {speaker_id}:"
        )
        
        if not ok or not new_name.strip():
            return
            
        # Save the new speaker name to the database
        self.library_ctrl.rename_speaker(self.current_media_id, speaker_id, new_name.strip())
        
        # Reload the transcript to show the updated speaker names
        if self.current_media_id:
            self._on_media_selected(self.current_media_id)
    
    def _on_word_clicked(self, start_sec: float):
        """Handle word selection.
        
        Args:
            start_sec: Start time in seconds
        """
        self.media_pane.seek(start_sec)
    
    def _on_word_double_clicked(self, segment_id: int, word_id: int, word_text: str):
        """Handle word edit request.
        
        Args:
            segment_id: Segment ID
            word_id: Word ID
            word_text: Current word text
        """
        new_text, ok = QInputDialog.getText(
            self, 
            "Edit Word", 
            "Correct word:", 
            text=word_text
        )
        
        if not ok or new_text.strip() == word_text:
            return
            
        # Update DB with new text
        self.library_ctrl.update_word(segment_id, word_id, new_text.strip())
        
        # Reload transcript
        if self.current_media_id:
            self._on_media_selected(self.current_media_id)
    
    def _on_player_position_changed(self, position: float):
        """Handle player position change.
        
        Args:
            position: Position in seconds
        """
        if self.current_media_id:
            # Only update every few seconds to avoid excessive DB writes
            if int(position) % 5 == 0:  # Every 5 seconds
                self.db.update_media_last_pos(self.current_media_id, position)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change.
        
        Args:
            index: Tab index
        """
        # If Words tab is selected and no segment is selected, auto-select first row
        if index == 2 and self.words_panel.table.rowCount() == 0:
            if self.segments_panel.table.rowCount() > 0:
                self.segments_panel.table.selectRow(0)
                # Get segment_id from the first row
                seg_item = self.segments_panel.table.item(0, 0)
                if seg_item:
                    segment_id = seg_item.data(Qt.UserRole)
                    self._on_segment_clicked(segment_id)
    
    def _on_export_clip(self):
        """Handle export clip action."""
        if not self.current_media_id:
            QMessageBox.warning(
                self,
                "Export Error",
                "No media loaded or no edit mask available."
            )
            return
        
        # Open file dialog for destination
        file_dialog = QFileDialog()
        dest_path, _ = file_dialog.getSaveFileName(
            self,
            "Export Edited Clip",
            str(Path.home()),
            "MP4 Video (*.mp4);;All Files (*)"
        )
        
        if not dest_path:
            return
            
        # Add default extension if not provided
        dest_path = Path(dest_path)
        if not dest_path.suffix:
            dest_path = dest_path.with_suffix('.mp4')
            
        # Start export
        try:
            self.editor_ctrl.export_clip(self.current_media_id, dest_path)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported clip to {dest_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export: {str(e)}"
            )
    
    def _notify_done(self, fname: str):
        """Play a sound and show notification when job is complete.
        
        Args:
            fname: File name
        """
        # Play sound
        self.done_sound.play()
        
        # Show notification
        self.tray.showMessage(
            "EZ Clip – Job Finished",
            f"{fname} is ready!",
            QSystemTrayIcon.Information,
            5000
        )