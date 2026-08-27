from __future__ import annotations

import subprocess

import pytest

import chew
from chew.core.identity import fingerprint
from chew.core.models import ExecutionPlan, KnowledgeTreeDraft
from chew.core.prompts import GKT_PROMPT_BUNDLE_ID, GKT_PROMPT_FINGERPRINT
from chew.pipeline.provenance import COMPILER_VERSION, UNKNOWN, _git_sha, benchmark_metadata, build_run_manifest


def _execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        policy_version="policy-1",
        default_runtime_id="fake",
        fallback_runtime_id="fake",
        reason="test",
        plan_fingerprint="a" * 64,
    )


def test_build_run_manifest_captures_compiler_and_prompt_provenance() -> None:
    manifest = build_run_manifest(
        run_id="run-1",
        compiler_strategy="gkt",
        execution_plan=_execution_plan(),
        runtime_id="fake",
        model="fake-model",
        raw_transcript_fingerprint="b" * 64,
        prepared_transcript_fingerprint="c" * 64,
    )

    assert manifest.run_id == "run-1"
    assert manifest.compiler.strategy == "gkt"
    assert manifest.compiler.compiler_version == COMPILER_VERSION
    assert manifest.prompt.bundle_id == GKT_PROMPT_BUNDLE_ID
    assert manifest.prompt.content_hash == GKT_PROMPT_FINGERPRINT
    assert manifest.pack_schema.knowledge_tree_schema_hash == fingerprint(KnowledgeTreeDraft.model_json_schema())
    assert manifest.execution.policy_version == "policy-1"
    assert manifest.execution.policy_fingerprint == "a" * 64
    assert manifest.execution.runtime == "fake"
    assert manifest.execution.model == "fake-model"
    assert manifest.inputs.raw_transcript_fingerprint == "b" * 64
    assert manifest.inputs.prepared_transcript_fingerprint == "c" * 64
    assert manifest.software.package_version == chew.__version__


def test_build_run_manifest_falls_back_when_execution_plan_is_none() -> None:
    manifest = build_run_manifest(
        run_id="run-1",
        compiler_strategy="gkt",
        execution_plan=None,
        runtime_id="fake",
        model=None,
        raw_transcript_fingerprint="b" * 64,
        prepared_transcript_fingerprint="c" * 64,
    )

    assert manifest.execution.policy_version == UNKNOWN
    assert manifest.execution.policy_fingerprint == ""
    assert manifest.execution.model is None


def test_build_run_manifest_schema_hash_is_stable_across_calls() -> None:
    first = build_run_manifest(
        run_id="run-1",
        compiler_strategy="gkt",
        execution_plan=_execution_plan(),
        runtime_id="fake",
        model=None,
        raw_transcript_fingerprint="b" * 64,
        prepared_transcript_fingerprint="c" * 64,
    )
    second = build_run_manifest(
        run_id="run-2",
        compiler_strategy="gkt",
        execution_plan=_execution_plan(),
        runtime_id="fake",
        model=None,
        raw_transcript_fingerprint="b" * 64,
        prepared_transcript_fingerprint="c" * 64,
    )

    assert first.pack_schema.knowledge_tree_schema_hash == second.pack_schema.knowledge_tree_schema_hash


def test_benchmark_metadata_reports_compiler_strategy_and_prompt_bundle() -> None:
    metadata = benchmark_metadata("gkt")

    assert metadata["compiler_strategy"] == "gkt"
    assert metadata["prompt_bundle"] == GKT_PROMPT_BUNDLE_ID
    assert metadata["package_version"] == chew.__version__
    assert metadata["git_sha"]


def test_benchmark_metadata_omits_prompt_bundle_for_non_gkt_strategies() -> None:
    metadata = benchmark_metadata("legacy_hierarchical")

    assert metadata["compiler_strategy"] == "legacy_hierarchical"
    assert "prompt_bundle" not in metadata


def test_git_sha_falls_back_to_unknown_when_git_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(subprocess, "run", _raise)

    assert _git_sha() == UNKNOWN
