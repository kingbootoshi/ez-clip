"""
Global configuration settings for the WhisperX transcription app.
"""
import os
import pathlib
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Paths
APP_DIR = pathlib.Path(__file__).parent.absolute()
DATA_DIR = pathlib.Path.home() / ".ez_clip_app"
DB_PATH = DATA_DIR / "transcripts.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# WhisperX model configuration
DEFAULT_MODEL_SIZE = "medium"  # tiny, base, small, medium, large-v1, large-v2
DEFAULT_LANGUAGE = "en"        # ISO language code, "auto" for auto-detection
DEVICE = "cuda" if os.environ.get("USE_GPU", "").lower() == "true" else "cpu"

# Diarization configuration
DEFAULT_MIN_SPEAKERS = 2
DEFAULT_MAX_SPEAKERS = 4

# HuggingFace token for pyannote.audio
HF_TOKEN = os.environ.get("HF_TOKEN")

# Threading configuration
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))

# UI configuration
POLL_INTERVAL_MS = 500  # How often to update progress in UI

# Status values for database
class Status:
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"