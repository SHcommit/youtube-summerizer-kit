"""Compressed content-addressed artifact storage."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import zstandard
from pydantic import BaseModel


class ArtifactCorruptError(RuntimeError):
    """Raised when an artifact cannot be decoded or fails integrity checking."""


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    digest: str
    media_type: str
    size: int


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.objects = root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _canonical_json(value: BaseModel | dict[str, Any]) -> bytes:
        content = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        return json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def path_for(self, ref: ArtifactRef) -> Path:
        return self.objects / ref.digest[:2] / f"{ref.digest[2:]}.json.zst"

    def ref_for_digest(self, digest: str) -> ArtifactRef:
        return ArtifactRef(digest=digest, media_type="application/json", size=0)

    def put_json(self, value: BaseModel | dict[str, Any]) -> ArtifactRef:
        raw = self._canonical_json(value)
        ref = ArtifactRef(hashlib.sha256(raw).hexdigest(), "application/json", len(raw))
        destination = self.path_for(ref)
        if destination.is_file():
            return ref
        destination.parent.mkdir(parents=True, exist_ok=True)
        compressed = zstandard.ZstdCompressor(level=3).compress(raw)
        descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent, prefix=".artifact-")
        try:
            with os.fdopen(descriptor, "wb") as temporary:
                temporary.write(compressed)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, destination)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return ref

    def get_json(self, ref: ArtifactRef) -> dict[str, Any]:
        try:
            raw = zstandard.ZstdDecompressor().decompress(self.path_for(ref).read_bytes())
            if hashlib.sha256(raw).hexdigest() != ref.digest:
                raise ArtifactCorruptError(f"artifact hash mismatch: {ref.digest}")
            value = json.loads(raw)
        except (OSError, zstandard.ZstdError, json.JSONDecodeError) as error:
            raise ArtifactCorruptError(f"cannot read artifact: {ref.digest}") from error
        if not isinstance(value, dict):
            raise ArtifactCorruptError(f"artifact is not a JSON object: {ref.digest}")
        return value
