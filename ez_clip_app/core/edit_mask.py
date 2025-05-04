"""
EditMask domain object for text-driven editing functionality.

This module defines a data class to represent which words should be kept or cut
in the final edited media file.
"""
from dataclasses import dataclass, field
from typing import List, Tuple
import json


@dataclass
class EditMask:
    """Mask that tracks which words to keep in an edited transcript.
    
    Attributes:
        media_id: Database ID for the associated media file
        keep: List of boolean values indicating which words to keep (True) or cut (False)
        kind: String identifying the mask format version
        _ranges: List of time ranges (start, end) in seconds (computed from keep[])
    """
    media_id: int
    keep: List[bool]                 # len == total words
    kind: str = "mask-v1"
    # ---------- non-serialised ----------
    _ranges: List[Tuple[float, float]] = field(init=False, default_factory=list)

    # build once ------------------------------------------------------
    def build_ranges(self, words, glue_gap: float = 0.12) -> None:
        """Collapse keep[] into merged (start,end) pairs in *seconds*.
        
        Args:
            words: List of Word objects with start/end times
            glue_gap: Maximum gap in seconds between words to merge them into a single range
            
        Returns:
            None (modifies self._ranges in place)
        """
        self._ranges = []
        cur = None
        for w, k in zip(words, self.keep):
            if k:
                if cur and (w.s - cur[1]) <= glue_gap:
                    cur = (cur[0], w.e)    # extend
                else:
                    if cur: 
                        self._ranges.append(cur)
                    cur = (w.s, w.e)
            else:
                if cur: 
                    self._ranges.append(cur)
                    cur = None
        if cur: 
            self._ranges.append(cur)
        return self._ranges
            
    def is_trivial(self) -> bool:
        """Return True if all words are kept (no editing needed)."""
        return all(self.keep)

    # serialisation --------------------------------------------------
    def dumps(self) -> str:
        """Serialize to JSON string.
        
        Returns:
            JSON string representation of the mask
        """
        removed = []
        s = None
        for i, k in enumerate(self.keep):
            if not k and s is None: 
                s = i
            if k and s is not None: 
                removed.append([s, i])
                s = None
        if s is not None: 
            removed.append([s, len(self.keep)])
        return json.dumps({"kind": self.kind, "remove": removed})

    @classmethod
    def loads(cls, media_id: int, json_str: str, total_words: int) -> "EditMask":
        """Deserialize from JSON string.
        
        Args:
            media_id: Database ID for the associated media file
            json_str: JSON string representation of the mask
            total_words: Total number of words in the transcript
            
        Returns:
            EditMask instance
        """
        data = json.loads(json_str)
        keep = [True] * total_words
        for s, e in data.get("remove", []): 
            keep[s:e] = [False] * (e - s)
        return cls(media_id, keep, data.get("kind", "mask-v1"))