"""
Unit tests for Pydantic models in the ez_clip_app.
"""
import pytest
from pydantic import ValidationError

from ez_clip_app.core.models import Word, Segment, TranscriptionResult
from ez_clip_app.data.database import DB


def test_word_model_basic():
    """Test basic Word model creation and validation."""
    # Valid word
    word = Word(w="hello", s=1.0, e=1.5, score=0.95)
    assert word.w == "hello"
    assert word.s == 1.0
    assert word.e == 1.5
    assert word.score == 0.95
    
    # Word with default score
    word = Word(w="world", s=2.0, e=2.5)
    assert word.w == "world"
    assert word.s == 2.0
    assert word.e == 2.5
    assert word.score is None
    
    # Test model_dump() method
    word_dict = word.model_dump()
    assert word_dict == {"w": "world", "s": 2.0, "e": 2.5, "score": None}


def test_word_model_validation_errors():
    """Test Word model validation errors."""
    # Missing required fields
    with pytest.raises(ValidationError):
        Word(s=1.0, e=1.5)  # Missing w
    
    with pytest.raises(ValidationError):
        Word(w="hello", e=1.5)  # Missing s
    
    with pytest.raises(ValidationError):
        Word(w="hello", s=1.0)  # Missing e


def test_segment_model_basic():
    """Test basic Segment model creation and validation."""
    # Valid segment without words
    segment = Segment(
        id=1,
        speaker="SPEAKER_01",
        start_sec=0.0,
        end_sec=5.0,
        text="Hello world"
    )
    assert segment.id == 1
    assert segment.speaker == "SPEAKER_01"
    assert segment.start_sec == 0.0
    assert segment.end_sec == 5.0
    assert segment.text == "Hello world"
    assert segment.words == []
    
    # Valid segment with words
    words = [
        Word(w="hello", s=0.0, e=0.5, score=0.9),
        Word(w="world", s=0.5, e=1.0, score=0.8)
    ]
    segment = Segment(
        id=1,
        speaker="SPEAKER_01",
        start_sec=0.0,
        end_sec=1.0,
        text="Hello world",
        words=words
    )
    assert segment.words[0].w == "hello"
    assert segment.words[1].w == "world"


def test_segment_model_validation_errors():
    """Test Segment model validation errors."""
    # Missing required fields
    with pytest.raises(ValidationError):
        Segment(
            speaker="SPEAKER_01",
            start_sec=0.0,
            end_sec=5.0,
            text="Hello world"
        )  # Missing id
    
    with pytest.raises(ValidationError):
        Segment(
            id=1,
            start_sec=0.0,
            end_sec=5.0,
            text="Hello world"
        )  # Missing speaker


def test_transcription_result_model():
    """Test TranscriptionResult model creation and validation."""
    # Create segments
    segment1 = Segment(
        id=1,
        speaker="SPEAKER_01",
        start_sec=0.0,
        end_sec=5.0,
        text="Hello world"
    )
    segment2 = Segment(
        id=2,
        speaker="SPEAKER_02",
        start_sec=5.0,
        end_sec=10.0,
        text="How are you?"
    )
    
    # Create TranscriptionResult
    result = TranscriptionResult(
        segments=[segment1, segment2],
        duration=10.0,
        full_text="Hello world\nHow are you?"
    )
    
    assert len(result.segments) == 2
    assert result.duration == 10.0
    assert result.full_text == "Hello world\nHow are you?"


def test_transcription_result_validation_errors():
    """Test TranscriptionResult model validation errors."""
    # Missing required fields
    with pytest.raises(ValidationError):
        TranscriptionResult(
            segments=[],
            full_text="Hello world"
        )  # Missing duration
    
    with pytest.raises(ValidationError):
        TranscriptionResult(
            segments=[],
            duration=10.0
        )  # Missing full_text


def test_models_extra_fields():
    """Test that models ignore extra fields."""
    # Word with extra fields
    word = Word(w="hello", s=1.0, e=1.5, score=0.95, extra_field="ignored")
    assert not hasattr(word, "extra_field")
    
    # Segment with extra fields
    segment = Segment(
        id=1,
        speaker="SPEAKER_01",
        start_sec=0.0,
        end_sec=5.0,
        text="Hello world",
        unknown_field="ignored"
    )
    assert not hasattr(segment, "unknown_field")


def test_models_roundtrip(fixture_data):
    """Test model round-trip conversion from dict → model → dict."""
    # Get segments data
    segments_data = fixture_data["segments"]
    
    # Create Segment models with words
    segment_models = []
    for seg_data in segments_data[:2]:  # Just use the first two segments for testing
        # Create Word models
        word_models = []
        for word_data in seg_data.get("words", [])[:2]:  # Just use first two words
            word = Word(
                w=word_data["word"],
                s=word_data["start"],
                e=word_data["end"],
                score=word_data.get("score", 0.5)
            )
            word_models.append(word)
        
        # Create Segment model
        segment = Segment(
            id=1,  # Just use a dummy ID
            speaker=seg_data["speaker"],
            start_sec=seg_data["start"],
            end_sec=seg_data["end"],
            text=seg_data["text"],
            words=word_models
        )
        segment_models.append(segment)
    
    # Create TranscriptionResult
    result = TranscriptionResult(
        segments=segment_models,
        duration=fixture_data["duration"],
        full_text=fixture_data["markdown"]
    )
    
    # Test conversion back to dict
    result_dict = result.model_dump()
    
    # Verify structure is preserved
    assert "segments" in result_dict
    assert "duration" in result_dict
    assert "full_text" in result_dict
    assert len(result_dict["segments"]) == len(segment_models)
    
    # Test segment conversion
    segment = result.segments[0]
    segment_dict = segment.model_dump()
    assert "id" in segment_dict
    assert "speaker" in segment_dict
    assert "start_sec" in segment_dict
    assert "end_sec" in segment_dict
    assert "text" in segment_dict
    assert "words" in segment_dict
    
    # Test word conversion
    if segment.words:
        word = segment.words[0]
        word_dict = word.model_dump()
        assert "w" in word_dict
        assert "s" in word_dict
        assert "e" in word_dict
        assert "score" in word_dict