# ADR-003: RunManifest v1 as the Per-Run Provenance Snapshot

## Status

Accepted

## Context

An engineering-system audit found that answering "which git commit / package version /
prompt / schema / model produced this Knowledge Pack?" for a single run required cross-referencing
several places: the `runs` table (`recipe_json`, `execution_plan_json`), the artifact store,
`chew.core.prompts.PROMPT_FINGERPRINT`, and git history. No single artifact answered the question
for one run.

The fingerprint building blocks already existed (`chew.core.identity.fingerprint`,
`PROMPT_FINGERPRINT`, `ExecutionPlan.plan_fingerprint`) — the gap was that nothing collected them
into one queryable snapshot per run.

## Decision

Add `RunManifest` (`src/chew/core/models.py`) as a `FrozenModel` built once per GKT run by
`chew.pipeline.provenance.build_run_manifest()`, immediately before
`KnowledgePackProjector().project(...)` in `pipeline/engine.py`. It is stored through the existing
`ArtifactStore.put_json()` — no new storage mechanism — and linked from both
`KnowledgePack.manifest_hash` and `runs.manifest_hash` (schema v9).

Fields are grouped as `software`, `compiler`, `prompt`, `pack_schema`, `execution`, and `inputs`.
Every field is a version string, a strategy name, or a content fingerprint. `RunManifest` never
stores API keys, raw user input, or endpoint details, so no redaction logic is needed.

`prompt.bundle_id`/`prompt.content_hash` originally shipped as a stub pointing at
`chew.core.prompts.PROMPT_FINGERPRINT`. Tracing the actual GKT extraction call
(`pipeline/extraction.py: KnowledgeExtractor`) found that it sends no prompt template text at
all — only `task`/`input`/`output_schema` — and that `PROMPT_FINGERPRINT` covers
`TOPIC_PROMPT`/`CHAPTER_PROMPT`/`COMPOSE_PROMPT`/`REPAIR_PROMPT`, which are used only by the
legacy `legacy_hierarchical` branch. The only prompt content the live GKT path actually sends is
the shared JSON-schema-enforcement instruction in `harness/builtin.py: request_prompt()`. That
instruction was moved to `chew.core.prompts.HARNESS_JSON_INSTRUCTION` (`harness/builtin.py` now
imports it — the string value is unchanged), and `GKT_PROMPT_BUNDLE_ID = "knowledge-extract/v1"` /
`GKT_PROMPT_FINGERPRINT = fingerprint({"bundle": ..., "instruction": ...})` were added alongside
it. `RunManifest.prompt` now uses these, so `bundle_id` is a real logical ID, not a stub.

The same trace found `pack_schema.knowledge_tree_schema_hash` was fingerprinting
`KnowledgePack.model_json_schema()` — the final rendered pack — instead of
`KnowledgeTreeDraft.model_json_schema()`, the schema actually sent as `output_schema` and enforced
on the LLM's output. Fixed to fingerprint `KnowledgeTreeDraft`.

One field remains best-effort by design, not as a stub to remove:

- `software.git_sha` and `software.lock_digest`: a `pip`-installed run has no `.git` or `uv.lock`
  to read, so both fall back to `"unknown"` rather than failing the run.

The legacy `legacy_hierarchical` compiler strategy (reachable only from
`benchmark/runner.py`'s `hierarchical()` comparison condition, not from any live CLI path — see
`docs/wiki/Current-System.md`) does not build a `RunManifest`. It is a benchmark comparison path,
not a path whose provenance users need to reproduce.

## Consequences

- A quality regression or "why did this run produce a different result?" question now starts from
  one artifact (`RunManifest`) reachable from a `run_id` or `KnowledgePack`, instead of manual
  cross-referencing.
- `runs` schema moved to v9 (`manifest_hash` column); existing databases migrate automatically via
  `Database._apply_migration`.
- `software.git_sha`/`lock_digest` reporting `"unknown"` for a `pip`-installed run is expected, not
  a bug report.
- A future prompt-bundle version bump (e.g. `knowledge-extract/v2`) should update
  `GKT_PROMPT_BUNDLE_ID` and, per `docs/decisions/0002-repository-governance.md`'s AI Project
  Policy, state in the PR whether the change is behavior-preserving, behavior-changing, or
  migration-required for existing Knowledge Packs.

## Related PRs / Releases

- Introduced on `feat/engineering-knowledge`; not yet released.
