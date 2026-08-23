# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Documentation Lifecycle**:
  - Defined canonical roles for active improvements, completed history, deferred product opportunities, and temporary handoffs in `AGENTS.md`.
  - Added a concise `handoff.md` execution index for current priorities without duplicating roadmaps or completed history.
- **Product Roadmap**:
  - Added `PRODUCT_ROADMAP.md` to separate deferred product opportunities from active technical improvements.
- **Evidence integrity and Frontier-first execution policy**:
  - Topic-model citations are parsed as untrusted candidates and become canonical evidence only after deterministic raw-transcript segment, timestamp, and quote validation.
  - Runs persist an immutable `ExecutionPlan` snapshot and each generation attempt records its policy fingerprint; model output cannot alter routing or token limits.
  - The default logical runtime is now `frontier`, which selects only Codex, Gemini, or Claude. Ollama remains explicit opt-in and falls back to the configured Frontier runtime when unavailable.
  - Adds deterministic Evidence/Policy test coverage, pull-request dependency review, and a built-wheel CLI smoke test in the release workflow.
- **Reproducible preprocessing token-baseline spike**:
  - Adds `scripts/spike_token_baseline.py`, a maintainer-only raw-caption measurement tool backed by the locked benchmark video set.
  - It records `cl100k_base` token counts, bilingual filler density, source provenance, duration verification, and current topic-segmentation counts without invoking an LLM.
- **Opt-in transcript preprocessing pipeline**:
  - Adds composable local preprocessing strategies: conservative filler removal, optional punctuation restoration, and optional semantic boundary detection.
  - `preprocess_transcript: true` preserves the preprocessed artifact separately, exposes estimated token savings in CLI output, and includes the preprocessing recipe in analysis cache identity.
- **Expanded generation-attempt profiling**:
  - SQLite schema v6 records each request's input characters, segment count, output-schema characters, repair flag, and retry flag alongside provider usage and duration fields.
  - Adds `scripts/report_job_measurements.py` to render per-run, read-only profiling reports without treating structural estimates as billing tokens.
- **Explicit opt-in task runtime routing**:
  - `task_runtimes` routes only explicitly named tasks to a user-selected BYOK runtime; all other tasks retain the configured default runtime and no provider is auto-switched.
- **Local LLM Runtime Decision Record**:
  - Documents that local Open LLM and Ollama are optional user choices, not a required product dependency.
- **Ollama request measurements and opt-in token-budget segmentation**:
  - Persists each generation attempt, including JSON repairs, against its SQLite job with runtime, model, provider-reported token counts, and available Ollama duration fields.
  - Adds `max_input_tokens` and `reserved_output_tokens` to `CHEW.md`; when configured, topic segmentation preserves the time boundary while preventing overlap from exceeding the explicit input budget.
  - Adds selected single-model identity to the analysis cache key so changing an Ollama model does not reuse an incompatible Knowledge Pack.
  - Marks Knowledge Packs with failed topic IDs and missing timestamp ranges; digest output visibly labels partial results.
  - Adds opt-in `output_verify: false` for blog/study output compilation; the default still performs outline, compose, and verification.
  - Adds opt-in `normalize_transcript: true`, preserving the raw transcript while analyzing a separately stored normalized artifact.
  - Routes layered-Ollama repairs to the failed task's tier rather than always downgrading to the smallest model.
  - `chew config --init` now offers an interactive Qwen3 4B / 8B / later choice and downloads a model only after confirmation.
- **`HuggingFaceHarness` and `LayeredOllamaHarness`** (§7-6, §7-7):
  - `HuggingFaceHarness`: free-tier hosted inference via HuggingFace Inference API (`huggingface_hub`); authenticates with `HF_TOKEN` env var.
  - `LayeredOllamaHarness`: routes pipeline tasks across three quantized Ollama model tiers (1.5B / 7B / 14B) based on task type (`topic_summary` → layer1, `chapter_summary` → layer2, `output_compose` → layer3).
- **Exponential Backoff with Full Jitter** (§6-1):
  - `_backoff_sleep()` in `scheduler.py` applies Full Jitter (random uniform between 0 and cap) so concurrent retrying workers do not retry in lock-step.
- **CLI Token Usage Display** (§6-2):
  - `CommandResult.usage` captures prompt and completion token counts from structured harness output.
  - Synthesis commands print a token-usage summary line after each run.
- **asyncio.Event-Driven Scheduler Polling** (§2-3):
  - Replaced busy-wait polling loop with `asyncio.Event` push notification, eliminating redundant wake-cycles and reducing CPU usage at idle.
- **Partial Failure: Topic Jobs Are Non-Terminal** (§7-3):
  - A topic job that exhausts its retry budget is marked `failed_runtime` instead of aborting the entire run. Chapter synthesis proceeds with the remaining completed topics.
- **SpanRecord Memory Cap** (§9-5):
  - `SpanRecord` accumulator in `telemetry.py` switched from an unbounded list to `collections.deque(maxlen=10_000)`, preventing memory growth on long-running pipelines.
- **Quantized Model Tag Pinning for `LayeredOllamaHarness`** (§7-7):
  - Module-level constants `LAYER1_MODEL`, `LAYER2_MODEL`, `LAYER3_MODEL` pin reproducible `q4_K_M` quantized tags (`qwen2.5:1.5b-instruct-q4_K_M`, `qwen2.5:7b-instruct-q4_K_M`, `qwen2.5:14b-instruct-q4_K_M`).
- **`chew doctor` Install Hints** (§9-10):
  - When a runtime is unavailable, `chew doctor` now prints a `→ Install: <command>` hint for all 7 supported runtimes (codex, gemini, ollama, layered_ollama, huggingface, antigravity, claude).
- **FastAPI Health & Readiness Server + `chew serve`** (§7-5):
  - New `src/chew/server.py` module exposes `/health` (always 200) and `/readiness` (200/503 with database `checks` dict) HTTP endpoints via FastAPI/uvicorn.
  - New `chew serve [--host HOST] [--port PORT]` CLI command starts the health server.
  - Optional extras group: `pip install 'chew[server]'` installs `fastapi>=0.111` and `uvicorn[standard]>=0.29`.
- **Fault Injection Test Suite** (§9-11):
  - `test_rate_limit_recovery_after_10_consecutive_successes`: verifies two halving events collapse the limit to 1 and 10 consecutive successes restore it.
  - `test_concurrent_db_writers_wal_integrity`: 10 threads writing via separate `Database` instances simultaneously do not corrupt the SQLite WAL database.
  - `test_partial_failure_with_forty_topics`: 40-topic run with 3 permanently failing topics completes without raising; chapter still runs.
  - `test_service_converts_harness_auth_error_to_authentication_required`: verifies `ApplicationService.generate()` converts `HarnessAuthenticationError` to `AuthenticationRequired`.
- **Agent Documentation Index** (`docs/agent-index.md`):
  - Lightweight LLM-readable wiki indexing project structure, key interfaces, runtime adapters, CLI commands, and sync rules for AI agents.

### Added
- **AI Agent Context Hygiene & Task Compacting Guidelines**:
  - Added Rule 10 to `AGENTS.md` (and symlinked `CLAUDE.md`, `GEMINI.md`) specifying plan-driven context hygiene and task compacting for independent sub-tasks to improve token efficiency and execution focus.

### Added
- **20-Year Senior IT/Staff Engineer Technical & Operational Evaluation**:
  - Comprehensive architectural and operational readiness assessment added to `IMPROVEMENTS.md` covering 8 core dimensions (Observability, Graceful Shutdown, Retry & Idempotency, Resource Management, Release Management, Getting Started UX, Harness Architecture, and Fault Injection Testing).
  - Defined 11 actionable operational debt tasks (§9) including Structured Logging (`structlog`), Graceful Shutdown signal handling, SQLite connection caching, and Ollama HTTP session reuse.


### Added
- **Multi-Channel Package Manager Support (`Homebrew`, `pipx`, `uv tool`, `pip`)**:
  - Added 1-line installation instructions for Homebrew (`brew install SHcommit/tap/chew`), `pipx`, `uv tool`, and `pip` in `README.md` and `README.ko.md`.
  - Added automated Homebrew Tap formula sync step to CD release workflow.

## [0.1.1] - 2026-08-17

### Fixed
- **CI/CD Workflow & Telemetry Import Fix**:
  - Added `telemetry` extra dependencies (`pip install '.[youtube,dev,telemetry]'`) to GitHub Actions CI and CD workflows.
  - Added write permissions (`permissions: contents: write`) and token authentication URL to GitHub Wiki auto-sync workflow (`wiki-sync.yml`).
  - Removed obsolete `.github/workflows/codeql.yml` to prevent 403 Forbidden failure email notifications on private repositories.

### Added
- **Core Refactoring (`ytsum` -> `chew`)**:
  - Renamed internal Python package directory from `src/ytsum` to `src/chew` and updated all module import namespaces (`chew.*`).
  - Standardized CLI output directories to `chew-output`, `chew-blog`, `chew-study`, and `chew-vault`.
  - Added support for `CHEW.md` project configuration files.
- **Performance Optimization & Dynamic Chapter Coalescing**:
  - Dynamic chapter coalescing (`coalesce_chapters`): Automatically merges excessive auto-generated YouTube chapters based on video duration (e.g. max 5 topics for videos < 30 mins), reducing total pipeline jobs by 82% (from 61 jobs to 11 jobs).
  - High Concurrency CLI Harnesses: Increased `maximum_concurrency` from 2 to 8 for `AntigravityHarness`, `CodexHarness`, and `ClaudeHarness`, accelerating parallel DAG task execution by over 16x (reducing total synthesis time from 30+ minutes down to 1 minute 50 seconds).
  - Resilient `compose` validation: Added soft fallback parsing for `overview` and `further_study` fields, preventing schema validation failures during final Knowledge Pack synthesis.
  - Agent Privacy Enforcement: Added Rule 8 in `AGENTS.md` strictly prohibiting full-disk recursive file scanning (`glob`).
- **3-Language Priority Transcript Acquisition & Fallback**:
  - Priority acquisition for Korean (`ko`), English (`en`), and Japanese (`ja`) captions with automatic fallback to any available caption track when exact requested language track is not directly uploaded.
  - Single-pass cross-lingual synthesis: LLM analyzes source transcript (e.g. English or Japanese) and directly synthesizes final Knowledge Pack and Digest outputs into the target language (`ko`, `en`, `ja`).
- **Fast-Fail Error Diagnostics & Max Retry Bounds**:
  - Maximum DAG job retry limit (max 2 attempts) with fast-fail error diagnostics.
  - Quota limit errors (`You've hit your usage limit`) and runtime authentication errors abort immediately with user-friendly error messages instead of infinite retry loops.
- **Core CLI Rebranding (`chew`)**:
  - Rebranded the primary CLI command to `chew` (`chew summarize`, `chew blog`, `chew study`, `chew obsidian`, `chew doctor`, etc.).
- **Local Audio and Video File Input**:
  - Direct transcription of local media files (`.mp3`, `.mp4`, `.m4a`, `.wav`, `.mkv`, `.mov`, `.aac`, `.flac`, `.ogg`, `.webm`, etc.) via `faster-whisper`.
  - Content-addressed SHA-256 fingerprinting for local files so Knowledge Packs are reused even after moving or renaming files.
  - Zero-copy processing: local files are never copied, altered, or deleted.
  - Command shortcut: run `chew summarize ./file.mp3`, `chew study ./lecture.mp4`, or `chew ./recording.m4a`.
  - Stored absolute source path preservation in SQLite DB for interrupted run recovery via `chew resume`.
  - Separate Korean and English error diagnostics for local media vs YouTube inputs.
- **AI Runtime Harness Adapters**:
  - Added native `Antigravity CLI (agy)` harness adapter (`AntigravityHarness`) supporting headless JSON print mode with structured schema validation.
- **Ports & Adapters Architecture Refactoring**:
  - Reorganized project into 9 clean subpackages (`core`, `pipeline`, `storage`, `harness`, `transcripts`, `app`, `retention`, `benchmark`, `cli`).
- **Architecture Diagrams**:
  - Interactive Mermaid diagram source code and high-resolution PNG visualizations for user flow and internal pipeline in both English and Korean.

## [0.1.0] - 2026-08-16

### Added
- **Core CLI (`chew`)**:
  - Local-first resumable knowledge compiler for YouTube videos.
  - Chapter-aware and adaptive 5-10 minute topic segmentation.
  - Hierarchical topic → chapter → Knowledge Pack synthesis pipeline.
- **AI Runtime Adapters**:
  - Integrated support for Codex CLI, Gemini CLI, Claude Code, and Ollama with automatic fallback and login status preflight checks.
- **Purpose-Specific Reassembly**:
  - Digest generation (with timestamped evidence), Blog post drafting, Study notes, and Obsidian vault export with `[[wikilinks]]`.
- **Durable Recovery & Caching**:
  - SQLite WAL state machine with worker claim leases and heartbeat recovery.
  - Resume interrupted runs with `chew resume [RUN_ID]`.
  - Content-addressed Knowledge Pack and output caching using canonical JSON SHA-256 digests compressed with `zstd`.
- **Storage Retention & Policy Management**:
  - Retention policies (`compact`, `private`, `archive`).
  - Management commands: `chew storage`, `chew cleanup`, `chew delete`, and `chew purge`.
- **Benchmarking Suite**:
  - Automated quality & recall benchmark framework (`chew benchmark`) comparing direct Gemini URL analysis against hierarchical pipeline synthesis.
