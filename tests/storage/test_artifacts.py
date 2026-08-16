import json
from pathlib import Path

import pytest

from ytsum.storage.artifacts import ArtifactCorruptError, ArtifactStore


def test_artifact_store_deduplicates_canonical_json(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    first = store.put_json({"b": 2, "a": 1})
    second = store.put_json({"a": 1, "b": 2})

    assert first == second
    assert store.get_json(first) == {"a": 1, "b": 2}
    assert len(list((tmp_path / "objects").rglob("*.zst"))) == 1


def test_artifact_store_rejects_corrupt_content(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    ref = store.put_json({"value": "safe"})
    store.path_for(ref).write_bytes(b"corrupt")

    with pytest.raises(ArtifactCorruptError):
        store.get_json(ref)


def test_artifact_bytes_are_canonical_before_hashing(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    ref = store.put_json({"한글": "값", "items": [2, 1]})

    assert ref.size == len(
        json.dumps(
            {"items": [2, 1], "한글": "값"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
