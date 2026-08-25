# Benchmark Progress Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every live benchmark condition and repeat before its external call starts.

**Architecture:** `BenchmarkRunner` emits an optional immutable progress event. The CLI renders that event immediately; result JSON and Markdown remain unchanged.

**Tech Stack:** Python, dataclasses, Typer, pytest.

## Global Constraints

- Preserve the explicit `--live` gate and deterministic condition ordering.
- Emit progress before the external runner call.
- Use a one-repeat live validation before the three-repeat final run.

### Task 1: Add runner progress events

**Files:** Modify `src/chew/benchmark/runner.py`; test `tests/test_benchmark.py`.

- [ ] Write a failing test that injects a callback, runs two repeats, and asserts events `direct 1/2` then `direct 2/2`.
- [ ] Run `uv run --extra dev pytest tests/test_benchmark.py -k progress` and confirm it fails.
- [ ] Add `BenchmarkProgress(condition_id, repeat, total_repeats)` and an optional `BenchmarkRunner` callback invoked immediately before `_observe`.
- [ ] Re-run the focused test and commit the runner change.

### Task 2: Render progress in the CLI

**Files:** Modify `src/chew/cli/main.py`; test `tests/test_benchmark.py`; update `CHANGELOG.md`, `README.md`, `README.ko.md`, `docs/agent-index.md`, and `handoff.md` if user-visible behavior changes.

- [ ] Write a failing CLI test asserting `Running <condition> repeat 1/1` appears before a saved report path.
- [ ] Run the focused test and confirm it fails.
- [ ] Pass a `typer.echo` progress callback to `BenchmarkRunner` only in `benchmark run`.
- [ ] Run `uv run --extra dev pytest && uv run --extra dev ruff check . && uv run --extra dev mypy src/chew`, then commit.

### Task 3: Validate the approved live benchmark

**Files:** No product code change; output only under `benchmark-results/`.

- [ ] Run the approved 14m34s benchmark with `--repeats 1` and confirm all three condition progress lines and report creation.
- [ ] Run the same command with `--repeats 3` only after the one-repeat run succeeds.
- [ ] Record completed behavior and the final report outcome in `CHANGELOG.md`/`handoff.md`; do not stage generated reports until reviewed.
