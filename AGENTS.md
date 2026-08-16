# AI Agent Development & Architecture Guide

This document provides essential context, architectural layout, and development guidelines for AI coding agents (Antigravity, Codex CLI, Claude Code, Gemini CLI, etc.) working on `youtube-summarizer-kit`.

---

## Ports & Adapters Architecture Layout

The codebase follows the **Ports & Adapters (Hexagonal)** architecture pattern to guarantee strict separation between core synthesis logic and external AI/data adapters.

```
src/ytsum/
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
│   └── [codex, gemini, claude, ollama, antigravity].py
│
├── transcripts/       # Layer 5: Data Input Adapters (Transcripts & Speech-to-Text)
│   ├── base.py / service.py / validation.py
│   └── [youtube_api, yt_dlp, whisper].py
│
├── app/               # Layer 6: Application Service & Container Bootstrap
│   ├── service.py     (Application use-case orchestrator)
│   ├── bootstrap.py   (Dependency injection container & AutoHarness)
│   └── config.py      (Markdown-based settings loader: YTSUM.md)
│
├── retention/         # Layer 7: Storage Retention & Cleanup Policies
│   └── planner.py     (Retention policy planner & cleaner)
│
├── benchmark/         # Layer 8: Quality Benchmarking Framework
│   └── runner.py      (Benchmark runner & comparison reports)
│
└── cli/               # Layer 9: Presentation Layer (Typer CLI Commands)
    └── main.py        (Bilingual Korean/English Typer commands)
```

---

## Core Rules for AI Agents

1. **Layer Dependency Direction**:
   - `core` MUST NOT import from `pipeline`, `app`, `harness`, `transcripts`, or `cli`.
   - `pipeline` orchestrates synthesis without knowing vendor LLM details.
   - `harness` adapters implement the `Harness` protocol in `harness/base.py`.
   - `transcripts` providers implement `TranscriptProvider` in `transcripts/base.py`.

2. **Backward Compatibility**:
   - Re-export modules at the package root (`src/ytsum/domain.py`, `src/ytsum/pipeline.py`, `src/ytsum/config.py`, `src/ytsum/cli.py`) MUST be maintained so tests and external entrypoints remain compatible.

3. **Single Source of Truth & Symlink Propagation**:
   - `AGENTS.md` is the single source of truth for architectural guidelines.
   - `CLAUDE.md` and `GEMINI.md` are symbolic links (`ln -s AGENTS.md`) pointing to `AGENTS.md`. Editing `AGENTS.md` updates all agent files instantly.

4. **Changelog & Documentation Synchronization**:
   - Every meaningful feature addition, CLI command change, or architectural refactoring MUST update `CHANGELOG.md` under `## [Unreleased]` and synchronize related documentation (`README.md`, `README.ko.md`).

5. **Gitflow Branching & Tag Release Strategy**:
   - Feature development MUST occur on topic branches (`feature/*`).
   - Completed features are merged into the `develop` integration testing branch.
   - Verified releases are merged from `develop` into `master` / `main` and tagged using Semantic Versioning (`v*.*.*`).
   - Pushing release tags (`git push origin master --tags`) triggers automated PyPI publishing and GitHub Release creation via `.github/workflows/cd.yml`.

6. **Verification Before Finishing**:
   - Always run the verification suite before declaring success:
     ```bash
     uv run --extra dev pytest
     uv run --extra dev ruff check .
     uv run --extra dev mypy src/ytsum
     ```
