"""Pure metric helpers for the maintainer-only preprocessing spike."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_EN_FILLERS = re.compile(r"\b(?:um+|uh+|you know|i mean)\b", re.IGNORECASE)
_KO_FILLERS = re.compile(r"(?<!\S)(?:음+~?|어+~?)(?!\S)")


@dataclass(frozen=True)
class TranscriptMetrics:
    key: str
    raw_chars: int
    raw_tokens: int
    filler_count: int
    filler_ratio: float
    segment_count: int


def lock_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure_text(key: str, segments: list[str], token_count: int) -> TranscriptMetrics:
    text = " ".join(segments)
    words = text.split()
    fillers = len(_EN_FILLERS.findall(text)) + len(_KO_FILLERS.findall(text))
    return TranscriptMetrics(
        key=key,
        raw_chars=len(text),
        raw_tokens=token_count,
        filler_count=fillers,
        filler_ratio=fillers / len(words) if words else 0.0,
        segment_count=len(segments),
    )
