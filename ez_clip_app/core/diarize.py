"""
PyAnnote wrapper for speaker diarization.
"""
import logging
import typing as t
from pathlib import Path
import whisperx

from ez_clip_app.core import model_cache
from ez_clip_app.config import DEFAULT_MIN_SPEAKERS, DEFAULT_MAX_SPEAKERS

# Set up logging
logger = logging.getLogger(__name__)


def diarize(
    audio_path: t.Union[str, Path],
    transcription_segments: t.List[dict],
    min_speakers: int = DEFAULT_MIN_SPEAKERS,
    max_speakers: int = DEFAULT_MAX_SPEAKERS,
    progress_callback: t.Callable[[float], None] = None
) -> t.List[dict]:
    """Perform speaker diarization on transcribed segments.
    
    Args:
        audio_path: Path to audio file
        transcription_segments: List of transcription segments from WhisperX
        min_speakers: Minimum number of speakers to detect
        max_speakers: Maximum number of speakers to detect
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        Updated list of segments with speaker labels
    """
    audio_path = Path(audio_path)
    logger.info(f"Starting speaker diarization for {audio_path}")
    
    try:
        # Load diarization model
        diarize_pipeline = model_cache.get_diarization_model()
        
        # Update progress
        if progress_callback:
            progress_callback(70)
        
        # Perform diarization
        diarize_segments = diarize_pipeline(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )
        
        # Update progress
        if progress_callback:
            progress_callback(80)
        
        try:
            # Assign speaker labels to transcription segments
            result = whisperx.assign_word_speakers(
                diarize_segments,
                transcription_segments
            )
            
            # Update progress
            if progress_callback:
                progress_callback(90)
            
            logger.info(f"Diarization completed: {len(result['segments'])} segments")
            
            return result["segments"]
        except (KeyError, IndexError, TypeError) as e:
            # Handle the case where assignment fails
            logger.warning(f"Speaker assignment failed: {e}. Falling back to simple assignment.")
            
            # Fall back to a simpler speaker assignment approach
            segments = transcription_segments.copy()
            
            # Create a mapping of time to speaker
            speaker_map = {}
            for segment, track in diarize_segments.itertracks(yield_label=True):
                start_time = float(segment.start)
                end_time = float(segment.end)
                speaker = track
                
                # Store speaker for each second (with 0.5s resolution)
                current_time = start_time
                while current_time < end_time:
                    speaker_map[current_time] = speaker
                    current_time += 0.5
            
            # Assign speakers to segments
            for segment in segments:
                segment_start = segment.get("start", 0)
                segment_end = segment.get("end", 0)
                
                # Find the most common speaker in this segment
                speaker_counts = {}
                current_time = segment_start
                while current_time < segment_end:
                    # Find the closest time key in speaker_map
                    closest_time = min(speaker_map.keys(), key=lambda x: abs(x - current_time), default=None)
                    if closest_time is not None and abs(closest_time - current_time) < 1.0:
                        speaker = speaker_map[closest_time]
                        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
                    current_time += 0.5
                
                # Assign the most common speaker, or a default if none found
                if speaker_counts:
                    most_common_speaker = max(speaker_counts.items(), key=lambda x: x[1])[0]
                    segment["speaker"] = f"SPEAKER_{most_common_speaker}"
                else:
                    segment["speaker"] = "SPEAKER_UNKNOWN"
            
            # Update progress
            if progress_callback:
                progress_callback(90)
            
            logger.info(f"Simple diarization completed: {len(segments)} segments")
            
            return segments
    
    except Exception as e:
        logger.error(f"Error during diarization: {e}")
        # Fall back to single speaker if diarization fails
        logger.warning("Falling back to single speaker mode")
        return merge_into_single_speaker(transcription_segments)


def merge_into_single_speaker(transcription_segments: t.List[dict]) -> t.List[dict]:
    """Merge all segments without diarization (single speaker).
    
    Args:
        transcription_segments: List of transcription segments from WhisperX
        
    Returns:
        Updated list of segments with default speaker label
    """
    logger.info("No diarization requested, using single speaker")
    
    # Add a default speaker label to all segments
    for segment in transcription_segments:
        segment["speaker"] = "SPEAKER_1"
    
    return transcription_segments