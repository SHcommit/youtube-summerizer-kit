# Short-Video Single-Frontier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route videos at or below 15 minutes through one Frontier synthesis call while preserving deterministic local validation and normal Knowledge Pack outputs.

**Architecture:** `AnalysisPipeline` decides the strategy after resolving the transcript. The short path uses one durable scheduler job and a dedicated strict schema; the handler materializes evidence locally and constructs a one-topic, one-chapter pack without calling chapter or compose generation.

**Tech Stack:** Python 3, Pydantic, SQLite scheduler, pytest.

## Global Constraints

- `SHORT_VIDEO_MAX_DURATION_MS` is exactly `900_000`.
- Frontier is the only semantic reasoning runtime; no local LLM route is added.
- The short path must call `short_video_summary` exactly once for a successful analysis.
- Existing long-video behavior and compatibility re-exports remain intact.

---

### Task 1: Define the short synthesis contract and strategy selection

**Files:**
- Modify: `src/chew/core/models.py`
- Modify: `src/chew/pipeline/engine.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `ShortVideoSummaryDraft`, `SHORT_VIDEO_MAX_DURATION_MS`, and `analysis_strategy_for_duration(duration_ms: int) -> str`.
- Consumes: resolved `Transcript.duration_ms`.

- [ ] **Step 1: Write failing tests**

```python
def test_short_video_strategy_includes_the_fifteen_minute_boundary() -> None:
    assert analysis_strategy_for_duration(900_000) == "single_frontier_v1"
    assert analysis_strategy_for_duration(900_001) == "hierarchical_v1"
```

Add a short-transcript pipeline test asserting only `short_video_summary` appears in harness requests.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `uv run --extra dev pytest tests/test_pipeline.py -k 'short_video' -v`

Expected: FAIL because the strategy function and short request do not exist.

- [ ] **Step 3: Add minimal contract and routing implementation**

Define `ShortVideoSummaryDraft` with `overview`, `topic_title`, `topic_summary`, `claims`, `concepts`, `examples`, and `further_study`. Resolve/cache the transcript before choosing the strategy, include it in request identity, and select the one-job graph for `single_frontier_v1`.

- [ ] **Step 4: Re-run focused tests**

Run: `uv run --extra dev pytest tests/test_pipeline.py -k 'short_video' -v`

Expected: PASS.

### Task 2: Materialize and persist the one-call Knowledge Pack

**Files:**
- Modify: `src/chew/pipeline/engine.py`
- Modify: `src/chew/core/prompts.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `ShortVideoSummaryDraft` and immutable raw transcript spans.
- Produces: regular `KnowledgePack` with one topic and one chapter.

- [ ] **Step 1: Write failing tests**

Add assertions that the short path creates one topic and chapter, preserves only validated evidence refs, stores a run pack, and never calls `chapter_summary` or `compose`.

- [ ] **Step 2: Run focused test and confirm failure**

Run: `uv run --extra dev pytest tests/test_pipeline.py -k 'short_video_single' -v`

Expected: FAIL because the short job handler has no pack materialization branch.

- [ ] **Step 3: Implement the handler branch**

Use the normal `_generate` retry/schema path for `short_video_summary`; convert its nested claims into `TopicSummaryDraft`, call `materialize_topic_summary`, derive `ChapterSummary` locally, build/store the pack, and record evidence-validation measurements.

- [ ] **Step 4: Re-run focused test**

Run: `uv run --extra dev pytest tests/test_pipeline.py -k 'short_video_single' -v`

Expected: PASS.

### Task 3: Document, verify, and commit

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `docs/agent-index.md`
- Modify: `CHANGELOG.md`
- Modify: `IMPROVEMENTS.md`
- Modify: `handoff.md`

- [ ] **Step 1: Document the 15-minute policy**

Describe single Frontier reasoning for short videos, deterministic local boundaries, and retained hierarchical behavior for longer video in English and Korean documentation.

- [ ] **Step 2: Run full verification**

Run: `uv run --extra dev pytest && uv run --extra dev ruff check . && uv run --extra dev mypy src/chew`

Expected: all commands exit 0.

- [ ] **Step 3: Commit**

Run: `git add src/chew/core/models.py src/chew/core/prompts.py src/chew/pipeline/engine.py tests/test_pipeline.py README.md README.ko.md docs/agent-index.md CHANGELOG.md IMPROVEMENTS.md handoff.md docs/superpowers/specs/2026-08-24-short-video-single-frontier-design.md docs/superpowers/plans/2026-08-24-short-video-single-frontier.md && git commit -m "feat: use one Frontier call for short videos"`
