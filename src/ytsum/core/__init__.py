"""Core domain models, identity normalization, and core prompts."""

from ytsum.core.identity import (
    SourceInputError,
    looks_like_local_media_input,
    normalize_source,
    normalize_youtube_url,
)
from ytsum.core.models import (
    Chapter,
    ChapterSummary,
    Claim,
    Evidence,
    FrozenModel,
    GenerationRequest,
    GenerationResult,
    KnowledgePack,
    Provenance,
    SourceIdentity,
    SourceKind,
    Topic,
    TopicSummary,
    Transcript,
    TranscriptSegment,
)
from ytsum.core.prompts import (
    CHAPTER_PROMPT,
    COMPOSE_PROMPT,
    PROMPT_FINGERPRINT,
    REPAIR_PROMPT,
    TOPIC_PROMPT,
)

__all__ = [
    "CHAPTER_PROMPT",
    "COMPOSE_PROMPT",
    "PROMPT_FINGERPRINT",
    "REPAIR_PROMPT",
    "TOPIC_PROMPT",
    "Chapter",
    "ChapterSummary",
    "Claim",
    "Evidence",
    "FrozenModel",
    "GenerationRequest",
    "GenerationResult",
    "KnowledgePack",
    "Provenance",
    "SourceIdentity",
    "SourceInputError",
    "SourceKind",
    "Topic",
    "TopicSummary",
    "Transcript",
    "TranscriptSegment",
    "looks_like_local_media_input",
    "normalize_source",
    "normalize_youtube_url",
]
