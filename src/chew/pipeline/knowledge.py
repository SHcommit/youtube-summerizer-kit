"""Construction of the canonical reusable Knowledge Pack."""

from __future__ import annotations

from chew.core.identity import fingerprint
from chew.core.models import ChapterSummary, KnowledgePack, MissingRange, SourceIdentity, TopicSummary


def build_knowledge_pack(
    *,
    source: SourceIdentity,
    title: str,
    language: str,
    overview: str,
    transcript_fingerprint: str,
    topics: tuple[TopicSummary, ...],
    chapters: tuple[ChapterSummary, ...],
    further_study: tuple[str, ...] = (),
    failed_topic_ids: tuple[str, ...] = (),
    missing_ranges: tuple[MissingRange, ...] = (),
    runtime_id: str | None = None,
    model: str | None = None,
) -> KnowledgePack:
    content: dict[str, object] = {
        "source": source.model_dump(mode="json"),
        "title": title,
        "language": language,
        "overview": overview,
        "transcript_fingerprint": transcript_fingerprint,
        "topics": [topic.model_dump(mode="json") for topic in topics],
        "chapters": [chapter.model_dump(mode="json") for chapter in chapters],
        "further_study": list(further_study),
        "failed_topic_ids": list(failed_topic_ids),
        "missing_ranges": [item.model_dump(mode="json") for item in missing_ranges],
        "runtime_id": runtime_id,
        "model": model,
    }
    return KnowledgePack(
        source=source,
        title=title,
        language=language,
        overview=overview,
        transcript_fingerprint=transcript_fingerprint,
        topics=topics,
        chapters=chapters,
        further_study=further_study,
        completion_status="partial" if failed_topic_ids else "complete",
        failed_topic_ids=failed_topic_ids,
        missing_ranges=missing_ranges,
        runtime_id=runtime_id,
        model=model,
        analysis_fingerprint=fingerprint(content),
    )
