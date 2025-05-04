"""
Thin wrapper around ffmpeg-python for later "Descript-style" edits.
Only defines interface signatures for now.
"""
import ffmpeg
from pathlib import Path
from typing import List, Tuple

def extract_clip(src: Path, dst: Path,
                 start: float, end: float) -> None:
    """Trim video between timestamps [start, end)."""
    (
        ffmpeg
        .input(str(src), ss=start, to=end)
        .output(str(dst), c="copy")
        .overwrite_output()
        .run(quiet=True)
    )

def concat_clips(clips: List[Path], dst: Path) -> None:
    """Simple concat by demux & remux (same codec)."""
    txt = "\n".join(f"file '{c}'" for c in clips)
    tmp_list = Path(dst.parent) / "_concat.txt"
    tmp_list.write_text(txt)
    (
        ffmpeg
        .input(str(tmp_list), format="concat", safe=0)
        .output(str(dst), c="copy")
        .overwrite_output()
        .run(quiet=True)
    )
    tmp_list.unlink()