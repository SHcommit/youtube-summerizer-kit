"""Source normalization and deterministic content fingerprints."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

from ytsum.core.models import SourceIdentity, SourceKind

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
_LOCAL_MEDIA_SUFFIXES = {
    ".aac",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
}


class SourceInputError(ValueError):
    """A missing, unsupported, or invalid source supplied by the user."""


def normalize_youtube_url(value: str) -> SourceIdentity:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _YOUTUBE_HOSTS:
        raise ValueError("유효한 YouTube URL이 아닙니다")

    video_id: str | None = None
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    else:
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] in {"shorts", "embed"}:
            video_id = parts[1]

    if video_id is None or _VIDEO_ID.fullmatch(video_id) is None:
        raise ValueError("YouTube 영상 ID를 찾을 수 없습니다")
    return SourceIdentity(
        source_id=f"youtube:{video_id}",
        video_id=video_id,
        canonical_url=f"https://www.youtube.com/watch?v={video_id}",
    )


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as media:
        while chunk := media.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_source(value: str, *, base_directory: Path | None = None) -> SourceIdentity:
    """Normalize a YouTube URL or an existing local audio/video file."""

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return normalize_youtube_url(value)

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (base_directory or Path.cwd()) / candidate
    candidate = candidate.resolve()
    if not candidate.is_file():
        raise SourceInputError(f"local media file not found: {candidate}")
    if candidate.suffix.lower() not in _LOCAL_MEDIA_SUFFIXES:
        raise SourceInputError(f"unsupported local media format: {candidate.suffix or '<none>'}")
    digest = _file_digest(candidate)
    return SourceIdentity(
        source_id=f"local:{digest}",
        canonical_url=candidate.as_uri(),
        kind=SourceKind.LOCAL_MEDIA,
        local_path=str(candidate),
    )


def looks_like_local_media_input(value: str) -> bool:
    """Return whether a CLI token has a supported local media extension."""

    return urlparse(value).scheme not in {"http", "https"} and (
        Path(value).suffix.lower() in _LOCAL_MEDIA_SUFFIXES
    )


def _canonical_bytes(value: BaseModel | Mapping[str, object] | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    serializable: Any = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(
        serializable,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def fingerprint(value: BaseModel | Mapping[str, object] | bytes) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()
