# Grounded Knowledge Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default hierarchical Frontier DAG with a checkpointed Grounded Knowledge Tree compiler that normally uses one Frontier request and renders every default output locally.

**Architecture:** Immutable core models distinguish untrusted extraction from trusted grounded evidence. Pipeline adapters compile a reversible prepared transcript, optionally apply one bounded Ollama annotation, extract once or refine twice only when static input budget requires it, ground locally, project to the compatible Knowledge Pack, and render without a harness. Existing SQLite, artifacts, telemetry, and legacy graph stay behind adapters.

**Tech Stack:** Python 3.12, Pydantic v2, SQLite WAL, zstd artifacts, pytest, Ruff, mypy, optional Ollama and LangGraph.

## Global Constraints

- `core` imports no pipeline, app, harness, transcript, CLI, storage, or LangGraph code.
- Raw transcript data/fingerprint is immutable and trusted citations must use raw segment IDs with locally derived timestamps.
- Normal compilation issues exactly one successful Frontier semantic call; over-budget compilation issues at most two, with no repair or topic/chapter fan-out.
- Ollama is one already-installed configured model, gets one cleanup-annotation batch at most, and cannot generate claims, summaries, or replacement prose.
- Digest, blog, study, JSON, and Obsidian default renderers make no model calls.
- Preserve package-root compatibility exports, canonical SQLite/artifact boundaries, and legacy benchmark strategy.
- Do not run a live Frontier benchmark until the final pre-deployment gate.

---

### Task 1: Tree models, grounding, assembly, and compatible projection

**Files:**
- Modify: `src/chew/core/models.py`, `src/chew/core/__init__.py`, `src/chew/domain.py`
- Create: `src/chew/pipeline/tree.py`
- Modify: `src/chew/pipeline/__init__.py`, `src/chew/pipeline.py`
- Test: `tests/test_domain.py`, `tests/test_tree.py`

**Interfaces:**
- Produces `KnowledgeTreeDraft`, `GroundedKnowledgeTree`, `TreeAssembler.assemble(...)`, and `KnowledgePackProjector.project(...)`.
- A trusted occurrence has `raw_segment_indexes: tuple[int, ...]`, `quote`, `start_ms`, and `end_ms`; a tree has deterministic diagnostics and fingerprint.

- [ ] **Step 1: Write failing domain and projection tests**

```python
def test_tree_assembler_rejects_ambiguous_and_dangling_references() -> None:
    tree = TreeAssembler().assemble(valid_draft(), raw_transcript=transcript())
    assert tree.timeline_sections[0].claim_ids == ("claim-1",)
    assert tree.diagnostics.unsupported_claim_count == 1

def test_projector_preserves_legacy_evidence_contract() -> None:
    pack = KnowledgePackProjector().project(tree=grounded_tree(), transcript=transcript())
    assert pack.topics[0].claims[0].evidence_refs[0].segment_indexes == (0,)
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run --extra dev pytest tests/test_tree.py tests/test_domain.py -v`

Expected: FAIL because tree types and projector do not exist.

- [ ] **Step 3: Add frozen draft/trusted models and pure assembler**

```python
class KnowledgeTreeDraft(FrozenModel):
    schema_version: str = "gkt-draft-v1"
    thesis: ClaimNodeDraft
    claims: tuple[ClaimNodeDraft, ...]
    occurrences: tuple[OccurrenceDraft, ...]
    concepts: tuple[ConceptDraft, ...] = ()
    timeline_sections: tuple[TimelineSectionDraft, ...] = ()

class TreeAssembler:
    def assemble(self, draft: KnowledgeTreeDraft, *, raw_transcript: Transcript,
                 raw_transcript_fingerprint: str,
                 prepared_transcript_fingerprint: str) -> GroundedKnowledgeTree: ...
```

Validate raw segment IDs before quote matching; search only the raw neighborhood; derive time from the first/last accepted segment. Fuzzy matching may locate a candidate but never establishes trust; reject non-unique matches. Remove dangling IDs, sort sections by grounded time, merge only identical claim/evidence pairs, and expose coverage/ambiguity/unsupported diagnostics.

- [ ] **Step 4: Implement versioned compatibility projection**

```python
class KnowledgePackProjector:
    def project(self, *, tree: GroundedKnowledgeTree, transcript: Transcript,
                source: SourceIdentity, title: str, language: str,
                analysis_fingerprint: str, runtime_id: str | None,
                model: str | None) -> KnowledgePack: ...
```

Derive legacy topics, chapters, claims, and `ValidatedEvidenceRef` values. Add only defaulted optional tree metadata to `KnowledgePack` so old artifacts remain valid.

- [ ] **Step 5: Run and commit**

Run: `uv run --extra dev pytest tests/test_tree.py tests/test_domain.py -v`

Expected: PASS.

```bash
git add src/chew/core src/chew/domain.py src/chew/pipeline tests/test_tree.py tests/test_domain.py
git commit -m "feat: add grounded knowledge tree domain"
```

### Task 2: Reversible input compiler and one-shot local annotation

**Files:**
- Create: `src/chew/pipeline/input_compiler.py`, `src/chew/pipeline/annotation.py`
- Modify: `src/chew/core/models.py`, `src/chew/pipeline/policy.py`, `src/chew/harness/base.py`, `src/chew/app/service.py`, `src/chew/app/bootstrap.py`
- Test: `tests/test_input_compiler.py`, `tests/test_annotation.py`, `tests/test_policy.py`

**Interfaces:**
- `InputCompiler.compile(transcript, InputBudget) -> PreparedTranscript`
- `TranscriptAnnotator.annotate(prepared, plan) -> AnnotationResult`
- `ExecutionPlan.runtime_for_role("knowledge_extract" | "transcript_annotate" | "style_render") -> str`

- [ ] **Step 1: Write failing reversibility and fallback tests**

```python
def test_prepared_paragraphs_keep_stable_raw_segment_mapping() -> None:
    prepared = InputCompiler().compile(raw, InputBudget(max_input_tokens=1000, reserved_output_tokens=100))
    assert prepared.paragraphs[0].raw_segment_indexes == (0, 1)
    assert "not" in prepared.render_for_frontier()

async def test_rejected_ollama_sidecar_restores_baseline() -> None:
    result = await TranscriptAnnotator(invalid_ollama()).annotate(prepared, plan)
    assert result.accepted is False
    assert result.prepared == prepared
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run --extra dev pytest tests/test_input_compiler.py tests/test_annotation.py tests/test_policy.py -v`

Expected: FAIL because compiler, role routes, and annotator do not exist.

- [ ] **Step 3: Implement fixed-order deterministic preparation**

Validate/sort ranges; remove overlapping automatic-caption edge duplication; separate allowlisted non-speech markers; remove standalone fillers only; normalize whitespace/Unicode; then group bounded paragraphs. Preserve protected number/unit/negation/proper-name/code-like spans. Give every paragraph stable IDs and raw mappings, calculate prompt + schema + reserve token estimate, and include compiler/schema version in the prepared fingerprint.

- [ ] **Step 4: Implement closed sidecar and policy**

```python
class AnnotationAction(StrEnum):
    DROP_FILLER = "DROP_FILLER"
    DROP_DUPLICATE = "DROP_DUPLICATE"
    MARK_BOUNDARY = "MARK_BOUNDARY"
    MARK_LOW_CONFIDENCE = "MARK_LOW_CONFIDENCE"
```

Allow a single bounded candidate batch. Reject the entire sidecar for unknown IDs, invalid schema/action, protected-span changes, timeout, deletion-limit violation, >5% token expansion, or policy mismatch. No local retry/repair. Local annotation must never change the selected Frontier extractor route or extraction call allowance.

- [ ] **Step 5: Run and commit**

Run: `uv run --extra dev pytest tests/test_input_compiler.py tests/test_annotation.py tests/test_policy.py -v`

Expected: PASS.

```bash
git add src/chew/core/models.py src/chew/pipeline/input_compiler.py src/chew/pipeline/annotation.py src/chew/pipeline/policy.py src/chew/harness src/chew/app tests
git commit -m "feat: prepare reversible transcript inputs"
```

### Task 3: Bounded extraction pipeline, artifacts, checkpoints, and trace

**Files:**
- Create: `src/chew/pipeline/extraction.py`
- Modify: `src/chew/core/prompts.py`, `src/chew/pipeline/engine.py`, `src/chew/storage/database.py`, `src/chew/telemetry.py`, `src/chew/app/service.py`
- Test: `tests/test_extraction.py`, `tests/test_pipeline.py`, `tests/storage/test_database.py`, `tests/test_telemetry.py`

**Interfaces:**
- `KnowledgeExtractor.extract(prepared, spec, plan, trace_id) -> ExtractionResult`
- Compiler checkpoints are keyed by `(run_id, stage, attempt)`; unknown provider acceptance maps to `external_outcome_unknown`.

- [ ] **Step 1: Write call-budget and resume-safety tests**

```python
async def test_in_budget_path_uses_exactly_one_frontier_call() -> None:
    result = await extractor.extract(prepared_that_fits(), spec, plan, "run-1")
    assert harness.tasks == ["knowledge_extract"]
    assert result.call_strategy == "single_pass"

async def test_invalid_output_does_not_issue_repair_call() -> None:
    with pytest.raises(ExtractionValidationError):
        await extractor.extract(prepared_that_fits(), spec, plan, "run-1")
    assert harness.tasks == ["knowledge_extract"]

async def test_unknown_provider_outcome_is_not_resubmitted_by_resume() -> None:
    await pipeline.analyze(url, config)
    assert database.get_run_state(run_id) == "external_outcome_unknown"
    assert harness.calls == 1
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run --extra dev pytest tests/test_extraction.py tests/test_pipeline.py tests/storage/test_database.py tests/test_telemetry.py -v`

Expected: FAIL because extraction strategy and compiler checkpoints do not exist.

- [ ] **Step 3: Implement strict one/two-call extraction**

Use provider-native structured `KnowledgeTreeDraft` output. If prepared input fits the selected static budget, issue exactly one `knowledge_extract` request. If it does not, issue at most `knowledge_extract_outline` and `knowledge_extract_refine`, both keyed to stable paragraph IDs; reject any plan allowing a third semantic call. Local parse normalization can recover syntax but invalid schema/semantics must create a failed checkpoint without automatic Frontier repair.

- [ ] **Step 4: Make GKT the default engine strategy**

Compile/store raw and prepared transcript artifacts, run eligible annotation once, extract, ground, assemble, project, and persist the compatible pack. Cache identity includes raw/prepared fingerprints, compiler/schema versions, analysis spec, runtime/model, call strategy, policy, and accepted sidecar fingerprint. Keep `build_analysis_job_graph` and the old handler behind the explicit `legacy_hierarchical` benchmark strategy only; default must create no topic/chapter/compose jobs.

- [ ] **Step 5: Add additive checkpoint migration and redacted spans**

Add `compiler_checkpoints(run_id, stage, attempt, artifact_hash, measurement_json, policy_fingerprint, correlation_id, completed_at)`. Checkpoint each successful stage: `acquiring -> compiling -> local_optimizing -> ready_for_frontier -> frontier_running -> grounding -> assembling -> rendering -> completed`. Persist uncertain acceptance as `external_outcome_unknown`; only explicit retry makes a new attempt. Emit redacted `workflow.run`, `transcript.acquire`, `input.compile`, `local.optimize`, `frontier.generate`, `evidence.ground`, `tree.assemble`, and `output.render` spans.

- [ ] **Step 6: Run and commit**

Run: `uv run --extra dev pytest tests/test_extraction.py tests/test_pipeline.py tests/storage/test_database.py tests/test_telemetry.py -v`

Expected: PASS.

```bash
git add src/chew/core/prompts.py src/chew/pipeline src/chew/storage/database.py src/chew/telemetry.py src/chew/app/service.py tests
git commit -m "feat: compile grounded trees with bounded frontier calls"
```

### Task 4: Deterministic default rendering and optional agent plane

**Files:**
- Modify: `src/chew/pipeline/outputs.py`, `src/chew/core/models.py`, `pyproject.toml`, `src/chew/app/bootstrap.py`, `src/chew/app/service.py`
- Create: `src/chew/agents/__init__.py`, `src/chew/agents/policy.py`, `src/chew/agents/tools.py`, `src/chew/agents/session_graph.py`
- Test: `tests/test_outputs.py`, `tests/agents/test_policy.py`, `tests/agents/test_session_graph.py`

**Interfaces:**
- `OutputCompiler.compile(pack, profile, settings, destination)` makes zero default harness calls.
- Optional `SessionGraph` uses typed `read_tree`, `search_evidence`, and `render_tree` application tools only.

- [ ] **Step 1: Write zero-model renderer and agent-boundary tests**

```python
async def test_all_default_profiles_render_without_harness_calls(tmp_path: Path) -> None:
    harness = OutputHarness()
    for profile in ("digest", "blog", "study", "json", "obsidian"):
        await OutputCompiler(harness).compile(pack(), profile, Settings(), tmp_path / profile)
    assert harness.tasks == []

def test_agent_policy_forbids_recursive_dispatch_and_unapproved_publish() -> None:
    with pytest.raises(ValueError):
        AgentExecutionPolicy(tools=("dispatch_agent",))
    assert policy.requires_approval("publish_approved")
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run --extra dev pytest tests/test_outputs.py tests/agents -v`

Expected: FAIL because blog/study use compose calls and the optional agent package is missing.

- [ ] **Step 3: Replace default output composition with local renderers**

Remove `_compose` from normal profiles. Render blog/study from ordered chapters, concepts, claims, evidence, and partial-status data; retain atomic writes/cache restore. Cache by tree/pack fingerprint and `RenderSpec`, not runtime or output verification. Define but do not auto-enable a bounded local `StyleRenderer` contract over grounded claim IDs/citation placeholders.

- [ ] **Step 4: Add isolated optional LangGraph adapter**

Add `agents = ["langgraph>=0.2"]`; import it lazily only in the optional adapter. Fix per-agent steps, calls, deadline, readable/writable artifact scope, tool allowlist, and approval requirements before invocation. Initial bounded graph reads/renders a completed tree only. It has a separate checkpointer and correlation IDs; it never receives a DB connection, artifact path, shell, browser, cookies, credentials, raw evidence mutation, recursive dispatch, or automatic external write.

- [ ] **Step 5: Run and commit**

Run: `uv run --extra dev pytest tests/test_outputs.py tests/agents -v`

Expected: PASS; use `pytest.importorskip("langgraph")` where dependency execution is required.

```bash
git add src/chew/pipeline/outputs.py src/chew/core/models.py src/chew/agents src/chew/app pyproject.toml tests
git commit -m "feat: render grounded packs and isolate agents"
```

### Task 5: Benchmark compatibility, documentation lifecycle, and verification

**Files:**
- Modify: `src/chew/benchmark/metrics.py`, necessary `benchmarks/` scripts, `CHANGELOG.md`, `README.md`, `README.ko.md`, `docs/agent-index.md`, `IMPROVEMENTS.md`, `handoff.md`
- Create: `docs/wiki/grounded-knowledge-tree.md`
- Test: `tests/test_benchmark.py`, `tests/test_benchmark_metrics.py`

- [ ] **Step 1: Write failing offline measurement tests**

```python
def test_gkt_measurement_reports_comparable_strategy_and_grounding_metrics() -> None:
    row = normalize_measurement(raw_measurement)
    assert row["strategy"] == "gkt_deterministic"
    assert {"frontier_call_count", "grounding_coverage", "ambiguous_anchors"} <= row.keys()
```

- [ ] **Step 2: Run focused tests**

Run: `uv run --extra dev pytest tests/test_benchmark.py tests/test_benchmark_metrics.py -v`

Expected: FAIL only if named strategy/measurement fields are absent.

- [ ] **Step 3: Add offline-compatible reporting and synchronize docs**

Keep fixture URLs and human-reference validation unchanged. Report separate `legacy_hierarchical`, `gkt_deterministic`, and `gkt_ollama_assisted` conditions with provider usage, calls, stage latency, grounding/timestamp metrics, unsupported claims, duplicates, memory, and pause/resume result. Record completed implementation in `CHANGELOG.md`, remove it from `IMPROVEMENTS.md`, keep independent reference approval/final live benchmark active, update README files and agent index, create a durable wiki operational note, and refresh the concise handoff.

- [ ] **Step 4: Run full required verification**

Run: `uv run --extra dev pytest`

Expected: all tests pass, optional dependency tests skipped only where appropriate.

Run: `uv run --extra dev ruff check .`

Expected: `All checks passed!`

Run: `uv run --extra dev mypy src/chew`

Expected: `Success: no issues found`.

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md README.md README.ko.md docs/agent-index.md docs/wiki/grounded-knowledge-tree.md IMPROVEMENTS.md handoff.md benchmarks src/chew/benchmark tests
git commit -m "docs: record grounded compiler adoption gates"
```

Do not execute a live end-to-end Frontier run here. It remains the final pre-deployment gate after independently reviewed JSON references and all behavior/policy termination work are complete.

## Plan Self-Review

- Spec coverage: Tasks 1–3 implement models, reversible input, optional local annotation, bounded extraction, grounding, projection, persistence, resume safety, and tracing. Task 4 adds zero-call renderers and the isolated optional agents plane. Task 5 preserves benchmark and documentation obligations.
- Placeholder scan: All implementation actions specify files, interfaces, tests, and bounds; later arbitrary styles/agents are represented by explicit constrained contracts.
- Type consistency: `PreparedTranscript -> TranscriptAnnotator/KnowledgeExtractor -> KnowledgeTreeDraft -> TreeAssembler -> GroundedKnowledgeTree -> KnowledgePackProjector -> OutputCompiler`.

