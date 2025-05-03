# Architecture Overview

EasyVid is designed with a modular, layered architecture to promote separation of concerns, reusability, and future extensibility. This document provides an overview of the application's architecture and how its components interact.

## High-Level Architecture

The application is structured in three main layers:

1. **User Interface Layer** - The desktop GUI and user interaction components
2. **Core Processing Layer** - The transcription, diarization, and orchestration logic
3. **Data Management Layer** - The database and persistence components

```
┌────────────────────────────────────────────────────────┐
│                    User Interface                       │
│ ┌────────────────────────────────────────────────────┐ │
│ │               desktop_gui.py (PySide6)             │ │
│ └────────────────────────────────────────────────────┘ │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                  Core Processing                        │
│ ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│ │ pipeline.py│  │transcribe.py│  │    diarize.py     │ │
│ └────────────┘  └────────────┘  └────────────────────┘ │
│         │              │                  │            │
│         └──────────────┼──────────────────┘            │
│                        │                               │
│ ┌────────────────────────────────────────────────────┐ │
│ │                  model_cache.py                    │ │
│ └────────────────────────────────────────────────────┘ │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                  Data Management                        │
│ ┌────────────────────────┐  ┌─────────────────────────┐│
│ │      database.py       │  │      schema.sql         ││
│ └────────────────────────┘  └─────────────────────────┘│
└────────────────────────────────────────────────────────┘
```

## Directory Structure

The application follows a structured directory layout:

```
ez_clip_app/
├── ui/
│   ├── __init__.py
│   └── desktop_gui.py          # PySide6 main window
├── core/
│   ├── __init__.py
│   ├── pipeline.py             # orchestrates full job
│   ├── transcribe.py           # WhisperX wrapper
│   ├── diarize.py              # pyannote wrapper
│   └── model_cache.py          # singleton loaders
├── data/
│   ├── __init__.py
│   ├── database.py             # SQLite helpers
│   └── schema.sql              # CREATE TABLE statements
├── __init__.py
├── main.py                     # launches GUI
├── config.py                   # global constants / env vars
└── requirements.txt
```

## Component Details

### User Interface Layer

#### `ui/desktop_gui.py`

This module implements the desktop GUI using PySide6. Key components include:

- **MainWindow**: The primary UI container with file selection and transcription settings
- **TranscriptionWorker**: A QRunnable worker for running tasks in background threads
- **WorkerSignals**: Signal provider for worker thread communication

The UI design follows a vertical layout with:
1. Top section for file selection and transcription settings
2. Middle section for active jobs and progress bars
3. Bottom section with tabbed display of transcription results

### Core Processing Layer

#### `core/pipeline.py`

The central orchestration module that:
- Coordinates the entire transcription process
- Manages data flow between components
- Handles error cases and progress reporting

Key features:
- `process_file`: Main processing function that orchestrates the full pipeline
- `JobSettings`: Dataclass for configuring transcription jobs
- `PipelineError`: Custom exception for pipeline-specific errors

#### `core/transcribe.py`

Handles the audio transcription process using WhisperX:
- Audio extraction from video files
- Transcription with word-level timestamps
- Progress reporting

#### `core/diarize.py`

Manages the speaker diarization process:
- Identifies different speakers in the audio
- Assigns speaker labels to transcription segments
- Merges transcription with speaker information

#### `core/model_cache.py`

Provides singleton model loaders:
- Caches models to avoid repeated loading
- Handles device management (CPU/GPU)
- Manages model resources efficiently

### Data Management Layer

#### `data/database.py`

Implements SQLite database operations:
- Connection management
- CRUD operations for media files, transcripts, and segments
- Progress tracking
- Error handling

#### `data/schema.sql`

Defines the database schema:
- Media files table
- Transcripts table
- Segments table
- Speakers table

### Configuration

#### `config.py`

Centralizes application configuration:
- Default settings
- Environment variable loading
- Path management
- Constants for statuses and other values

### Main Entry Point

#### `main.py`

The application entry point:
- Sets up logging
- Processes command-line arguments
- Launches the GUI

## Data Flow

1. User selects a media file via the GUI
2. UI creates a job in the database with 'queued' status
3. UI spawns a background worker to process the file
4. Pipeline:
   - Updates status to 'running'
   - Extracts audio from the media file
   - Transcribes audio using WhisperX
   - Performs speaker diarization if enabled
   - Saves results to the database
   - Updates status to 'done' or 'error'
5. UI polls the database for progress updates
6. Upon completion, UI displays transcript and segments

## State Machine

The application follows a simple state machine for job processing:

```
  ┌─────────┐
  │ QUEUED  │
  └────┬────┘
       │ worker.start()
       ▼
  ┌─────────┐
  │ RUNNING │
  └────┬────┘
       │
       ├───────► success ───────► ┌──────┐
       │                          │ DONE │
       │                          └──────┘
       │
       └───► exception ───────► ┌───────┐
                                │ ERROR │
                                └───────┘
```

## Threading Model

The application uses a multi-threaded architecture:
- Main thread: UI responsiveness
- Worker threads: File processing

Thread communication happens via:
- Qt signals for progress and completion
- SQLite database for persistent state
- File system for media files and extracted audio

## Dependencies Management

External dependencies are managed through:
- `requirements.txt`: Explicit version requirements
- `model_cache.py`: Lazy loading of ML models
- `config.py`: Environment variables for configuration

## Future Extensibility

The architecture is designed to support future extensions:
- Clear separation between UI and core processing
- Modular design for component replacement
- Database schema supports advanced features
- Pipeline designed for reuse in other contexts (e.g., web service)