"""RunManifest v1: a read-only per-run provenance snapshot for the GKT compiler."""

from __future__ import annotations

import hashlib
import platform
import subprocess
from pathlib import Path

import chew
from chew.core.identity import fingerprint
from chew.core.models import (
    CompilerProvenance,
    ExecutionPlan,
    ExecutionProvenance,
    InputProvenance,
    KnowledgeTreeDraft,
    KnowledgeTreeSchemaProvenance,
    PromptProvenance,
    RunManifest,
    SoftwareProvenance,
)
from chew.core.prompts import GKT_PROMPT_BUNDLE_ID, GKT_PROMPT_FINGERPRINT

COMPILER_VERSION = "gkt-v1"
UNKNOWN = "unknown"

_KNOWLEDGE_TREE_SCHEMA_HASH = fingerprint(KnowledgeTreeDraft.model_json_schema())


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return UNKNOWN
    return result.stdout.strip() if result.returncode == 0 else UNKNOWN


def _lock_digest() -> str:
    lock_file = Path(__file__).resolve().parents[3] / "uv.lock"
    if not lock_file.is_file():
        return UNKNOWN
    try:
        return hashlib.sha256(lock_file.read_bytes()).hexdigest()
    except OSError:
        return UNKNOWN


def benchmark_metadata(compiler_strategy: str) -> dict[str, str]:
    """Common provenance fields for a benchmark condition's observation metadata.

    `prompt_bundle` is included only for the "gkt" strategy: legacy compiler strategies have
    no logical prompt bundle ID (only the unstructured `PROMPT_FINGERPRINT` hash), so reporting
    `GKT_PROMPT_BUNDLE_ID` for them would misattribute the prompt in use.
    """

    metadata = {
        "compiler_strategy": compiler_strategy,
        "package_version": chew.__version__,
        "git_sha": _git_sha(),
    }
    if compiler_strategy == "gkt":
        metadata["prompt_bundle"] = GKT_PROMPT_BUNDLE_ID
    return metadata


def build_run_manifest(
    *,
    run_id: str,
    compiler_strategy: str,
    execution_plan: ExecutionPlan | None,
    runtime_id: str,
    model: str | None,
    raw_transcript_fingerprint: str,
    prepared_transcript_fingerprint: str,
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        software=SoftwareProvenance(
            package_version=chew.__version__,
            git_sha=_git_sha(),
            python_version=platform.python_version(),
            lock_digest=_lock_digest(),
        ),
        compiler=CompilerProvenance(strategy=compiler_strategy, compiler_version=COMPILER_VERSION),
        prompt=PromptProvenance(bundle_id=GKT_PROMPT_BUNDLE_ID, content_hash=GKT_PROMPT_FINGERPRINT),
        pack_schema=KnowledgeTreeSchemaProvenance(knowledge_tree_schema_hash=_KNOWLEDGE_TREE_SCHEMA_HASH),
        execution=ExecutionProvenance(
            policy_version=execution_plan.policy_version if execution_plan is not None else UNKNOWN,
            policy_fingerprint=execution_plan.plan_fingerprint if execution_plan is not None else "",
            runtime=runtime_id,
            model=model,
        ),
        inputs=InputProvenance(
            raw_transcript_fingerprint=raw_transcript_fingerprint,
            prepared_transcript_fingerprint=prepared_transcript_fingerprint,
        ),
    )
