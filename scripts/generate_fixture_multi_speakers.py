#!/usr/bin/env python3
"""
Generate a frozen JSON fixture from the real multi_speakers.mp4 clip.

Why?
    • Unit tests shouldn't call heavy ML models every run.
    • We run the full pipeline **once**, then reuse the JSON forever
      (regenerate only when you intentionally upgrade models).

Outputs
-------
A file like tests/fixtures/multi_speakers_fixture.json with structure:
{
  "duration":  51.234,
  "segments":  [ {...}, {...}, ... ],   # speaker-labelled + word-level
  "markdown":  "**00:** ...",           # pretty transcript for snapshot tests
  "model_meta": {
        "whisper_size":   "medium",
        "diarize":        true,
        "generated_at":   "2025-05-03T18:55:42Z"
  }
}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to make ez_clip_app importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tempfile
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import whisperx                            # pulls torch etc.; heavy
from ez_clip_app.core import model_cache
from ez_clip_app.core.formatting import segments_to_markdown
from ez_clip_app.core.transcribe import extract_audio, transcribe
from ez_clip_app.core.diarize import diarize, merge_into_single_speaker


# ---------- helpers ---------------------------------------------------------

def _np_to_builtin(obj: Any) -> Any:
    """Recursively convert numpy types → native Python for JSON-ability."""
    if isinstance(obj, dict):
        return {k: _np_to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_np_to_builtin(i) for i in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_)):
        return bool(obj)
    return obj


def build_fixture(
    video_path: Path,
    model_size: str = "medium",
    language: str = "en",
    diarize_flag: bool = True,
    min_speakers: int = 1,
    max_speakers: int = 4,
    hf_token: str | None = None,
) -> Dict[str, Any]:
    """Run the heavy parts once and return a fully serialisable dict."""
    # ---------------- extraction + transcription ------------------
    wav_path = extract_audio(video_path)

    result = transcribe(
        wav_path,
        model_size=model_size,
        language=language,
        progress_callback=lambda p: None,          # suppress prints
    )

    segments: List[dict] = result.segments

    # ---------------- optional diarisation -----------------------
    if diarize_flag:
        # WhisperX <-> pyannote bridge
        segments = diarize(
            wav_path,
            segments,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            progress_callback=lambda p: None,
        )
    else:
        segments = merge_into_single_speaker(segments)

    # ---------------- markdown pretty print ----------------------
    md = segments_to_markdown(segments)

    # ---------------- build payload ------------------------------
    payload: Dict[str, Any] = {
        "duration":       float(result.duration),
        "segments":       _np_to_builtin(segments),
        "markdown":       md,
        "model_meta": {
            "whisper_size": model_size,
            "diarize":      diarize_flag,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        },
    }
    return payload


# ---------- CLI -------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate JSON fixture for EZ-Clip unit tests."
    )
    parser.add_argument(
        "--video",
        type=Path,
        required=True,
        help="Path to multi_speakers.mp4 (or any other clip).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Where to write the JSON fixture (will overwrite).",
    )
    parser.add_argument(
        "--model-size",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v1", "large-v2", "turbo"],
    )
    parser.add_argument("--language", default="en")
    parser.add_argument(
        "--no-diarize",
        action="store_true",
        help="Skip speaker diarization (single-speaker fixture).",
    )
    parser.add_argument("--min-speakers", type=int, default=1)
    parser.add_argument("--max-speakers", type=int, default=4)
    parser.add_argument(
        "--hf-token",
        default=os.getenv("HF_TOKEN", ""),
        help="Hugging Face token (env HF_TOKEN takes precedence).",
    )

    args = parser.parse_args(argv)

    # honour user-supplied HF token (whisperx / pyannote)
    if args.hf_token:
        os.environ["HF_TOKEN"] = args.hf_token

    if not args.video.exists():
        parser.error(f"Video not found: {args.video}")

    print(f"[•] Processing {args.video} with WhisperX-{args.model_size} …")

    fixture = build_fixture(
        video_path=args.video,
        model_size=args.model_size,
        language=args.language,
        diarize_flag=not args.no_diarize,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
        hf_token=args.hf_token or None,
    )

    # Pretty-print JSON (ensure dirs exist)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=2)

    print(f"[✓] Fixture written → {args.out}  "
          f"({len(fixture['segments'])} segments, "
          f"{fixture['duration']:.1f} s)")

    # cleanup wav
    try:
        wav_path = next(
            p for p in Path(tempfile.gettempdir()).glob("tmp*.wav") if p.exists()
        )
        wav_path.unlink(missing_ok=True)
    except StopIteration:
        pass


if __name__ == "__main__":
    main()