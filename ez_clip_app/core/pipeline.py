"""
Pipeline orchestration for the WhisperX transcription app.
"""
import logging
import os
import tempfile
import dataclasses
import typing as t
from pathlib import Path

from ez_clip_app.config import Status
from ez_clip_app.data.database import DB
from ez_clip_app.core import transcribe
from ez_clip_app.core import diarize
from ez_clip_app.core.formatting import segments_to_markdown

# Set up logging
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class JobSettings:
    """Settings for a transcription job."""
    model_size: str = "medium"
    language: str = "en"
    diarize: bool = True
    min_speakers: int = 2
    max_speakers: int = 4
    hf_token: t.Optional[str] = None


class PipelineError(Exception):
    """Exception raised for errors in the transcription pipeline."""
    pass


def process_file(
    media_path: t.Union[str, Path],
    settings: JobSettings,
    db: DB,
    progress_cb: t.Callable[[float], None] = None
) -> int:
    """Process a media file through the transcription pipeline.
    
    Args:
        media_path: Path to the media file
        settings: Job settings
        db: Database instance
        progress_cb: Callback for progress updates (0-100)
        
    Returns:
        Transcript ID
        
    Raises:
        PipelineError: If processing fails
    """
    media_path = Path(media_path)
    
    # Validate file exists
    if not media_path.exists():
        raise PipelineError(f"File not found: {media_path}")
    
    # Set HF token if provided
    if settings.hf_token:
        os.environ["HF_TOKEN"] = settings.hf_token
    
    # Insert media into database
    job_id = db.insert_media(media_path)
    logger.info(f"Starting job {job_id} for {media_path}")
    
    # Track temporary files for cleanup
    temp_files = []
    
    try:
        # Update status to running
        db.set_status(job_id, Status.RUNNING)
        
        # Extract audio
        audio_path = transcribe.extract_audio(media_path)
        temp_files.append(audio_path)
        
        # Update progress
        if progress_cb:
            progress_cb(5)
            db.update_progress(job_id, 5)
        
        # Transcribe audio
        def transcribe_progress(p):
            # Scale progress to 5-65% range
            scaled = 5 + (p * 0.6)
            if progress_cb:
                progress_cb(scaled)
                db.update_progress(job_id, scaled)
        
        transcription = transcribe.transcribe(
            audio_path,
            model_size=settings.model_size,
            language=settings.language,
            progress_callback=transcribe_progress
        )
        
        # Update progress
        if progress_cb:
            progress_cb(65)
            db.update_progress(job_id, 65)
        
        # Perform diarization or use single speaker
        try:
            if settings.diarize:
                def diarize_progress(p):
                    # Scale progress to 65-90% range
                    scaled = 65 + (p * 0.25)
                    if progress_cb:
                        progress_cb(scaled)
                        db.update_progress(job_id, scaled)
                
                segments = diarize.diarize(
                    audio_path,
                    transcription.segments,
                    min_speakers=settings.min_speakers,
                    max_speakers=settings.max_speakers,
                    progress_callback=diarize_progress
                )
            else:
                segments = diarize.merge_into_single_speaker(transcription.segments)
        except Exception as e:
            logger.error(f"Diarization error: {e}")
            # Fall back to single speaker if diarization fails
            logger.warning("Falling back to single speaker mode due to diarization error")
            segments = diarize.merge_into_single_speaker(transcription.segments)
        
        # Update progress
        if progress_cb:
            progress_cb(90)
            db.update_progress(job_id, 90)
        
        # Get speaker map from database (may be empty)
        speaker_map = db.get_speaker_map(job_id)
        
        # Format the segments into a speaker-aware Markdown string with speaker mapping
        formatted_full_text = segments_to_markdown(segments, speaker_map)

        # Save the formatted transcript and segments to the database
        transcript_id = db.save_transcript(
            job_id,
            formatted_full_text,  # Use the new Markdown formatted text
            transcription.duration,
            segments
        )
        
        # Mark as completed
        db.set_status(job_id, Status.DONE)
        
        # Final progress update
        if progress_cb:
            progress_cb(100)
            db.update_progress(job_id, 100)
        
        logger.info(f"Job {job_id} completed successfully")
        return transcript_id
    
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        db.set_error(job_id, str(e))
        raise PipelineError(f"Failed to process {media_path}: {e}")
    
    finally:
        # Clean up temporary files
        for temp_path in temp_files:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_path}: {e}")