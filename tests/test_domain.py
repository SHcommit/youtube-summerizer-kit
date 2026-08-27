import pytest
from pydantic import ValidationError

from chew.core.models import (
    CompilerProvenance,
    ExecutionProvenance,
    InputProvenance,
    KnowledgeTreeSchemaProvenance,
    PromptProvenance,
    RunManifest,
    SoftwareProvenance,
)
from chew.domain import Claim, Provenance, SourceIdentity, Transcript, TranscriptSegment


def test_domain_models_are_immutable() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )

    with pytest.raises(ValidationError):
        source.video_id = "other"  # type: ignore[misc]


def test_transcript_rejects_segments_beyond_duration() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )

    with pytest.raises(ValidationError, match="duration"):
        Transcript(
            source=source,
            language="ko",
            duration_ms=1_000,
            provenance=Provenance.MANUAL_SUBTITLE,
            segments=(TranscriptSegment(start_ms=500, end_ms=1_500, text="내용"),),
        )


def test_source_claim_requires_timestamped_evidence() -> None:
    with pytest.raises(ValidationError, match="source claims require evidence"):
        Claim(text="영상에서 확인한 주장", provenance=Provenance.SOURCE)


def test_ai_explanation_can_be_explicitly_ungrounded() -> None:
    claim = Claim(text="AI가 추가한 설명", provenance=Provenance.AI_EXPLANATION)

    assert claim.evidence == ()


def _run_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        software=SoftwareProvenance(
            package_version="0.3.0", git_sha="deadbeef", python_version="3.12.0", lock_digest="a" * 64
        ),
        compiler=CompilerProvenance(strategy="gkt", compiler_version="gkt-v1"),
        prompt=PromptProvenance(bundle_id="unversioned", content_hash="b" * 64),
        pack_schema=KnowledgeTreeSchemaProvenance(knowledge_tree_schema_hash="c" * 64),
        execution=ExecutionProvenance(policy_version="policy-1", policy_fingerprint="d" * 64, runtime="fake"),
        inputs=InputProvenance(raw_transcript_fingerprint="e" * 64, prepared_transcript_fingerprint="f" * 64),
    )


def test_run_manifest_is_immutable() -> None:
    manifest = _run_manifest()

    with pytest.raises(ValidationError):
        manifest.run_id = "run-2"  # type: ignore[misc]


def test_run_manifest_round_trips_through_json() -> None:
    manifest = _run_manifest()

    restored = RunManifest.model_validate_json(manifest.model_dump_json())

    assert restored == manifest
