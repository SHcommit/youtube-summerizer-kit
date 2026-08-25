"""Pure grounding, assembly, and compatibility projection for knowledge trees."""

from __future__ import annotations

import re
from collections.abc import Iterable

from chew.core.identity import fingerprint
from chew.core.models import (
    ChapterSummary,
    Claim,
    ClaimNodeDraft,
    ConceptDraft,
    Evidence,
    GroundedClaim,
    GroundedConcept,
    GroundedKnowledgeTree,
    GroundedOccurrence,
    GroundedTimelineSection,
    GroundingDiagnostics,
    KnowledgePack,
    KnowledgeTreeDraft,
    Provenance,
    SourceIdentity,
    TimelineSectionDraft,
    TopicSummary,
    Transcript,
    ValidatedEvidenceRef,
)

_WHITESPACE = re.compile(r"\s+")


def _normalized(value: str) -> str:
    return _WHITESPACE.sub("", value).casefold()


class TreeAssembler:
    """Convert untrusted node references into a locally grounded tree."""

    def assemble(
        self,
        draft: KnowledgeTreeDraft | dict[str, object],
        *,
        raw_transcript: Transcript,
        raw_transcript_fingerprint: str,
        prepared_transcript_fingerprint: str,
    ) -> GroundedKnowledgeTree:
        parsed = KnowledgeTreeDraft.model_validate(draft)
        grounded, rejected_occurrences = self._ground_occurrences(parsed, raw_transcript)
        occurrence_by_id = {occurrence.occurrence_id: occurrence for occurrence in grounded}
        claims, unsupported_claims = self._ground_claims(parsed.claims, occurrence_by_id)
        claim_by_id = {claim.claim_id: claim for claim in claims}
        concepts, dangling_concepts = self._ground_concepts(parsed.concepts, claim_by_id, occurrence_by_id)
        sections, dangling_sections = self._ground_sections(
            parsed.timeline_sections, claim_by_id, occurrence_by_id
        )
        summary_ids = tuple(claim_id for claim_id in parsed.summary_claim_ids if claim_id in claim_by_id)
        dangling_summary = len(parsed.summary_claim_ids) - len(summary_ids)
        relations = tuple(
            relation
            for relation in parsed.relations
            if relation[0] in claim_by_id and relation[2] in claim_by_id
        )
        diagnostics = GroundingDiagnostics(
            candidate_occurrence_count=len(parsed.occurrences),
            grounded_occurrence_count=len(grounded),
            unsupported_claim_count=unsupported_claims,
            ambiguous_anchor_count=0,
            dangling_reference_count=(
                rejected_occurrences + dangling_concepts + dangling_sections + dangling_summary
            ),
        )
        content = {
            "schema_version": "gkt-v1",
            "raw_transcript_fingerprint": raw_transcript_fingerprint,
            "prepared_transcript_fingerprint": prepared_transcript_fingerprint,
            "thesis_claim_id": parsed.thesis_claim_id,
            "summary_claim_ids": summary_ids,
            "claims": [claim.model_dump(mode="json") for claim in claims],
            "occurrences": [occurrence.model_dump(mode="json") for occurrence in grounded],
            "concepts": [concept.model_dump(mode="json") for concept in concepts],
            "timeline_sections": [section.model_dump(mode="json") for section in sections],
            "relations": relations,
            "diagnostics": diagnostics.model_dump(mode="json"),
        }
        return GroundedKnowledgeTree.model_validate({**content, "fingerprint": fingerprint(content)})

    @staticmethod
    def _ground_occurrences(
        draft: KnowledgeTreeDraft, transcript: Transcript
    ) -> tuple[tuple[GroundedOccurrence, ...], int]:
        grounded: list[GroundedOccurrence] = []
        rejected = 0
        for occurrence in draft.occurrences:
            indexes = occurrence.raw_segment_indexes
            if any(index < 0 or index >= len(transcript.segments) for index in indexes):
                rejected += 1
                continue
            segments = tuple(transcript.segments[index] for index in indexes)
            searchable = " ".join(segment.text for segment in segments)
            if _normalized(occurrence.quote) not in _normalized(searchable):
                rejected += 1
                continue
            grounded.append(
                GroundedOccurrence(
                    occurrence_id=occurrence.occurrence_id,
                    raw_segment_indexes=indexes,
                    quote=occurrence.quote,
                    start_ms=segments[0].start_ms,
                    end_ms=segments[-1].end_ms,
                    context_type=occurrence.context_type,
                )
            )
        return tuple(grounded), rejected

    @staticmethod
    def _ground_claims(
        drafts: Iterable[ClaimNodeDraft], occurrences: dict[str, GroundedOccurrence]
    ) -> tuple[tuple[GroundedClaim, ...], int]:
        claims: list[GroundedClaim] = []
        unsupported = 0
        for claim in drafts:
            accepted_ids = tuple(item for item in claim.occurrence_ids if item in occurrences)
            if claim.provenance == Provenance.SOURCE and not accepted_ids:
                unsupported += 1
                continue
            if not accepted_ids:
                unsupported += 1
                continue
            claims.append(
                GroundedClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    occurrence_ids=accepted_ids,
                    provenance=claim.provenance,
                )
            )
        return tuple(claims), unsupported

    @staticmethod
    def _ground_concepts(
        drafts: Iterable[ConceptDraft], claims: dict[str, GroundedClaim], occurrences: dict[str, GroundedOccurrence]
    ) -> tuple[tuple[GroundedConcept, ...], int]:
        result: list[GroundedConcept] = []
        dangling = 0
        for concept in drafts:
            claim_ids = tuple(item for item in concept.claim_ids if item in claims)
            occurrence_ids = tuple(item for item in concept.occurrence_ids if item in occurrences)
            dangling += len(concept.claim_ids) - len(claim_ids)
            dangling += len(concept.occurrence_ids) - len(occurrence_ids)
            result.append(
                GroundedConcept(
                    concept_id=concept.concept_id,
                    title=concept.title,
                    definition=concept.definition,
                    claim_ids=claim_ids,
                    occurrence_ids=occurrence_ids,
                )
            )
        return tuple(result), dangling

    @staticmethod
    def _ground_sections(
        drafts: Iterable[TimelineSectionDraft], claims: dict[str, GroundedClaim], occurrences: dict[str, GroundedOccurrence]
    ) -> tuple[tuple[GroundedTimelineSection, ...], int]:
        result: list[GroundedTimelineSection] = []
        dangling = 0
        for section in drafts:
            claim_ids = tuple(item for item in section.claim_ids if item in claims)
            anchor_ids = tuple(item for item in section.anchor_occurrence_ids if item in occurrences)
            dangling += len(section.claim_ids) - len(claim_ids)
            dangling += len(section.anchor_occurrence_ids) - len(anchor_ids)
            result.append(
                GroundedTimelineSection(
                    section_id=section.section_id,
                    title=section.title,
                    claim_ids=claim_ids,
                    anchor_occurrence_ids=anchor_ids,
                )
            )
        result.sort(
            key=lambda section: min(
                (occurrences[item].start_ms for item in section.anchor_occurrence_ids), default=0
            )
        )
        return tuple(result), dangling


class KnowledgePackProjector:
    """Derive the existing pack schema without copying ungrounded prose."""

    def project(
        self,
        *,
        tree: GroundedKnowledgeTree,
        transcript: Transcript,
        source: SourceIdentity,
        title: str,
        language: str,
        analysis_fingerprint: str,
        runtime_id: str | None,
        model: str | None,
    ) -> KnowledgePack:
        claims = {claim.claim_id: claim for claim in tree.claims}
        occurrences = {occurrence.occurrence_id: occurrence for occurrence in tree.occurrences}
        topics: list[TopicSummary] = []
        chapters: list[ChapterSummary] = []
        for section in tree.timeline_sections:
            section_claims = tuple(
                self._project_claim(claims[item], occurrences, tree.raw_transcript_fingerprint)
                for item in section.claim_ids
            )
            summary = " ".join(claim.text for claim in section_claims)
            topic_id = f"{section.section_id}:topic"
            topics.append(TopicSummary(topic_id=topic_id, title=section.title, summary=summary, claims=section_claims))
            chapters.append(
                ChapterSummary(
                    chapter_id=section.section_id,
                    title=section.title,
                    summary=summary,
                    topic_ids=(topic_id,),
                )
            )
        if not topics:
            thesis = claims.get(tree.thesis_claim_id)
            if thesis is not None:
                projected = self._project_claim(thesis, occurrences, tree.raw_transcript_fingerprint)
                topics.append(TopicSummary(topic_id="grounded-tree-topic", title="Overview", summary=projected.text, claims=(projected,)))
                chapters.append(ChapterSummary(chapter_id="grounded-tree", title="Overview", summary=projected.text, topic_ids=("grounded-tree-topic",)))
        overview = claims.get(tree.thesis_claim_id, next(iter(claims.values()), None))
        return KnowledgePack(
            source=source,
            title=title,
            language=language,
            overview=overview.text if overview is not None else "",
            transcript_fingerprint=tree.raw_transcript_fingerprint,
            topics=tuple(topics),
            chapters=tuple(chapters),
            runtime_id=runtime_id,
            model=model,
            analysis_fingerprint=analysis_fingerprint,
            grounded_tree_fingerprint=tree.fingerprint,
        )

    @staticmethod
    def _project_claim(
        claim: GroundedClaim,
        occurrences: dict[str, GroundedOccurrence],
        raw_fingerprint: str,
    ) -> Claim:
        refs = tuple(
            ValidatedEvidenceRef(
                segment_indexes=occurrence.raw_segment_indexes,
                start_ms=occurrence.start_ms,
                end_ms=occurrence.end_ms,
                quote=occurrence.quote,
                raw_transcript_fingerprint=raw_fingerprint,
            )
            for occurrence_id in claim.occurrence_ids
            if (occurrence := occurrences.get(occurrence_id)) is not None
        )
        return Claim(
            text=claim.text,
            provenance=claim.provenance,
            evidence=tuple(Evidence(text=ref.quote, start_ms=ref.start_ms, end_ms=ref.end_ms) for ref in refs),
            evidence_refs=refs,
        )
