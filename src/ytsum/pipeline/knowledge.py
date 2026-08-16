"""Construction of the canonical reusable Knowledge Pack."""

from __future__ import annotations

from ytsum.core.identity import fingerprint
from ytsum.core.models import ChapterSummary, KnowledgePack, SourceIdentity, TopicSummary


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
        analysis_fingerprint=fingerprint(content),
    )
