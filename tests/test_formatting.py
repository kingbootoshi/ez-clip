"""
Validate segments_to_markdown() behaviour on controlled inputs.
"""
import pytest
from ez_clip_app.core.formatting import segments_to_markdown

def test_markdown_roundtrip(fixture_data):
    md = segments_to_markdown(fixture_data["segments"])
    # Snapshot string equality
    assert md == fixture_data["markdown"]

@pytest.mark.parametrize(
    "segments, expected",
    [
        # single speaker collapse
        ([{"start":0,"end":1,"text":"hello","speaker":"00"},
          {"start":1.5,"end":2,"text":"world","speaker":"00"}],
         "**00:** hello world"),
        # speaker switch
        ([{"start":0,"end":1,"text":"foo","speaker":"A"},
          {"start":1,"end":2,"text":"bar","speaker":"B"}],
         "**A:** foo\n\n**B:** bar"),
    ]
)
def test_edge_cases(segments, expected):
    assert segments_to_markdown(segments) == expected