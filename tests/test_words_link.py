"""
Tests for words linking to segments.
"""
import pytest

def test_words_roundtrip(tmp_path):
    from ez_clip_app.data.database import DB
    db = DB(db_path=":memory:")
    media_id = db.insert_media("dummy.mp4")
    db.save_transcript(
        media_id, "hi", 1.0,
        [dict(speaker="01", start=0.0, end=1.0,
              text="hi", words=[dict(word="hi",
                                     start=0.0, end=0.2, score=1.0)])]
    )
    res = db.get_transcript(media_id)
    assert res["segments"][0]["words"][0]["text"] == "hi"