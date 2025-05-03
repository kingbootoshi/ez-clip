"""
PyAnnote wrapper for speaker diarization.
"""
import logging
import typing as t
from pathlib import Path
import whisperx
from typing import List, Dict
import json
import os
import traceback
import pandas as pd  # Added for DataFrame conversion in assign_word_speakers

from ez_clip_app.core import model_cache
from ez_clip_app.config import DEFAULT_MIN_SPEAKERS, DEFAULT_MAX_SPEAKERS

# Set up logging
logger = logging.getLogger(__name__)


def _annotation_to_turns(annotation) -> List[Dict]:
    """
    Convert pyannote.core.Annotation into WhisperX-compatible
    list of speaker turns.
    """
    turns = []
    for segment, _, label in annotation.itertracks(yield_label=True):
        label_str = str(label)
        speaker_id = label_str.removeprefix("SPEAKER_")
        turns.append(
            {
                "start": float(segment.start),
                "end":   float(segment.end),
                "speaker": speaker_id,
            }
        )
    # sort just in case
    turns = sorted(turns, key=lambda t: t["start"])
    
    if os.getenv("EZCLIP_DBG"):
        logger.debug("[DBG] speaker_turns sample (raw IDs): %s", turns[:3])
        
    return turns


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
        annotation = diarize_pipeline(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )
        speaker_turns = _annotation_to_turns(annotation)
        
        if os.getenv("EZCLIP_DBG") and transcription_segments:
            logger.debug(
                "[DBG] transcription_segments[0]: %s | keys=%s",
                transcription_segments[0],
                list(transcription_segments[0].keys()))
            logger.debug(
                "[DBG] speaker_turns[0]: %s | keys=%s",
                speaker_turns[0],
                list(speaker_turns[0].keys()))
            logger.debug(
                "[DBG] Counts → turns=%d, segments=%d",
                len(speaker_turns), len(transcription_segments))
        
        # Update progress
        if progress_callback:
            progress_callback(80)
        
        try:
            # whisperx.assign_word_speakers expects a pandas DataFrame
            # with at least [start, end, speaker] columns. Convert our
            # list-of-dict speaker_turns into the required format.

            diarize_df = pd.DataFrame(speaker_turns)

            # Defensive check – ensure required columns exist to avoid
            # downstream KeyErrors should whisperX change its API.
            required_cols = {"start", "end", "speaker"}
            if not required_cols.issubset(diarize_df.columns):
                missing = required_cols - set(diarize_df.columns)
                raise RuntimeError(
                    f"Diarization DataFrame missing expected columns: {missing}"
                )

            transcript_dict = {"segments": transcription_segments}
            result = whisperx.assign_word_speakers(diarize_df, transcript_dict)
            
            # Update progress
            if progress_callback:
                progress_callback(90)
            
            logger.info(f"Diarization completed: {len(result['segments'])} segments")
            
            return result["segments"]
        except Exception as exc:
            logger.error("assign_word_speakers() failed: %s", exc)
            logger.error(traceback.format_exc())

            if os.getenv("EZCLIP_DBG"):
                dump = {
                    "speaker_turns": speaker_turns[:10],
                    "transcription_segments": transcription_segments[:10],
                    "exception": str(exc),
                    "traceback": traceback.format_exc(),
                }
                dump_path = Path("/tmp/ezclip_dbg_assign_word_speakers.json")
                dump_path.write_text(json.dumps(dump, indent=2))
                logger.warning("[DBG] dumped payload to %s", dump_path)

            # Handle the case where assignment fails
            logger.warning(f"Speaker assignment failed: {exc}. Falling back to simple assignment.")
            
            # Fall back to a simpler speaker assignment approach
            segments = transcription_segments.copy()
            
            # Create a mapping of time to speaker
            speaker_map = {}
            for segment, _, label in annotation.itertracks(yield_label=True):
                start_time = float(segment.start)
                end_time = float(segment.end)
                label_str = str(label)
                speaker = label_str.removeprefix("SPEAKER_")
                
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
                    segment["speaker"] = most_common_speaker  # Already has SPEAKER_ prefix
                else:
                    segment["speaker"] = "SPEAKER_UNKNOWN"
            
            # Update progress
            if progress_callback:
                progress_callback(90)
            
            if os.getenv("EZCLIP_DBG"):
                logger.debug("[DBG] simple-assignment speakers present: %s",
                             {s['speaker'] for s in segments})
            
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