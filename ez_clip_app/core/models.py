"""
Pydantic models for the WhisperX app.

This module contains the data transfer objects used to represent transcription data
throughout the application.
"""
from pydantic import BaseModel, ConfigDict


class Word(BaseModel):
    """Single token with timing-info + (optional) speaker label.
    
    Attributes:
        w: The word text (surface form)
        s: Start time in seconds (start-sec)
        e: End time in seconds (end-sec)
        score: Confidence score (0-1) for the word, optional
        speaker: Speaker identifier, optional
    """
    w: str
    s: float  # start_sec
    e: float  # end_sec
    score: float = 0.0
    speaker: str | None = None  # NEW — populated by DB
    model_config = ConfigDict(
        extra='ignore',          # tolerate unknown keys at parse-time
        validate_assignment=True # allow mutability for *declared* attrs
    )


class Segment(BaseModel):
    """Segment model representing a segment of the transcription.
    
    Attributes:
        id: The segment ID
        speaker: Speaker identifier
        start_sec: Start time in seconds
        end_sec: End time in seconds
        text: The transcribed text
        words: List of Word objects
    """
    id: int
    speaker: str
    start_sec: float
    end_sec: float
    text: str
    words: list[Word] = []
    model_config = ConfigDict(extra='ignore')


class TranscriptionResult(BaseModel):
    """Complete transcription result for a media file.
    
    Attributes:
        segments: List of Segment objects
        duration: Duration of the transcription in seconds
        full_text: The complete transcription text
    """
    segments: list[Segment]
    duration: float
    full_text: str