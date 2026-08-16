"""Source normalization and content fingerprints (re-exported from core)."""

from ytsum.core.identity import (
    SourceInputError,
    fingerprint,
    looks_like_local_media_input,
    normalize_source,
    normalize_youtube_url,
)

__all__ = [
    "SourceInputError",
    "fingerprint",
    "looks_like_local_media_input",
    "normalize_source",
    "normalize_youtube_url",
]
