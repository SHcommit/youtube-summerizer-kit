"""Purpose-specific compilation from canonical Knowledge Packs."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ytsum.app.config import Settings
from ytsum.core.identity import fingerprint
from ytsum.core.models import GenerationRequest, KnowledgePack, Provenance
from ytsum.harness.base import Harness
from ytsum.storage.artifacts import ArtifactCorruptError, ArtifactStore
from ytsum.storage.database import Database

OUTPUT_RECIPE_FINGERPRINT = fingerprint(
    {
        "outline_task": "output_outline",
        "compose_task": "output_compose",
        "verify_task": "output_verify",
        "schema_version": 1,
    }
)


@dataclass(frozen=True, slots=True)
class OutputManifest:
    profile: str
    cache_key: str
    files: tuple[Path, ...]


def _timestamp(milliseconds: int) -> str:
    seconds = milliseconds // 1_000
    hours, remainder = divmod(seconds, 3_600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", "-", value).strip().strip(".")
    return cleaned or "note"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".ytsum-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


class OutputCompiler:
    def __init__(
        self,
        harness: Harness | None = None,
        *,
        database: Database | None = None,
        artifacts: ArtifactStore | None = None,
    ) -> None:
        self.harness = harness
        self.database = database
        self.artifacts = artifacts

    async def compile(
        self,
        pack: KnowledgePack,
        profile: str,
        settings: Settings,
        destination: Path,
    ) -> OutputManifest:
        cache_key = fingerprint(
            {
                "pack": pack.analysis_fingerprint,
                "profile": profile,
                "instructions": settings.instructions,
                "language": settings.language,
                "depth": settings.depth,
                "runtime": settings.runtime,
                "recipe": OUTPUT_RECIPE_FINGERPRINT,
                "renderer": 1,
            }
        )
        destination.mkdir(parents=True, exist_ok=True)
        cached = self._restore_cached(cache_key, destination)
        if cached is not None:
            return OutputManifest(profile, cache_key, cached)
        if profile == "obsidian":
            files = self._render_obsidian(pack, destination)
        elif profile == "json":
            path = destination / "knowledge-pack.json"
            _atomic_write(
                path,
                json.dumps(pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
            )
            files = (path,)
        elif profile in {"blog", "study"} and self.harness is not None:
            preference = getattr(self.harness, "set_preference", None)
            if callable(preference):
                preference(settings.runtime)
            path = destination / "index.md"
            _atomic_write(path, await self._compose(pack, profile, settings, cache_key))
            files = (path,)
        else:
            path = destination / "index.md"
            _atomic_write(path, self._render_digest(pack))
            files = (path,)
        self._store_cached(cache_key, pack.source.source_id, destination, files)
        return OutputManifest(profile, cache_key, files)

    def _restore_cached(self, cache_key: str, destination: Path) -> tuple[Path, ...] | None:
        if self.database is None or self.artifacts is None:
            return None
        digest = self.database.get_cached_output(cache_key)
        if digest is None:
            return None
        try:
            payload = self.artifacts.get_json(self.artifacts.ref_for_digest(digest))
        except ArtifactCorruptError:
            return None
        entries = payload.get("files")
        if not isinstance(entries, list):
            return None
        restored: list[Path] = []
        for entry in entries:
            if not isinstance(entry, dict):
                return None
            relative = entry.get("path")
            content = entry.get("content")
            if not isinstance(relative, str) or not isinstance(content, str):
                return None
            candidate = Path(relative)
            if candidate.is_absolute() or ".." in candidate.parts:
                return None
            path = destination / candidate
            _atomic_write(path, content)
            restored.append(path)
        return tuple(restored)

    def _store_cached(
        self,
        cache_key: str,
        source_id: str,
        destination: Path,
        files: tuple[Path, ...],
    ) -> None:
        if self.database is None or self.artifacts is None:
            return
        payload = {
            "files": [
                {
                    "path": str(path.relative_to(destination)),
                    "content": path.read_text(encoding="utf-8"),
                }
                for path in files
            ]
        }
        ref = self.artifacts.put_json(payload)
        self.database.cache_output(cache_key, source_id, ref.digest)

    async def _compose(
        self, pack: KnowledgePack, profile: str, settings: Settings, trace_id: str
    ) -> str:
        assert self.harness is not None
        source = pack.model_dump(mode="json")
        outline = await self.harness.generate(
            GenerationRequest(
                request_id=f"{trace_id}:outline",
                task="output_outline",
                input={"pack": source, "profile": profile, "instructions": settings.instructions},
                output_schema={"type": "object", "required": ["sections"]},
                trace_id=trace_id,
            )
        )
        composition = await self.harness.generate(
            GenerationRequest(
                request_id=f"{trace_id}:compose",
                task="output_compose",
                input={
                    "pack": source,
                    "outline": outline.output,
                    "profile": profile,
                    "instructions": settings.instructions,
                },
                output_schema={"type": "object", "required": ["markdown"]},
                trace_id=trace_id,
            )
        )
        markdown = composition.output.get("markdown")
        if not isinstance(markdown, str):
            raise ValueError("output composer did not return markdown")
        verification = await self.harness.generate(
            GenerationRequest(
                request_id=f"{trace_id}:verify",
                task="output_verify",
                input={"pack": source, "markdown": markdown, "profile": profile},
                output_schema={"type": "object", "required": ["markdown", "valid"]},
                trace_id=trace_id,
            )
        )
        verified = verification.output.get("markdown")
        if not isinstance(verified, str):
            raise ValueError("output verifier did not return markdown")
        return verified.rstrip() + "\n"

    @staticmethod
    def _render_digest(pack: KnowledgePack) -> str:
        lines = [f"# {pack.title}", "", pack.overview, ""]
        for chapter in pack.chapters:
            lines.extend((f"## {chapter.title}", "", chapter.summary, ""))
            chapter_topics = [topic for topic in pack.topics if topic.topic_id in chapter.topic_ids]
            for topic in chapter_topics:
                lines.extend((f"### {topic.title}", "", topic.summary, ""))
                for claim in topic.claims:
                    label = {
                        Provenance.SOURCE: "Source",
                        Provenance.AI_EXPLANATION: "AI Explanation",
                        Provenance.EXTERNAL_RESEARCH: "External Research",
                    }.get(claim.provenance, claim.provenance.value)
                    timestamp = (
                        f" ({_timestamp(claim.evidence[0].start_ms)})" if claim.evidence else ""
                    )
                    lines.append(f"- [{label}] {claim.text}{timestamp}")
                if topic.claims:
                    lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_obsidian(pack: KnowledgePack, destination: Path) -> tuple[Path, ...]:
        topic_files: list[Path] = []
        links: list[str] = []
        used_names: set[str] = set()
        for topic in pack.topics:
            name = _safe_name(topic.title)
            if name in used_names:
                name = f"{name}-{_safe_name(topic.topic_id)}"
            used_names.add(name)
            path = destination / f"{name}.md"
            links.append(f"- [[{name}]]")
            _atomic_write(
                path,
                "---\n"
                f"source: {pack.source.canonical_url}\n"
                f"topic_id: {topic.topic_id}\n"
                "---\n\n"
                f"# {topic.title}\n\n{topic.summary}\n",
            )
            topic_files.append(path)
        index = destination / "index.md"
        _atomic_write(
            index,
            "---\n"
            f"source: {pack.source.canonical_url}\n"
            "---\n\n"
            f"# {pack.title}\n\n{pack.overview}\n\n## 소주제\n\n" + "\n".join(links) + "\n",
        )
        return (index, *topic_files)
