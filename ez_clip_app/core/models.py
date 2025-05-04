"""
Pydantic models for the WhisperX app.

This module contains the data transfer objects used to represent transcription data
throughout the application.
"""
from pydantic import BaseModel, ConfigDict


class Word(BaseModel):
    """Word model representing individual words in a transcription segment.
    
    Attributes:
        w: The word text
        s: Start time in seconds
        e: End time in seconds
        score: Confidence score (0-1) for the word, optional
    """
    w: str
    s: float  # start_sec
    e: float  # end_sec
    score: float | None = None
    model_config = ConfigDict(extra='ignore')  # tolerate unknown keys


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