"""
Tests for the EditMask domain object.
"""
import json
import pytest
from ez_clip_app.core import EditMask
from ez_clip_app.core.models import Word


def test_edit_mask_initialization():
    """Test basic EditMask initialization."""
    mask = EditMask(media_id=1, keep=[True, False, True])
    assert mask.media_id == 1
    assert mask.keep == [True, False, True]
    assert mask.kind == "mask-v1"
    assert mask._ranges == []


def test_is_trivial():
    """Test the is_trivial method."""
    # All words kept
    mask = EditMask(media_id=1, keep=[True, True, True])
    assert mask.is_trivial() is True
    
    # Some words removed
    mask = EditMask(media_id=1, keep=[True, False, True])
    assert mask.is_trivial() is False
    
    # All words removed (unlikely but should work)
    mask = EditMask(media_id=1, keep=[False, False, False])
    assert mask.is_trivial() is False


def test_dumps_loads_roundtrip():
    """Test serialization and deserialization roundtrip."""
    # Original mask
    original = EditMask(media_id=1, keep=[True, False, True, True, False, False, True])
    
    # Serialize
    json_str = original.dumps()
    
    # Deserialize
    total_words = len(original.keep)
    restored = EditMask.loads(1, json_str, total_words)
    
    # Verify
    assert restored.media_id == original.media_id
    assert restored.keep == original.keep
    assert restored.kind == original.kind


def test_build_ranges():
    """Test building time ranges from words."""
    # Create test words
    words = [
        Word(w="hello", s=0.0, e=0.5),
        Word(w="this", s=0.6, e=0.9),
        Word(w="is", s=1.0, e=1.2),
        Word(w="a", s=1.3, e=1.4),
        Word(w="test", s=1.5, e=2.0),
    ]
    
    # Keep all words - should result in a single range if gap is large enough
    mask = EditMask(media_id=1, keep=[True, True, True, True, True])
    ranges = mask.build_ranges(words, glue_gap=0.5)
    assert len(ranges) == 1
    assert ranges[0] == (0.0, 2.0)  # Start of first word to end of last word
    
    # Keep all words but with smaller glue gap - should result in multiple ranges
    mask = EditMask(media_id=1, keep=[True, True, True, True, True])
    ranges = mask.build_ranges(words, glue_gap=0.05)
    assert len(ranges) == 5  # Each word is its own range
    
    # Keep some words
    mask = EditMask(media_id=1, keep=[True, False, True, True, False])
    ranges = mask.build_ranges(words, glue_gap=0.5)
    assert len(ranges) == 2
    assert ranges[0] == (0.0, 0.5)  # First word
    assert ranges[1] == (1.0, 1.4)  # "is" and "a" merged


def test_dumps_format():
    """Test the format of the dumped JSON."""
    mask = EditMask(media_id=1, keep=[True, False, False, True, True, False])
    json_str = mask.dumps()
    data = json.loads(json_str)
    
    assert data["kind"] == "mask-v1"
    assert data["remove"] == [[1, 3], [5, 6]]  # Indices of removed spans


def test_loads_with_different_total():
    """Test loading with a different total_words than in the original mask."""
    original = EditMask(media_id=1, keep=[True, False, True])
    json_str = original.dumps()
    
    # Load with a larger total_words
    loaded = EditMask.loads(1, json_str, 5)
    assert len(loaded.keep) == 5
    assert loaded.keep[:3] == [True, False, True]  # Original part preserved
    assert loaded.keep[3:] == [True, True]  # New elements set to True