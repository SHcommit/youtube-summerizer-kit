# Benchmark Display Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render human-readable language-and-duration labels for benchmark videos without changing their persisted keys.

**Architecture:** Keep fixture keys as the sole comparison identity. Add a pure presentation helper in `benchmarks/render_report.py`, then call it at Markdown, HTML table, and Plotly chart rendering boundaries.

**Tech Stack:** Python 3, pytest, Plotly.

## Global Constraints

- Do not change `benchmarks/videos.lock.json`, saved metrics, quality references, or key-based comparison behavior.
- Known labels use `English`/`Korean` and compact durations such as `2h 00m` and `4m 35s`.
- Unknown/malformed keys must render as their original key.

---

### Task 1: Add and verify display-label rendering

**Files:**
- Modify: `tests/test_benchmark_foundation.py`
- Modify: `benchmarks/render_report.py`

**Interfaces:**
- Produces: `display_video_label(key: str) -> str`
- Consumes: each report video row's existing `key` field.

- [ ] **Step 1: Write the failing tests**

```python
def test_display_video_label_uses_language_and_duration() -> None:
    assert render_report.display_video_label("youtube_en_2h00m09s_for_benchmark") == "English · 2h 00m"
    assert render_report.display_video_label("youtube_ko_45m46s_for_benchmark") == "Korean · 45m 46s"
    assert render_report.display_video_label("custom-video") == "custom-video"
```

Also extend the existing report rendering test with a `youtube_en_4m35s_for_benchmark` row and assert `English · 4m 35s` appears in both Markdown and HTML.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run --extra dev pytest tests/test_benchmark_foundation.py -k 'display_video_label or renders_previous_current' -v`

Expected: FAIL because `display_video_label` does not exist and the report still contains the internal fixture key.

- [ ] **Step 3: Write the minimal implementation**

```python
def display_video_label(key: str) -> str:
    # Parse only the stable catalog key shape; preserve unknown historical keys.
    ...
```

Use it for the Markdown results column, the HTML comparison table, and the `x` values of token and latency Plotly figures. Keep each row's `key` intact for all data operations.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `uv run --extra dev pytest tests/test_benchmark_foundation.py -k 'display_video_label or renders_previous_current' -v`

Expected: PASS.

- [ ] **Step 5: Run project verification**

Run: `uv run --extra dev pytest && uv run --extra dev ruff check . && uv run --extra dev mypy src/chew`

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

Run: `git add benchmarks/render_report.py tests/test_benchmark_foundation.py docs/superpowers/specs/2026-08-24-benchmark-display-labels-design.md docs/superpowers/plans/2026-08-24-benchmark-display-labels.md && git commit -m "fix: simplify benchmark video labels"`
