# API Reference

This document provides detailed information about the core APIs in EasyVid, focusing on the key functions, classes, and interfaces that developers might need when extending or integrating the application.

## Core Pipeline API

The pipeline module provides the main orchestration functionality.

### `pipeline.process_file`

```python
def process_file(
    media_path: Union[str, Path],
    settings: JobSettings,
    db: DB,
    progress_cb: Callable[[float], None] = None
) -> int
```

Process a media file through the transcription pipeline.

#### Parameters:
- `media_path`: Path to the media file (video or audio)
- `settings`: Job settings configuration
- `db`: Database instance
- `progress_cb`: Optional callback function for progress updates (0-100)

#### Returns:
- `int`: Transcript ID in the database

#### Raises:
- `PipelineError`: If processing fails

#### Example:

```python
from pathlib import Path
from ez_clip_app.core.pipeline import process_file, JobSettings
from ez_clip_app.data.database import DB

# Initialize database
db = DB()

# Configure job settings
settings = JobSettings(
    model_size="medium",
    language="en",
    diarize=True,
    min_speakers=2,
    max_speakers=4
)

# Process a file with progress reporting
def progress_callback(percent):
    print(f"Progress: {percent:.1f}%")

try:
    transcript_id = process_file(
        media_path=Path("/path/to/video.mp4"),
        settings=settings,
        db=db,
        progress_cb=progress_callback
    )
    print(f"Transcript ID: {transcript_id}")
except PipelineError as e:
    print(f"Processing failed: {e}")
```

### `JobSettings` Class

```python
@dataclasses.dataclass
class JobSettings:
    model_size: str = "medium"
    language: str = "en"
    diarize: bool = True
    min_speakers: int = 2
    max_speakers: int = 4
    hf_token: Optional[str] = None
```

Configuration settings for a transcription job.

#### Attributes:
- `model_size`: WhisperX model size ('tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2')
- `language`: Language code (e.g., 'en', 'es', 'fr') or 'auto' for auto-detection
- `diarize`: Whether to perform speaker diarization
- `min_speakers`: Minimum number of speakers to detect
- `max_speakers`: Maximum number of speakers to detect
- `hf_token`: Optional Hugging Face token for diarization models

## Transcription API

The transcription module provides audio extraction and transcription functionality.

### `transcribe.extract_audio`

```python
def extract_audio(media_path: Union[str, Path]) -> Path
```

Extract audio from a media file using FFmpeg.

#### Parameters:
- `media_path`: Path to the media file

#### Returns:
- `Path`: Path to the extracted audio file (WAV)

#### Raises:
- `ffmpeg.Error`: If audio extraction fails

### `transcribe.transcribe`

```python
def transcribe(
    audio_path: Union[str, Path],
    model_size: str = DEFAULT_MODEL_SIZE,
    language: str = DEFAULT_LANGUAGE,
    batch_size: int = 16,
    progress_callback: Callable[[float], None] = None
) -> TranscriptionResult
```

Transcribe an audio file using WhisperX.

#### Parameters:
- `audio_path`: Path to the audio file
- `model_size`: WhisperX model size
- `language`: Language code or 'auto'
- `batch_size`: Batch size for processing
- `progress_callback`: Optional callback for progress updates

#### Returns:
- `TranscriptionResult`: Object containing segments and full text

#### Example:

```python
from ez_clip_app.core.transcribe import extract_audio, transcribe

# Extract audio from video
audio_path = extract_audio("/path/to/video.mp4")

# Transcribe the audio
result = transcribe(
    audio_path,
    model_size="medium",
    language="en",
    progress_callback=lambda p: print(f"Transcription progress: {p}%")
)

print(f"Full text: {result.full_text}")
print(f"Duration: {result.duration} seconds")
print(f"Number of segments: {len(result.segments)}")
```

### `TranscriptionResult` Class

```python
class TranscriptionResult:
    def __init__(self, segments, full_text, duration):
        self.segments = segments
        self.full_text = full_text
        self.duration = duration
```

Container for transcription results.

#### Attributes:
- `segments`: List of transcription segments with timestamps
- `full_text`: Complete transcript text
- `duration`: Audio duration in seconds

## Diarization API

The diarization module provides speaker identification functionality.

### `diarize.diarize`

```python
def diarize(
    audio_path: Union[str, Path],
    transcription_segments: List[dict],
    min_speakers: int = DEFAULT_MIN_SPEAKERS,
    max_speakers: int = DEFAULT_MAX_SPEAKERS,
    progress_callback: Callable[[float], None] = None
) -> List[dict]
```

Perform speaker diarization on transcribed segments.

#### Parameters:
- `audio_path`: Path to the audio file
- `transcription_segments`: List of transcription segments from WhisperX
- `min_speakers`: Minimum number of speakers to detect
- `max_speakers`: Maximum number of speakers to detect
- `progress_callback`: Optional callback for progress updates

#### Returns:
- `List[dict]`: Updated list of segments with speaker labels

### `diarize.merge_into_single_speaker`

```python
def merge_into_single_speaker(transcription_segments: List[dict]) -> List[dict]
```

Merge all segments without diarization (single speaker).

#### Parameters:
- `transcription_segments`: List of transcription segments from WhisperX

#### Returns:
- `List[dict]`: Updated list of segments with default speaker label

#### Example:

```python
from ez_clip_app.core.diarize import diarize, merge_into_single_speaker

# With diarization
diarized_segments = diarize(
    audio_path="/path/to/audio.wav",
    transcription_segments=transcription_result.segments,
    min_speakers=2,
    max_speakers=4
)

# Without diarization
single_speaker_segments = merge_into_single_speaker(transcription_result.segments)
```

## Model Cache API

The model cache module provides singleton model loaders.

### `model_cache.get_whisper`

```python
def get_whisper(model_size=DEFAULT_MODEL_SIZE)
```

Get or load WhisperX model.

#### Parameters:
- `model_size`: Model size ('tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2')

#### Returns:
- Loaded WhisperX model

### `model_cache.get_diarization_model`

```python
def get_diarization_model()
```

Get or load PyAnnote diarization model.

#### Returns:
- Loaded diarization pipeline

### `model_cache.get_alignment_model`

```python
def get_alignment_model()
```

Get or load WhisperX alignment model.

#### Returns:
- Tuple of (model, metadata)

## Database API

The database module provides SQLite database operations.

### `DB` Class

```python
class DB:
    def __init__(self, db_path: Union[str, Path] = DB_PATH):
        ...
```

Database interface for the WhisperX app.

#### Key Methods:

#### `insert_media`

```python
def insert_media(self, path: Union[str, Path]) -> int
```

Insert a new media file or get existing ID.

#### Parameters:
- `path`: Path to the media file

#### Returns:
- `int`: Media file ID

#### `set_status`

```python
def set_status(self, media_id: int, status: str)
```

Update the status of a media file.

#### Parameters:
- `media_id`: Media file ID
- `status`: New status (queued, running, done, error)

#### `update_progress`

```python
def update_progress(self, media_id: int, progress: float)
```

Update the progress of a media file.

#### Parameters:
- `media_id`: Media file ID
- `progress`: Progress percentage (0-100)

#### `set_error`

```python
def set_error(self, media_id: int, error_msg: str)
```

Set error message and update status.

#### Parameters:
- `media_id`: Media file ID
- `error_msg`: Error message

#### `save_transcript`

```python
def save_transcript(self, media_id: int, full_text: str, duration: float, segments: List[dict]) -> int
```

Save transcript and segments.

#### Parameters:
- `media_id`: Media file ID
- `full_text`: Complete transcript text
- `duration`: Audio duration in seconds
- `segments`: List of segment dictionaries

#### Returns:
- `int`: Transcript ID

#### `get_active_jobs`

```python
def get_active_jobs(self) -> List[sqlite3.Row]
```

Get all active jobs for progress tracking.

#### Returns:
- `List[sqlite3.Row]`: List of row objects with id, filepath, status, progress

#### `get_transcript`

```python
def get_transcript(self, media_id: int) -> Dict
```

Get complete transcript with segments for a media file.

#### Parameters:
- `media_id`: Media file ID

#### Returns:
- `Dict`: Dictionary with transcript and segments

#### Example:

```python
from ez_clip_app.data.database import DB

# Initialize database
db = DB()

# Insert a new media file
media_id = db.insert_media("/path/to/video.mp4")

# Update status and progress
db.set_status(media_id, "running")
db.update_progress(media_id, 50.0)

# Retrieve active jobs
active_jobs = db.get_active_jobs()
for job in active_jobs:
    print(f"Job {job['id']}: {job['status']} ({job['progress']}%)")

# Get transcript
transcript_data = db.get_transcript(media_id)
if transcript_data:
    print(f"Transcript: {transcript_data['transcript']['full_text'][:100]}...")
    print(f"Segments: {len(transcript_data['segments'])}")
```

## GUI API

The GUI module provides the desktop user interface.

### `MainWindow` Class

```python
class MainWindow(QMainWindow):
    def __init__(self):
        ...
```

Main application window.

Key methods relevant for extension:

#### `on_select_file`

```python
def on_select_file(self)
```

Open file dialog and start processing selected file.

#### `update_progress`

```python
def update_progress(self, job_id, progress)
```

Update progress bar for a specific job.

#### `poll_progress`

```python
def poll_progress(self)
```

Poll database for progress updates on active jobs.

#### `display_transcript`

```python
def display_transcript(self, job_id)
```

Display transcript and segments for completed job.

## Configuration API

The config module provides application-wide configuration.

### Key Constants:

- `APP_DIR`: Application directory
- `DATA_DIR`: Data directory (`~/.ez_clip_app`)
- `DB_PATH`: Database path
- `DEFAULT_MODEL_SIZE`: Default WhisperX model size
- `DEFAULT_LANGUAGE`: Default language code
- `DEVICE`: Computation device ('cuda' or 'cpu')
- `DEFAULT_MIN_SPEAKERS`: Default minimum speakers
- `DEFAULT_MAX_SPEAKERS`: Default maximum speakers
- `HF_TOKEN`: HuggingFace token from environment
- `MAX_WORKERS`: Maximum worker threads
- `POLL_INTERVAL_MS`: UI polling interval
- `Status`: Class with status constants