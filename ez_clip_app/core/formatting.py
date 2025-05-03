# -*- coding: utf-8 -*-
"""
Utilities for formatting transcription data.
"""
import logging
import typing as t
from typing import List, Dict

# Set up logging
logger = logging.getLogger(__name__)


def segments_to_markdown(segments: List[Dict]) -> str:
    """
    Converts a list of transcription segments into a speaker-aware Markdown string.

    Merges consecutive segments from the same speaker and prefixes each speaker's
    turn with their ID in bold (e.g., "**SPEAKER_00:**"). Turns are separated
    by double newlines.

    Args:
        segments (List[Dict]): A list of segment dictionaries. Each dictionary must
                               have a 'start' key (for sorting) and should have
                               'speaker' and 'text' keys. Missing 'speaker' defaults
                               to 'SPEAKER_UNKNOWN'. Missing 'text' defaults to "".

    Returns:
        str: A Markdown-formatted string representing the transcript with
             speaker attribution. Returns an empty string if the input list
             is empty.
    """
    # Return early if there are no segments to process
    if not segments:
        logger.warning("segments_to_markdown called with empty segment list.")
        return ""

    logger.info(f"Formatting {len(segments)} segments into Markdown.")

    # Sort segments by start time to ensure chronological order.
    # This is crucial for correctly merging consecutive utterances.
    try:
        segments = sorted(segments, key=lambda s: s["start"])
    except KeyError:
        logger.error("Segments missing 'start' key, cannot sort for formatting.")
        # Fallback: attempt to process without sorting, results may be incorrect.
        pass # Or raise an error depending on desired strictness

    output_paragraphs = [] # Stores the final formatted paragraphs
    current_buffer = []    # Temporarily holds text pieces for the current speaker
    current_speaker = None # Tracks the speaker of the current buffer

    def flush_buffer():
        """
        Flushes the content of the current_buffer into the output_paragraphs list.
        Formats the text with the current speaker's ID. Clears the buffer afterwards.
        """
        # nonlocal current_speaker, current_buffer, output_paragraphs # Not strictly needed but clarifies intent
        if current_buffer:
            # Join collected text pieces, strip surrounding whitespace
            joined_text = " ".join(current_buffer).strip()
            # Format the paragraph with speaker ID in bold Markdown
            formatted_paragraph = f"**{current_speaker}:** {joined_text}"
            output_paragraphs.append(formatted_paragraph)
            # Clear the buffer for the next speaker turn
            current_buffer.clear()
            logger.debug(f"Flushed buffer for {current_speaker}, added paragraph.")

    # Iterate through each sorted segment
    for i, seg in enumerate(segments):
        # Get speaker, default to 'SPEAKER_UNKNOWN' if missing
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        # Get text, default to empty string, strip whitespace
        text = seg.get("text", "").strip()

        # If the speaker changes OR it's the very first segment, flush the previous buffer
        # and update the current speaker.
        if speaker != current_speaker:
            # Don't flush if it's the *very first* segment and buffer is empty
            # Ensures flush isn't called unnecessarily at start
            if i > 0 or current_buffer:
                 flush_buffer()
            current_speaker = speaker
            logger.debug(f"Speaker changed to {current_speaker} at segment {i}")

        # Append the current segment's text to the buffer if it's not empty
        if text:
            current_buffer.append(text)

    # After the loop finishes, flush any remaining text in the buffer
    # (this handles the very last speaker turn)
    flush_buffer()

    logger.info(f"Formatting complete. Generated {len(output_paragraphs)} paragraphs.")

    # Join all formatted paragraphs with double newlines for Markdown compatibility
    final_markdown = "\n\n".join(output_paragraphs)
    return final_markdown 