from pathlib import Path

import pytest

from ytsum.domain import SourceIdentity, SourceKind
from ytsum.identity import fingerprint, normalize_source, normalize_youtube_url


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/watch?v=abcDEF_1234",
        "https://www.youtube.com/watch?v=abcDEF_1234&list=ignored",
        "https://youtu.be/abcDEF_1234?t=10",
        "https://youtube.com/shorts/abcDEF_1234",
        "https://youtube.com/embed/abcDEF_1234",
    ],
)
def test_url_forms_share_identity(url: str) -> None:
    identity = normalize_youtube_url(url)

    assert identity.source_id == "youtube:abcDEF_1234"
    assert identity.canonical_url == "https://www.youtube.com/watch?v=abcDEF_1234"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=abcDEF_1234",
        "https://youtube.com/watch?v=short",
        "not-a-url",
    ],
)
def test_invalid_youtube_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="YouTube"):
        normalize_youtube_url(url)


def test_fingerprint_is_canonical_for_mapping_order() -> None:
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})


def test_fingerprint_accepts_models_and_bytes() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )

    assert len(fingerprint(source)) == 64
    assert len(fingerprint(Path("fixture").as_posix().encode())) == 64


def test_local_media_identity_uses_content_hash_and_resolved_locator(tmp_path: Path) -> None:
    first = tmp_path / "recording.mp3"
    second = tmp_path / "moved.mp3"
    first.write_bytes(b"same audio bytes")
    second.write_bytes(b"same audio bytes")

    first_identity = normalize_source(str(first))
    second_identity = normalize_source(str(second))

    assert first_identity.kind == SourceKind.LOCAL_MEDIA
    assert first_identity.source_id == second_identity.source_id
    assert first_identity.source_id == (
        "local:aafe9f6cb200b33109672a43c8ea1e40835484abeb0520632cdc9362ce1f58a1"
    )
    assert first_identity.local_path == str(first.resolve())
    assert first_identity.canonical_url == first.resolve().as_uri()
    assert first_identity.video_id is None


def test_relative_local_video_path_is_resolved_from_working_directory(tmp_path: Path) -> None:
    media = tmp_path / "lecture.mp4"
    media.write_bytes(b"video")

    identity = normalize_source("lecture.mp4", base_directory=tmp_path)

    assert identity.kind == SourceKind.LOCAL_MEDIA
    assert identity.local_path == str(media.resolve())


@pytest.mark.parametrize("name", ["missing.mp3", "notes.txt"])
def test_missing_or_unsupported_local_media_is_rejected(tmp_path: Path, name: str) -> None:
    if name == "notes.txt":
        (tmp_path / name).write_text("not media")

    with pytest.raises(ValueError, match="local media"):
        normalize_source(name, base_directory=tmp_path)
