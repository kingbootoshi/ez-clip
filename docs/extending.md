# Extending the Application

This guide provides information on how to extend EasyVid for various use cases. The application was designed with modularity in mind, making it straightforward to add new features, modify existing ones, or integrate with other systems.

## Table of Contents

1. [Adding Alternative Transcription Engines](#adding-alternative-transcription-engines)
2. [Supporting Additional Languages](#supporting-additional-languages)
3. [Creating a Web UI](#creating-a-web-ui)
4. [Adding Export Formats](#adding-export-formats)
5. [Extending the Database Schema](#extending-the-database-schema)
6. [Adding Custom Post-Processing](#adding-custom-post-processing)
7. [Batch Processing](#batch-processing)
8. [Integration with Video Editors](#integration-with-video-editors)
9. [Cloud Deployment](#cloud-deployment)

## Adding Alternative Transcription Engines

EZ Clip currently uses WhisperX for transcription, but you can extend it to support other engines:

1. Create a new module in the `core` directory (e.g., `core/transcribe_faster_whisper.py`)
2. Implement a compatible transcription function:

```python
def transcribe_faster_whisper(
    audio_path: Path,
    model_size: str = "medium",
    language: str = "en",
    progress_callback: Callable = None
) -> TranscriptionResult:
    """Transcribe audio using Faster Whisper."""
    from faster_whisper import WhisperModel
    
    # Load model
    model = WhisperModel(model_size, device="cuda" if torch.cuda.is_available() else "cpu")
    
    # Transcribe
    segments, info = model.transcribe(
        str(audio_path),
        language=language
    )
    
    # Convert to our format
    result_segments = []
    full_text = ""
    
    for segment in segments:
        result_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": [{"w": word.word, "s": word.start, "e": word.end} for word in segment.words]
        })
        full_text += segment.text + " "
    
    return transcribe.TranscriptionResult(
        segments=result_segments,
        full_text=full_text.strip(),
        duration=info.duration
    )
```

3. Update the `model_cache.py` to support the new engine:

```python
def get_faster_whisper(model_size="medium"):
    """Get or load Faster Whisper model."""
    if f"faster_whisper_{model_size}" not in _WHISPER_MODELS:
        from faster_whisper import WhisperModel
        _WHISPER_MODELS[f"faster_whisper_{model_size}"] = WhisperModel(
            model_size, 
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
    return _WHISPER_MODELS[f"faster_whisper_{model_size}"]
```

4. Modify the UI to let users select the transcription engine:

```python
# Add to desktop_gui.py's init_ui method
self.engine_combo = QComboBox()
self.engine_combo.addItems(["WhisperX", "faster_whisper"])
settings_layout.addRow("Transcription Engine:", self.engine_combo)
```

5. Update the pipeline to use the selected engine:

```python
# In pipeline.py, modify process_file
engine = settings.engine  # Add this to JobSettings

if engine == "WhisperX":
    transcription = transcribe.transcribe(audio_path, ...)
elif engine == "faster_whisper":
    from .transcribe_faster_whisper import transcribe_faster_whisper
    transcription = transcribe_faster_whisper(audio_path, ...)
else:
    raise PipelineError(f"Unknown transcription engine: {engine}")
```

## Supporting Additional Languages

To add support for additional languages:

1. Update the language dropdown in `desktop_gui.py`:

```python
# Expanded language list
self.language_combo.addItems([
    "en", "auto", "es", "fr", "de", "it", "pt", "nl", "ja", "zh",
    "ar", "hi", "ru", "ko", "tr", "pl", "vi", "th", "uk", "cs"
])
```

2. Add language-specific alignment models in `model_cache.py`:

```python
def get_alignment_model(language_code="en"):
    """Get or load WhisperX alignment model."""
    if f"align_{language_code}" not in _DIARIZATION_MODELS:
        try:
            import WhisperX
            
            logger.info(f"Loading alignment model for {language_code}...")
            model_a, metadata = WhisperX.load_align_model(
                language_code=language_code,
                device=DEVICE
            )
            _DIARIZATION_MODELS[f"align_{language_code}"] = (model_a, metadata)
            logger.info(f"Alignment model for {language_code} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading alignment model for {language_code}: {e}")
            raise
    
    return _DIARIZATION_MODELS[f"align_{language_code}"]
```

3. Update the transcribe function to use the language-specific alignment:

```python
# In transcribe.py
alignment_model, metadata = model_cache.get_alignment_model(language)
```

## Creating a Web UI

To create a web UI for EasyVid, leveraging the existing core modules:

1. Create a new directory for the web interface:

```bash
mkdir -p ez_clip_app/web
touch ez_clip_app/web/__init__.py
```

2. Implement a Flask application (`ez_clip_app/web/app.py`):

```python
from flask import Flask, render_template, request, jsonify
import threading
from pathlib import Path
import tempfile
import os
import uuid

from ..core.pipeline import process_file, JobSettings, PipelineError
from ..data.database import DB
from ..config import Status

app = Flask(__name__)
db = DB()

# Temporary storage for uploaded files
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "WhisperX_uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Track jobs and progress
active_jobs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Save the uploaded file
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_FOLDER / f"{file_id}_{file.filename}"
    file.save(file_path)
    
    # Get settings from form
    settings = JobSettings(
        model_size=request.form.get('model_size', 'medium'),
        language=request.form.get('language', 'en'),
        diarize=request.form.get('diarize', 'true').lower() == 'true',
        min_speakers=int(request.form.get('min_speakers', 2)),
        max_speakers=int(request.form.get('max_speakers', 4))
    )
    
    # Add job to database
    job_id = db.insert_media(file_path)
    
    # Start processing in background thread
    def process_job():
        try:
            def progress_cb(progress):
                db.update_progress(job_id, progress)
                active_jobs[job_id] = progress
            
            process_file(file_path, settings, db, progress_cb)
        except Exception as e:
            db.set_error(job_id, str(e))
    
    thread = threading.Thread(target=process_job)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'message': 'File uploaded and processing started'
    })

@app.route('/progress/<int:job_id>')
def get_progress(job_id):
    job = db.get_job_status(job_id)  # New method needed in DB class
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'progress': job['progress'],
        'error': job.get('error_msg')
    })

@app.route('/transcript/<int:job_id>')
def get_transcript(job_id):
    result = db.get_transcript(job_id)
    if not result:
        return jsonify({'error': 'Transcript not found'}), 404
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
```

3. Create templates directory and HTML templates:

```bash
mkdir -p ez_clip_app/web/templates
mkdir -p ez_clip_app/web/static
```

4. Implement front-end templates with HTML, CSS, and JavaScript

5. Create a new entry point `ez_clip_app/web_main.py`:

```python
#!/usr/bin/env python3
"""
Web server entry point for the WhisperX transcription app.
"""
import sys
import logging
import argparse
from pathlib import Path

from web.app import app

# Configure logging
def setup_logging(verbose=False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path.home() / '.WhisperX_web.log')
        ]
    )

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='WhisperX web server')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('-h', '--host', default='127.0.0.1', help='Host to run the server on')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting WhisperX web server")
    
    app.run(host=args.host, port=args.port)

if __name__ == '__main__':
    main()
```

6. Add necessary methods to the `DB` class for web interface

## Adding Export Formats

To add export functionality for different formats:

1. Create a new directory for exporters:

```bash
mkdir -p ez_clip_app/exporters
touch ez_clip_app/exporters/__init__.py
```

2. Implement different export formats:

```python
# ez_clip_app/exporters/srt.py
def export_to_srt(segments, output_path):
    """Export segments to SRT format."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start = format_timestamp(segment['start_sec'])
            end = format_timestamp(segment['end_sec'])
            
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment['text']}\n\n")

def format_timestamp(seconds):
    """Format seconds to SRT timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
```

```python
# ez_clip_app/exporters/vtt.py
def export_to_vtt(segments, output_path):
    """Export segments to WebVTT format."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        
        for i, segment in enumerate(segments, 1):
            start = format_timestamp(segment['start_sec'])
            end = format_timestamp(segment['end_sec'])
            
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment['text']}\n\n")

def format_timestamp(seconds):
    """Format seconds to WebVTT timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
```

```python
# ez_clip_app/exporters/txt.py
def export_to_txt(transcript, output_path):
    """Export full transcript to text file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(transcript)
```

```python
# ez_clip_app/exporters/json.py
import json

def export_to_json(transcript_data, output_path):
    """Export transcript data to JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
```

3. Update the UI to support exports:

```python
# Add export buttons to desktop_gui.py
export_group = QGroupBox("Export")
export_layout = QHBoxLayout(export_group)

export_srt_btn = QPushButton("Export SRT")
export_srt_btn.clicked.connect(self.export_srt)
export_layout.addWidget(export_srt_btn)

export_vtt_btn = QPushButton("Export VTT")
export_vtt_btn.clicked.connect(self.export_vtt)
export_layout.addWidget(export_vtt_btn)

export_txt_btn = QPushButton("Export TXT")
export_txt_btn.clicked.connect(self.export_txt)
export_layout.addWidget(export_txt_btn)

export_json_btn = QPushButton("Export JSON")
export_json_btn.clicked.connect(self.export_json)
export_layout.addWidget(export_json_btn)

main_layout.addWidget(export_group)

# Add export methods
def export_srt(self):
    if not hasattr(self, "current_transcript_id"):
        QMessageBox.warning(self, "Export Error", "No transcript to export")
        return
    
    file_path, _ = QFileDialog.getSaveFileName(
        self, "Export SRT", "", "SubRip (*.srt)"
    )
    
    if file_path:
        from ez_clip_app.exporters.srt import export_to_srt
        result = self.db.get_transcript(self.current_transcript_id)
        export_to_srt(result["segments"], file_path)
        QMessageBox.information(self, "Export Complete", f"Exported to {file_path}")
```

## Extending the Database Schema

To extend the database schema:

1. Create a migration file in `ez_clip_app/data/migrations/`:

```sql
-- Add custom metadata table
CREATE TABLE IF NOT EXISTS transcript_metadata (
    transcript_id INTEGER PRIMARY KEY REFERENCES transcripts(id) ON DELETE CASCADE,
    title TEXT,
    description TEXT,
    tags TEXT,
    language_confidence REAL,
    custom_data TEXT
);

-- Add text search index
CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts USING fts5(
    transcript_id,
    text,
    content='transcripts',
    content_rowid='id'
);

-- Add triggers to keep the FTS index updated
CREATE TRIGGER IF NOT EXISTS transcripts_ai AFTER INSERT ON transcripts BEGIN
  INSERT INTO transcript_fts(transcript_id, text) VALUES (new.id, new.full_text);
END;

CREATE TRIGGER IF NOT EXISTS transcripts_ad AFTER DELETE ON transcripts BEGIN
  INSERT INTO transcript_fts(transcript_fts, rowid, transcript_id, text) VALUES('delete', old.id, old.id, old.full_text);
END;

CREATE TRIGGER IF NOT EXISTS transcripts_au AFTER UPDATE ON transcripts BEGIN
  INSERT INTO transcript_fts(transcript_fts, rowid, transcript_id, text) VALUES('delete', old.id, old.id, old.full_text);
  INSERT INTO transcript_fts(rowid, transcript_id, text) VALUES (new.id, new.id, new.full_text);
END;
```

2. Add migration logic to the DB class:

```python
def _check_and_migrate_schema(self):
    """Check current schema version and migrate if needed."""
    with self._get_connection() as conn:
        # Get current version
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        
        # Target version from code
        target_version = 2  # Increment this when adding migrations
        
        if version < target_version:
            # Run migrations
            for v in range(version + 1, target_version + 1):
                migration_file = Path(__file__).parent / f"migrations/v{v}.sql"
                if migration_file.exists():
                    with open(migration_file, "r") as f:
                        conn.executescript(f.read())
                    print(f"Applied migration to version {v}")
            
            # Update version
            conn.execute(f"PRAGMA user_version = {target_version}")
```

3. Update the `__init__` method to call the migration function:

```python
def __init__(self, db_path=DB_PATH):
    self.db_path = Path(db_path)
    self._ensure_tables()
    self._check_and_migrate_schema()
```

## Adding Custom Post-Processing

To add custom post-processing of transcripts:

1. Create a new module for post-processing:

```python
# ez_clip_app/core/post_process.py
import re

def clean_transcript(text):
    """Clean transcript by removing hesitations, etc."""
    # Remove hesitations and filler words
    text = re.sub(r'\b(um|uh|er|ah|like|you know|I mean)\b', '', text)
    
    # Fix capitalization
    text = '. '.join(s.strip().capitalize() for s in text.split('.'))
    
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

def add_punctuation(text):
    """Add missing punctuation using NLP."""
    # This would require an NLP library like spaCy
    # Simplified example:
    if not text.endswith(('.', '?', '!')):
        text += '.'
    
    return text

def format_numbers(text):
    """Format numbers consistently."""
    # Convert digits to words for small numbers
    def replace_number(match):
        num = int(match.group(0))
        if 0 <= num <= 10:
            words = ['zero', 'one', 'two', 'three', 'four', 'five', 
                     'six', 'seven', 'eight', 'nine', 'ten']
            return words[num]
        return match.group(0)
    
    return re.sub(r'\b\d+\b', replace_number, text)
```

2. Update the pipeline to use these functions:

```python
# In pipeline.py
from .post_process import clean_transcript, add_punctuation, format_numbers

# After transcription, add:
if settings.clean_transcript:
    transcription.full_text = clean_transcript(transcription.full_text)
    
    for segment in transcription.segments:
        segment['text'] = clean_transcript(segment['text'])

if settings.add_punctuation:
    transcription.full_text = add_punctuation(transcription.full_text)
    
    for segment in transcription.segments:
        segment['text'] = add_punctuation(segment['text'])
```

3. Update JobSettings to include post-processing options:

```python
@dataclasses.dataclass
class JobSettings:
    model_size: str = "medium"
    language: str = "en"
    diarize: bool = True
    min_speakers: int = 2
    max_speakers: int = 4
    hf_token: Optional[str] = None
    clean_transcript: bool = False
    add_punctuation: bool = False
    format_numbers: bool = False
```

## Batch Processing

To add batch processing capabilities:

1. Create a new module for batch processing:

```python
# ez_clip_app/core/batch.py
import os
import threading
import queue
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable

from .pipeline import process_file, JobSettings, PipelineError
from ..data.database import DB
from ..config import MAX_WORKERS

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Process multiple files with configurable concurrency."""
    
    def __init__(self, max_workers=MAX_WORKERS):
        self.max_workers = max_workers
        self.queue = queue.Queue()
        self.db = DB()
        self.running = False
        self.progress_callbacks = {}
    
    def add_file(self, file_path: Path, settings: JobSettings, 
                progress_callback: Callable[[int, float], None] = None):
        """Add a file to the processing queue."""
        job_id = self.db.insert_media(file_path)
        
        if progress_callback:
            self.progress_callbacks[job_id] = progress_callback
            
        self.queue.put((job_id, file_path, settings))
        return job_id
        
    def add_files(self, directory: Path, settings: JobSettings, 
                 extensions=None, recursive=False):
        """Add all files in a directory to the queue."""
        if extensions is None:
            extensions = ['.mp4', '.mp3', '.wav', '.avi', '.mkv', '.m4a']
            
        added_jobs = []
        
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in extensions:
                        job_id = self.add_file(file_path, settings)
                        added_jobs.append(job_id)
        else:
            for ext in extensions:
                for file_path in directory.glob(f"*{ext}"):
                    job_id = self.add_file(file_path, settings)
                    added_jobs.append(job_id)
                    
        return added_jobs
    
    def start(self, block=False):
        """Start processing the queue."""
        if self.running:
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        if block:
            self.worker_thread.join()
    
    def stop(self):
        """Stop processing the queue."""
        self.running = False
        
    def _process_queue(self):
        """Process files from the queue using ThreadPoolExecutor."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while self.running:
                try:
                    # Get file from queue with timeout
                    job_id, file_path, settings = self.queue.get(timeout=1)
                    
                    # Process the file
                    def task_wrapper():
                        try:
                            def progress_cb(progress):
                                # Update progress in DB
                                self.db.update_progress(job_id, progress)
                                
                                # Call user callback if provided
                                if job_id in self.progress_callbacks:
                                    self.progress_callbacks[job_id](job_id, progress)
                                    
                            process_file(file_path, settings, self.db, progress_cb)
                        except Exception as e:
                            logger.error(f"Error processing {file_path}: {e}")
                        finally:
                            self.queue.task_done()
                            
                    # Submit task to thread pool
                    executor.submit(task_wrapper)
                    
                except queue.Empty:
                    # No more files in queue
                    if self.queue.empty():
                        # Sleep a bit to prevent CPU spinning
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Error in batch processor: {e}")
```

2. Update the UI to support batch processing:

```python
# Add batch processing UI elements
batch_button = QPushButton("Batch Process Folder")
batch_button.clicked.connect(self.on_batch_process)
top_layout.addWidget(batch_button)

# Add batch processing method
def on_batch_process(self):
    folder_path = QFileDialog.getExistingDirectory(
        self, "Select Folder with Media Files", str(Path.home())
    )
    
    if not folder_path:
        return
        
    # Get settings
    settings = JobSettings(
        model_size=self.model_combo.currentText(),
        language=self.language_combo.currentText(),
        diarize=self.diarize_checkbox.isChecked(),
        min_speakers=self.min_speakers_spin.value(),
        max_speakers=self.max_speakers_spin.value(),
        hf_token=HF_TOKEN
    )
    
    # Create batch dialog
    dialog = BatchDialog(folder_path, settings, self)
    dialog.exec()
```

3. Create a batch dialog class:

```python
class BatchDialog(QDialog):
    def __init__(self, folder_path, settings, parent=None):
        super().__init__(parent)
        self.folder_path = Path(folder_path)
        self.settings = settings
        self.db = DB()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Batch Processing")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)
        
        self.recursive_check = QCheckBox()
        options_layout.addRow("Include Subfolders:", self.recursive_check)
        
        self.extensions_edit = QLineEdit(".mp4,.mp3,.wav,.avi,.mkv")
        options_layout.addRow("File Extensions:", self.extensions_edit)
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 16)
        self.max_workers_spin.setValue(MAX_WORKERS)
        options_layout.addRow("Concurrent Jobs:", self.max_workers_spin)
        
        layout.addWidget(options_group)
        
        # Progress
        self.progress_list = QListWidget()
        layout.addWidget(self.progress_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_batch)
        button_layout.addWidget(self.start_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def start_batch(self):
        extensions = [ext.strip() for ext in self.extensions_edit.text().split(",")]
        recursive = self.recursive_check.isChecked()
        max_workers = self.max_workers_spin.value()
        
        # Setup batch processor
        self.processor = BatchProcessor(max_workers=max_workers)
        
        # Add progress callback
        def progress_callback(job_id, progress):
            file_path = self.db.get_media_path(job_id)
            if file_path:
                file_name = Path(file_path).name
                self.update_progress_item(job_id, file_name, progress)
        
        # Add all files
        job_ids = self.processor.add_files(
            self.folder_path, 
            self.settings,
            extensions=extensions,
            recursive=recursive
        )
        
        # Create progress items
        for job_id in job_ids:
            file_path = self.db.get_media_path(job_id)
            if file_path:
                file_name = Path(file_path).name
                self.add_progress_item(job_id, file_name)
                # Register callback
                self.processor.progress_callbacks[job_id] = progress_callback
        
        # Start processing
        self.processor.start()
        
        # Disable start button
        self.start_button.setEnabled(False)
    
    def add_progress_item(self, job_id, file_name):
        item = QListWidgetItem(f"{file_name}: 0%")
        item.setData(Qt.UserRole, job_id)
        self.progress_list.addItem(item)
    
    def update_progress_item(self, job_id, file_name, progress):
        for i in range(self.progress_list.count()):
            item = self.progress_list.item(i)
            if item.data(Qt.UserRole) == job_id:
                item.setText(f"{file_name}: {progress:.1f}%")
                break
```

## Integration with Video Editors

To integrate with video editing software:

1. Create exporters for popular video editing formats:

```python
# ez_clip_app/exporters/premiere.py
def export_to_premiere(segments, output_path):
    """Export segments to Adobe Premiere Pro marker format (CSV)."""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write("Marker Name,Description,In,Out,Duration,Time\n")
        
        for i, segment in enumerate(segments):
            name = f"Speaker {segment['speaker']}"
            description = segment['text']
            in_point = format_premiere_time(segment['start_sec'])
            out_point = format_premiere_time(segment['end_sec'])
            duration = format_premiere_time(segment['end_sec'] - segment['start_sec'])
            
            f.write(f'"{name}","{description}",{in_point},{out_point},{duration},{in_point}\n')

def format_premiere_time(seconds):
    """Format seconds to Premiere Pro time format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds - int(seconds)) * 30)  # Assuming 30fps
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
```

```python
# ez_clip_app/exporters/fcpxml.py
def export_to_fcpxml(segments, output_path, fps=30):
    """Export segments to Final Cut Pro XML format."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
    <resources>
        <format id="r1" name="FFVideoFormat1080p30" frameDuration="1/30s"/>
    </resources>
    <library>
        <event name="Transcription">
            <project name="Transcribed Markers">
                <sequence format="r1">
                    <spine>
"""
    
    for segment in segments:
        start_frames = int(segment['start_sec'] * fps)
        end_frames = int(segment['end_sec'] * fps)
        duration_frames = end_frames - start_frames
        
        xml += f"""                        <marker start="{start_frames}/{fps}s" duration="{duration_frames}/{fps}s" 
                                value="{segment['speaker']}: {segment['text']}"/>
"""
    
    xml += """                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml)
```

2. Add these options to the export menu in the UI

## Cloud Deployment

For cloud deployment, you can adapt the application as follows:

1. Create a container configuration (`Dockerfile`):

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r ez_clip_app/requirements.txt

# Expose port for web interface
EXPOSE 5000

# Set environment variables
ENV PYTHONPATH=/app
ENV HF_HOME=/app/models

# Entry point
CMD ["python", "-m", "ez_clip_app.web_main", "--host", "0.0.0.0"]
```

2. Create a docker-compose file for easier deployment:

```yaml
version: '3'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - HF_TOKEN=${HF_TOKEN}
      - USE_GPU=false
      - MAX_WORKERS=4
    restart: unless-stopped
  
  # Optional GPU support
  app-gpu:
    build: .
    ports:
      - "5001:5000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - HF_TOKEN=${HF_TOKEN}
      - USE_GPU=true
      - MAX_WORKERS=2
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

3. Configure database for cloud storage:

```python
# In config.py, add support for external database URL
import os

# Database configuration
DB_URL = os.environ.get('DATABASE_URL', f'sqlite:///{Path.home()}/.ez_clip_app.db')

# In database.py, update to support different database types
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def get_engine(db_url=DB_URL):
    """Get SQLAlchemy engine based on database URL."""
    return create_engine(db_url)
```

4. Implement horizontal scaling and job queue using Redis:

```python
# In web/app.py
import redis
from rq import Queue

# Configure Redis connection
redis_conn = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD', '')
)

# Create RQ queue
job_queue = Queue(connection=redis_conn)

@app.route('/upload', methods=['POST'])
def upload_file():
    # ...existing code...
    
    # Enqueue job instead of processing in thread
    job = job_queue.enqueue(
        'ez_clip_app.core.worker.process_job',
        job_id,
        str(file_path),
        settings.__dict__
    )
    
    return jsonify({
        'job_id': job_id,
        'queue_job_id': job.id,
        'message': 'File uploaded and queued for processing'
    })
```

5. Create a worker module:

```python
# ez_clip_app/core/worker.py
from pathlib import Path
from ..data.database import DB
from .pipeline import process_file, JobSettings

def process_job(job_id, file_path, settings_dict):
    """Worker function for processing jobs from the queue."""
    db = DB()
    
    # Convert settings_dict back to JobSettings
    settings = JobSettings(**settings_dict)
    
    # Define progress callback
    def progress_cb(progress):
        db.update_progress(job_id, progress)
    
    # Process the file
    return process_file(
        Path(file_path), 
        settings, 
        db, 
        progress_cb
    )
```

6. Start worker processes:

```bash
# In your worker startup script
rq worker --url redis://redis:6379/0 WhisperX
```

With these extensions, you can adapt EasyVid to a wide variety of use cases and deployment scenarios while maintaining the core functionality.