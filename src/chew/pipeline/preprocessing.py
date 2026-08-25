"""Optional, local transcript preprocessing strategies.

The strategies never call an LLM.  Missing optional dependencies simply remove
their strategy from the composed pipeline, preserving the base CLI workflow.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, cast

from chew.core.models import Transcript, TranscriptSegment
from chew.pipeline.segmentation import BoundaryDetector, PausePunctuationBoundaryDetector

_KO_FILLERS = re.compile(r"(?<!\S)(?:음+~?|어+~?)(?!\S)")
_EN_FILLERS = re.compile(
    r"\b(?:um+|uh+|you know|i mean)\b",
    re.IGNORECASE,
)
_STUTTER = re.compile(r"(?<!\w)(\w)\1{2,}")
_MULTI_SPACE = re.compile(r"\s+")


class PreprocessingStrategy(Protocol):
    """A locally executable preprocessing step."""

    @property
    def name(self) -> str: ...

    def available(self) -> bool: ...

    def process(self, transcript: Transcript) -> Transcript: ...


class PunctuationModelProtocol(Protocol):
    def restore_punctuation(self, text: str) -> str: ...


class SentenceTransformerProtocol(Protocol):
    def encode(self, texts: list[str], *, normalize_embeddings: bool) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True, slots=True)
class PreprocessingStats:
    original_segment_count: int
    processed_segment_count: int
    original_token_estimate: int
    processed_token_estimate: int
    removed_filler_count: int
    applied_strategies: tuple[str, ...]

    @property
    def token_reduction_pct(self) -> float:
        if self.original_token_estimate == 0:
            return 0.0
        return (1 - self.processed_token_estimate / self.original_token_estimate) * 100


def _token_estimate(transcript: Transcript) -> int:
    return sum(len(segment.text.split()) for segment in transcript.segments)


def count_fillers(text: str) -> int:
    """Count filler phrases recognized by the built-in removal strategy."""
    return len(_KO_FILLERS.findall(text)) + len(_EN_FILLERS.findall(text))


class FillerRemovalStrategy:
    name = "filler-removal"

    def available(self) -> bool:
        return True

    def process(self, transcript: Transcript) -> Transcript:
        cleaned: list[TranscriptSegment] = []
        for segment in transcript.segments:
            text = _KO_FILLERS.sub("", segment.text)
            text = _EN_FILLERS.sub("", text)
            text = _STUTTER.sub(r"\1", text)
            text = _MULTI_SPACE.sub(" ", text).strip(" ,")
            if text:
                cleaned.append(segment.model_copy(update={"text": text}))
        # A transcript consisting entirely of fillers is still evidence.  Do
        # not turn it into an invalid empty Transcript.
        return transcript.model_copy(update={"segments": tuple(cleaned)}) if cleaned else transcript


class PunctuationStrategy:
    name = "punctuation-restoration"

    def __init__(self) -> None:
        self._model: PunctuationModelProtocol | None = None

    def available(self) -> bool:
        return importlib.util.find_spec("deepmultilingualpunctuation") is not None

    def _get_model(self) -> PunctuationModelProtocol:
        if self._model is None:
            module = import_module("deepmultilingualpunctuation")
            self._model = cast(PunctuationModelProtocol, module.PunctuationModel())
        return self._model

    def process(self, transcript: Transcript) -> Transcript:
        model = self._get_model()
        return transcript.model_copy(
            update={
                "segments": tuple(
                    segment.model_copy(update={"text": model.restore_punctuation(segment.text).strip()})
                    for segment in transcript.segments
                )
            }
        )


class SemanticBoundaryDetector:
    """Choose low-similarity boundaries near the normal target timestamp."""

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._model: SentenceTransformerProtocol | None = None
        self._fallback: BoundaryDetector = PausePunctuationBoundaryDetector()

    def _get_model(self) -> SentenceTransformerProtocol:
        if self._model is None:
            module = import_module("sentence_transformers")
            self._model = cast(
                SentenceTransformerProtocol,
                module.SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2"),
            )
        return self._model

    def choose(self, transcript: Transcript, start_ms: int, target_ms: int, limit_ms: int) -> int:
        candidates = [
            segment
            for segment in transcript.segments
            if start_ms < segment.end_ms <= limit_ms and segment.start_ms >= start_ms
        ]
        if len(candidates) < 3:
            return self._fallback.choose(transcript, start_ms, target_ms, limit_ms)
        embeddings = self._get_model().encode([segment.text for segment in candidates], normalize_embeddings=True)
        scored: list[tuple[float, int]] = []
        for index in range(len(candidates) - 1):
            similarity = float(
                sum(float(a) * float(b) for a, b in zip(embeddings[index], embeddings[index + 1], strict=True))
            )
            boundary = candidates[index].end_ms
            if similarity < self.threshold:
                scored.append((similarity + abs(boundary - target_ms) / 1_000_000, boundary))
        return min(scored)[1] if scored else self._fallback.choose(transcript, start_ms, target_ms, limit_ms)


class SemanticBoundaryStrategy:
    name = "semantic-boundary"

    def available(self) -> bool:
        return importlib.util.find_spec("sentence_transformers") is not None

    def process(self, transcript: Transcript) -> Transcript:
        return transcript

    def make_detector(self, threshold: float = 0.5) -> SemanticBoundaryDetector:
        return SemanticBoundaryDetector(threshold)


class TranscriptPreprocessor:
    """Apply enabled preprocessing strategies in a fixed, auditable order."""

    def __init__(self, strategies: list[PreprocessingStrategy] | None = None) -> None:
        self.strategies = strategies or [FillerRemovalStrategy(), PunctuationStrategy(), SemanticBoundaryStrategy()]
        self.boundary_detector: BoundaryDetector | None = None

    def process(self, transcript: Transcript) -> tuple[Transcript, PreprocessingStats]:
        original = transcript
        applied: list[str] = []
        for strategy in self.strategies:
            if not strategy.available():
                continue
            transcript = strategy.process(transcript)
            applied.append(strategy.name)
            if isinstance(strategy, SemanticBoundaryStrategy):
                self.boundary_detector = strategy.make_detector()
        return transcript, PreprocessingStats(
            original_segment_count=len(original.segments),
            processed_segment_count=len(transcript.segments),
            original_token_estimate=_token_estimate(original),
            processed_token_estimate=_token_estimate(transcript),
            removed_filler_count=sum(count_fillers(segment.text) for segment in original.segments)
            - sum(count_fillers(segment.text) for segment in transcript.segments),
            applied_strategies=tuple(applied),
        )


def preprocess_transcript(
    transcript: Transcript,
    strategies: list[PreprocessingStrategy] | None = None,
) -> tuple[Transcript, PreprocessingStats]:
    return TranscriptPreprocessor(strategies).process(transcript)
