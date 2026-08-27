from chew.core.identity import fingerprint
from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.pipeline.tree import KnowledgePackProjector, TreeAssembler


def _transcript() -> Transcript:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    return Transcript(
        source=source,
        language="en",
        duration_ms=30_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        title="Grounded fixture",
        segments=(
            TranscriptSegment(start_ms=0, end_ms=10_000, text="Latency decreased by forty percent."),
            TranscriptSegment(start_ms=10_000, end_ms=20_000, text="Retries remain bounded."),
            TranscriptSegment(start_ms=20_000, end_ms=30_000, text="This is a conclusion."),
        ),
    )


def _draft() -> dict[str, object]:
    return {
        "thesis_claim_id": "claim-1",
        "claims": [
            {
                "claim_id": "claim-1",
                "text": "Latency decreased by forty percent.",
                "occurrence_ids": ["occurrence-1"],
            },
            {
                "claim_id": "unsupported",
                "text": "Invented statement.",
                "occurrence_ids": ["missing-occurrence"],
            },
        ],
        "occurrences": [
            {
                "occurrence_id": "occurrence-1",
                "raw_segment_indexes": [0],
                "quote": "Latency decreased by forty percent.",
            }
        ],
        "concepts": [
            {
                "concept_id": "latency",
                "title": "Latency",
                "definition": "Response delay.",
                "claim_ids": ["claim-1", "missing-claim"],
                "occurrence_ids": ["occurrence-1"],
            }
        ],
        "timeline_sections": [
            {
                "section_id": "section-1",
                "title": "Result",
                "claim_ids": ["claim-1", "missing-claim"],
                "anchor_occurrence_ids": ["occurrence-1"],
            }
        ],
    }


def test_tree_assembly_drops_dangling_references_and_derives_source_time() -> None:
    transcript = _transcript()

    tree = TreeAssembler().assemble(
        _draft(),
        raw_transcript=transcript,
        raw_transcript_fingerprint=fingerprint(transcript),
        prepared_transcript_fingerprint="prepared-fingerprint",
    )

    assert tree.timeline_sections[0].claim_ids == ("claim-1",)
    assert tree.occurrences[0].start_ms == 0
    assert tree.occurrences[0].end_ms == 10_000
    assert tree.diagnostics.unsupported_claim_count == 1


def test_projector_creates_legacy_pack_with_validated_evidence() -> None:
    transcript = _transcript()
    tree = TreeAssembler().assemble(
        _draft(),
        raw_transcript=transcript,
        raw_transcript_fingerprint=fingerprint(transcript),
        prepared_transcript_fingerprint="prepared-fingerprint",
    )

    pack = KnowledgePackProjector().project(
        tree=tree,
        transcript=transcript,
        source=transcript.source,
        title="Grounded fixture",
        language="en",
        analysis_fingerprint="analysis-fingerprint",
        runtime_id="fake",
        model="fake-model",
    )

    claim = pack.topics[0].claims[0]
    assert claim.evidence_refs[0].segment_indexes == (0,)
    assert claim.evidence_refs[0].start_ms == 0
    assert pack.grounded_tree_fingerprint == tree.fingerprint


def test_projector_links_run_manifest_hash_onto_pack() -> None:
    transcript = _transcript()
    tree = TreeAssembler().assemble(
        _draft(),
        raw_transcript=transcript,
        raw_transcript_fingerprint=fingerprint(transcript),
        prepared_transcript_fingerprint="prepared-fingerprint",
    )

    pack = KnowledgePackProjector().project(
        tree=tree,
        transcript=transcript,
        source=transcript.source,
        title="Grounded fixture",
        language="en",
        analysis_fingerprint="analysis-fingerprint",
        runtime_id="fake",
        model="fake-model",
        manifest_hash="a" * 64,
    )

    assert pack.manifest_hash == "a" * 64
