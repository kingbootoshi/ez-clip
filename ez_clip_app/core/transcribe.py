"""
WhisperX wrapper for transcription with word-level timestamps.
"""
import logging
import typing as t
from pathlib import Path
import ffmpeg
import tempfile
import whisperx

from ez_clip_app.core import model_cache
from ez_clip_app.config import DEFAULT_MODEL_SIZE, DEFAULT_LANGUAGE, DEVICE

# Set up logging
logger = logging.getLogger(__name__)

class TranscriptionResult:
    """Container for transcription results."""
    
    def __init__(self, segments, full_text, duration):
        self.segments = segments
        self.full_text = full_text
        self.duration = duration


def extract_audio(media_path: t.Union[str, Path]) -> Path:
    """Extract audio from media file using ffmpeg.
    
    Args:
        media_path: Path to media file
        
    Returns:
        Path to extracted audio file (WAV)
    """
    media_path = Path(media_path)
    # Create temporary file with .wav extension
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()
    
    try:
        logger.info(f"Extracting audio from {media_path}")
        
        # Use ffmpeg to extract audio
        (
            ffmpeg
            .input(str(media_path))
            .output(str(temp_path), acodec='pcm_s16le', ar='16000', ac=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        logger.info(f"Audio extracted to {temp_path}")
        return temp_path
    
    except ffmpeg.Error as e:
        logger.error(f"Error extracting audio: {e.stderr.decode()}")
        if temp_path.exists():
            temp_path.unlink()
        raise


def transcribe(
    audio_path: t.Union[str, Path],
    model_size: str = DEFAULT_MODEL_SIZE,
    language: str = DEFAULT_LANGUAGE,
    batch_size: int = 16,
    progress_callback: t.Callable[[float], None] = None
) -> TranscriptionResult:
    """Transcribe audio file using WhisperX.
    
    Args:
        audio_path: Path to audio file
        model_size: WhisperX model size
        language: Language code (or 'auto' for auto-detection)
        batch_size: Batch size for processing
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        TranscriptionResult with segments and full text
    """
    audio_path = Path(audio_path)
    logger.info(f"Transcribing {audio_path} with {model_size} model")
    
    try:
        # Load WhisperX model
        model = model_cache.get_whisper(model_size)
        
        # Initial progress update
        if progress_callback:
            progress_callback(5)
        
        # Transcribe audio
        result = model.transcribe(
            str(audio_path),
            language=language,
            batch_size=batch_size
        )
        
        # Progress update after initial transcription
        if progress_callback:
            progress_callback(30)
        
        # Get word-level alignments
        alignment_model, metadata = model_cache.get_alignment_model()
        result = whisperx.align(
            result["segments"],
            alignment_model,
            metadata,
            str(audio_path),
            DEVICE
        )
        
        # Progress update after alignment
        if progress_callback:
            progress_callback(60)
        
        # Extract duration from result or compute it
        duration = result.get("duration", 0)
        
        # Combine all text
        full_text = " ".join(segment["text"] for segment in result["segments"])
        
        logger.info(f"Transcription completed: {len(result['segments'])} segments")
        
        return TranscriptionResult(
            segments=result["segments"],
            full_text=full_text,
            duration=duration
        )
    
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise