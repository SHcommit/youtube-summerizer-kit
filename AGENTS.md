# AI Agent Development & Architecture Guide

This document provides essential context, architectural layout, and development guidelines for AI coding agents (Antigravity, Codex CLI, Claude Code, Gemini CLI, etc.) working on `youtube-summarizer-kit`.

---

## Ports & Adapters Architecture Layout

The codebase follows the **Ports & Adapters (Hexagonal)** architecture pattern to guarantee strict separation between core synthesis logic and external AI/data adapters.

```
src/chew/
├── core/              # Layer 1: Core Domain Entities, Value Objects, Identity (SHA-256), & Prompts
│   ├── models.py      (Frozen pydantic models: SourceIdentity, Transcript, KnowledgePack, etc.)
│   ├── identity.py    (YouTube URL & local media normalization, SHA-256 fingerprinting)
│   └── prompts.py     (Core system prompt templates)
│
├── pipeline/          # Layer 2: Analysis Engine & Output Compiler
│   ├── segmentation.py (Adaptive topic & chapter transcript segmentation)
│   ├── scheduler.py    (Async DAG task scheduler & lease execution)
│   ├── engine.py       (Hierarchical topic → chapter → Knowledge Pack synthesis)
│   ├── knowledge.py    (Knowledge Pack formatting)
│   └── outputs.py      (Digest, blog, study notes, & obsidian vault compilation)
│
├── storage/           # Layer 3: Persistence Adapters
│   ├── database.py    (SQLite WAL state machine & worker claims)
│   └── artifacts.py   (Content-addressed zstd artifact storage)
│
├── harness/           # Layer 4: AI Runtime Adapters (LLM Execution Engines)
│   ├── base.py / builtin.py / registry.py
│   └── [codex, gemini, claude, ollama, layered_ollama, huggingface, antigravity].py
│
├── transcripts/       # Layer 5: Data Input Adapters (Transcripts & Speech-to-Text)
│   ├── base.py / service.py / validation.py
│   └── [youtube_api, yt_dlp, whisper].py
│
├── app/               # Layer 6: Application Service & Container Bootstrap
│   ├── service.py     (Application use-case orchestrator)
│   ├── bootstrap.py   (Dependency injection container & AutoHarness)
│   └── config.py      (Markdown-based settings loader: CHEW.md)
│
├── retention/         # Layer 7: Storage Retention & Cleanup Policies
│   └── planner.py     (Retention policy planner & cleaner)
│
├── benchmark/         # Layer 8: Quality Benchmarking Framework
│   └── runner.py      (Benchmark runner & comparison reports)
│
└── cli/               # Layer 9: Presentation Layer (Typer CLI Commands)
    └── main.py        (Bilingual Korean/English Typer commands)

reports/               # Central Benchmarking & Performance Observability Reports
├── BENCHMARK.md       (Release performance history & OpenTelemetry Jaeger setup)
├── performance_analysis.md (Baseline vs optimized commit diff comparisons)
├── trace_report.md    (Generated OpenTelemetry span execution report)
└── performance-comparisons/transcript-preprocessing/
                        (Immutable preprocessing benchmark runs + latest summary)

benchmarks/            # Maintainer-only post-feature validation scripts
├── benchmark.sh       (Friendly wrapper: report allInOne, baseline, quality, render)
├── videos.lock.json   (Canonical five-video preprocessing fixture)
└── *.py               (Metrics, quality validation, and Markdown/HTML report rendering)
```

---

## Core Rules for AI Agents

1. **Layer Dependency Direction**:
   - `core` MUST NOT import from `pipeline`, `app`, `harness`, `transcripts`, or `cli`.
   - `pipeline` orchestrates synthesis without knowing vendor LLM details.
   - `harness` adapters implement the `Harness` protocol in `harness/base.py`.
   - `transcripts` providers implement `TranscriptProvider` in `transcripts/base.py`.

2. **Backward Compatibility**:
   - Re-export modules at the package root (`src/chew/domain.py`, `src/chew/pipeline.py`, `src/chew/config.py`, `src/chew/cli.py`) MUST be maintained so tests and external entrypoints remain compatible.

3. **Single Source of Truth & Symlink Propagation**:
   - `AGENTS.md` is the single source of truth for architectural guidelines.
   - `CLAUDE.md` and `GEMINI.md` are symbolic links (`ln -s AGENTS.md`) pointing to `AGENTS.md`. Editing `AGENTS.md` updates all agent files instantly.

4. **Changelog & Documentation Synchronization**:
   - Every meaningful feature addition, CLI command change, or architectural refactoring MUST update `CHANGELOG.md` under `## [Unreleased]` and synchronize related documentation (`README.md`, `README.ko.md`).

5. **Gitflow Branching & Tag Release Strategy**:
   - Feature development MUST occur on topic branches (`feature/*`).
   - External contributors fork the repository and submit Pull Requests targeting the **`develop`** branch.
   - Completed features MUST be merged into the **`develop`** integration testing branch first. `master` is reserved strictly for tagged production releases.
   - Verified releases are merged from `develop` into `master` / `main` and tagged using Semantic Versioning (`v*.*.*`).
   - Pushing release tags (`git push origin master --tags`) triggers automated PyPI publishing and GitHub Release creation via `.github/workflows/cd.yml`.

6. **Verification Before Finishing**:
   - Always run the verification suite before declaring success:
     ```bash
     uv run --extra dev pytest
     uv run --extra dev ruff check .
     uv run --extra dev mypy src/chew
     ```

7. **Background Process & Task Lifecycle Management**:
   - AI Agents working on this codebase MUST clean up and terminate all spawned background tasks (`uv run chew`, async CLI processes, schedule timers) using `manage_task kill` immediately upon task completion, cancellation, or before responding to the user. Never leave orphan processes running in the background.

8. **No Blind Full-Disk File Scanning**:
   - AI Agents MUST NOT run recursive home-directory searches (`Path.home().glob()`, `find ~`) when locating application state or database files. Always inspect `bootstrap.py`, settings, or query the user directly.

9. **Performance Benchmarking & OpenTelemetry Trace Score Tracking**:
   - Whenever modifying pipeline segmentation, harness concurrency, or DAG execution logic, AI Agents MUST run the benchmark (`time uv run --extra youtube chew 'https://www.youtube.com/watch?v=NAumQObJEwM'`) to verify no performance regressions occurred compared to the baseline (1m 50s).
   - Use `chew benchmark-dashboard` or `chew benchmark-ui` to generate `reports/trace_report.md` and inspect real-time OpenTelemetry trace graphs in Jaeger UI at `http://localhost:16686`.
   - Before tagging a new production release, AI Agents MUST record and update the best benchmark scores table in `reports/BENCHMARK.md` (symlinked at `BENCHMARK.md`) and synchronize the latest performance reports to [GitHub Wiki](https://github.com/SHcommit/youtube-summerizer-kit/wiki).

10. **Plan-Driven Context Hygiene & Task Compacting**:
    - When executing multi-step implementation plans or sequential tasks, if subsequent sub-tasks do NOT have direct dependencies on preceding conversational context (e.g., intermediate debug logs, verbose tool outputs), AI Agents SHOULD compact or clear unnecessary context or checkpoint progress in structured artifacts (`implementation_plan.md` / `walkthrough.md`) before proceeding with independent sub-tasks to ensure token efficiency, focus, and clean execution state.

11. **Agent Documentation Index — Read First, Keep in Sync**:
    - Before exploring the codebase, read `docs/agent-index.md`. It provides a layer map, key file pointers, harness table, CLI command table, protocol signatures, and a sync checklist — all in one place.
    - Whenever you add a harness, CLI command, new layer, optional extras group, or make a schema/protocol change, you MUST update the relevant section(s) of `docs/agent-index.md` in the same commit. The sync checklist in §10 of that doc tells you exactly what to update for each change type.
    - Also keep `CHANGELOG.md` (under `## [Unreleased]`), `README.md`, and `README.ko.md` in sync as required by Rule 4.

