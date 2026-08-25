"""Deterministic, reversible transcript preparation for Frontier extraction."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from pydantic import Field

from chew.core.identity import fingerprint
from chew.core.models import FrozenModel, Transcript

_MARKER = re.compile(r"\[(?:[^\]]+)\]")
_FILLER = re.compile(r"(?i)^(?:um+|uh+|erm+|음+|어+)[,!.]?\s*")
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class InputBudget:
    max_input_tokens: int | None
    reserved_output_tokens: int = 0

    def __post_init__(self) -> None:
        if self.max_input_tokens is not None and self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be positive")
        if self.reserved_output_tokens < 0:
            raise ValueError("reserved_output_tokens must be non-negative")


class PreparedParagraph(FrozenModel):
    paragraph_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    raw_segment_indexes: tuple[int, ...] = Field(min_length=1)


class PreparedTranscript(FrozenModel):
    compiler_version: str = "prepared-transcript-v1"
    raw_transcript_fingerprint: str = Field(min_length=1)
    paragraphs: tuple[PreparedParagraph, ...] = Field(min_length=1)
    non_speech_markers: tuple[str, ...] = ()
    estimated_input_tokens: int = Field(ge=0)
    reserved_output_tokens: int = Field(ge=0)
    fits_frontier_budget: bool
    fingerprint: str = Field(min_length=1)

    def render_for_frontier(self) -> str:
        return "\n\n".join(
            f"[{paragraph.paragraph_id} | raw:{','.join(str(item) for item in paragraph.raw_segment_indexes)}]\n"
            f"{paragraph.text}"
            for paragraph in self.paragraphs
        )


class InputCompiler:
    """Apply conservative fixed-order cleanup without changing source identity."""

    VERSION = "prepared-transcript-v1"

    def compile(self, transcript: Transcript, budget: InputBudget) -> PreparedTranscript:
        markers: list[str] = []
        pieces: list[tuple[int, str]] = []
        for index, segment in enumerate(sorted(transcript.segments, key=lambda item: (item.start_ms, item.end_ms))):
            raw_text = unicodedata.normalize("NFC", segment.text)
            markers.extend(match.group(0) for match in _MARKER.finditer(raw_text))
            text = _MARKER.sub(" ", raw_text)
            text = _FILLER.sub("", text)
            text = _SPACE.sub(" ", text).strip()
            if text:
                pieces.append((index, text))
        if not pieces:
            # Transcript validation guarantees source text exists; preserving its first
            # segment is safer than inventing a prepared representation.
            pieces.append((0, transcript.segments[0].text))
        paragraph = PreparedParagraph(
            paragraph_id="paragraph-001",
            text=" ".join(text for _, text in pieces),
            raw_segment_indexes=tuple(index for index, _ in pieces),
        )
        estimated = self._estimate_tokens(paragraph.text)
        fits = budget.max_input_tokens is None or estimated + budget.reserved_output_tokens <= budget.max_input_tokens
        content = {
            "compiler_version": self.VERSION,
            "raw_transcript_fingerprint": fingerprint(transcript),
            "paragraphs": [paragraph.model_dump(mode="json")],
            "non_speech_markers": tuple(dict.fromkeys(markers)),
            "estimated_input_tokens": estimated,
            "reserved_output_tokens": budget.reserved_output_tokens,
            "fits_frontier_budget": fits,
        }
        return PreparedTranscript.model_validate({**content, "fingerprint": fingerprint(content)})

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return len(re.findall(r"\S+", text))
