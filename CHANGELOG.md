# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Live benchmark progress**: each condition/repeat is emitted immediately before its external
  provider call, making long explicit live runs observable before their final report is written.
- **Grounded Knowledge Tree compiler foundation**: adds immutable untrusted tree drafts and
  locally grounded tree artifacts, reversible prepared-transcript input, one-shot local annotation
  sidecars, and a one-call Frontier extraction path (with a bounded two-call over-budget refine
  adapter). The compatible Knowledge Pack now records the resulting tree fingerprint.
- **Role-bound local annotation**: an already-installed single Ollama model may receive one
  closed transcript-annotation sidecar request when explicitly enabled; policy keeps extraction
  on the Frontier runtime and records the local stage separately.
- **Explicit unknown-outcome retry**: a run whose provider acceptance is uncertain cannot be
  silently resent; an explicit `resume` records a new retry attempt before reopening it.
- **Comparable GKT benchmark condition**: short-video benchmark specifications now include a
  `gkt-deterministic` condition alongside the historical single-pass and hierarchical paths,
  using the same resolved transcript snapshot and configured Frontier runtime.
- **GKT trace vocabulary**: compiler execution now emits `input.compile`, `frontier.generate`,
  `evidence.ground`, and `tree.assemble` spans, aligned with immutable compiler checkpoints.
- **GKT benchmark diagnostics**: deterministic GKT benchmark results now report Frontier call count,
  grounding coverage, ambiguous anchors, and unsupported tree claims alongside quality metrics.
- **Benchmark-reference review queues**: adds non-executable, AI-assisted Markdown candidate
  queues for the current short, long, and Korean fixtures. Human approval is required before any
  candidate can enter a live benchmark reference.
- **User-reviewed benchmark references**: transcribes 14 approved claims across six source-specific
  JSON reference artifacts. Five queue entries marked for revision remain excluded, and all reference
  files pass the pre-provider structural validation.
- **Korean conversational benchmark fixture**: adds the publicly captioned 38m48s Korean
  conversational fixture `youtube_ko_38m48s_for_benchmark` to the locked maintainer preprocessing
  catalog. It is a reproducibility input only; no live Frontier benchmark or quality claim was run.
- **Korean lecture benchmark fixture**: adds the publicly captioned 45m46s Korean lecture
  `youtube_ko_45m46s_for_benchmark` to the locked maintainer preprocessing catalog. It is a
  reproducibility input only; no live Frontier benchmark or quality claim was run.
- **Bounded, credential-free transcript recovery**:
  - Public transcript providers now have 20-second individual deadlines and a 60-second
    acquisition budget with structured timeout and YouTube failure reasons.
  - `chew summarize --transcript <VTT|SRT|TXT> --source-url <URL>` accepts user-provided raw
    transcript evidence without browser cookies, Keychain access, proxies, or third-party
    transcript-site fallback.
  - Application bootstrap no longer supplies browser profile or cookie configuration to the
    default transcript provider chain.
- **YouTube caption acquisition hardening**:
  - Adds a player-bootstrap `youtubei` structured transcript provider and a direct player-response `captionTracks` provider ahead of third-party extractors.
  - Records timed-text `HTTP 429` explicitly and continues when YouTube rejects a `youtubei` request with `FAILED_PRECONDITION`.
  - Enables an installed Node.js runtime for anonymous public yt-dlp caption retrieval.
- **Resilient transcript acquisition**:
  - Adds `pytubefix` caption extraction as an independent fallback after yt-dlp and youtube-transcript-api.
  - Preserves 429 as a rate-limit outcome, retries it with bounded backoff, and gives an actionable CLI recovery message.
  - Documents provider order, credential-free boundaries, and recovery behavior in `docs/wiki/transcript-acquisition.md`.

### Changed
- **Codex GKT strict-schema compatibility**: fixed-length relation tuples now emit a string-object
  `items` schema while preserving their length validation, allowing Codex structured extraction to
  accept the Grounded Knowledge Tree response contract.
- **Locked preprocessing measurement**: the metrics-only baseline and candidate paths now have a
  recorded seven-fixture run, including the Korean lecture and conversational fixtures. All seven
  captions resolved with the entry-specific language; tokenizer input changed from 132,312 to
  118,716 (10.28%). This remains non-billing, non-quality evidence and does not change the
  opt-in preprocessing default.
- **Reviewed preprocessing conclusion**: promoted the seven-fixture metrics-only result to the
  maintainer benchmark index. The default remains opt-in because the report has no quality gate or
  provider-billing evidence.
- **Default compilation and rendering path**: application runs now select the GKT compiler;
  default Digest, Blog, Study, JSON, and Obsidian profiles render deterministically from the
  persisted Knowledge Pack without outline, compose, or verification model requests. The former
  hierarchical pipeline remains available only as an explicit compatibility/benchmark strategy.
- **Readable benchmark display labels**: Markdown, HTML, and Plotly per-video reports now show
  compact language-and-duration labels such as `English · 2h 00m` while preserving the immutable
  fixture key in locks, metrics, and quality comparisons.
- **Reviewed benchmark-reference guardrail**: quality references now require non-empty claims and
  evidence, valid source metadata, positive durations/tolerances, and in-range timestamps. Invalid
  files are rejected by the CLI before a live provider call.
- **Per-video benchmark caption language**: each locked benchmark entry now declares its requested
  caption language. Both preprocessing measurement paths use that value, and the obsolete duplicate
  report-side lock file was removed in favor of `benchmarks/videos.lock.json`. Filler metrics now
  reuse the product's Korean and English filler definitions.
- **Named maintainer benchmark inputs**: renamed locked YouTube fixture keys to the explicit
  `youtube_en_<duration>_for_benchmark` form, making their dedicated benchmark role clear without
  conflating them with product URLs or a particular synthesis path.
- **Explicit schema migration history**: SQLite schema upgrades now execute named, idempotent
  version steps through v7, including the existing run and measurement indexes, rather than
  relying on implicit current-schema creation for evolution.
- **Canonical segmentation depth values**: removed localized Korean depth aliases from chapter
  coalescing so only documented canonical configuration values affect segmentation behavior.
- **Run-local telemetry injection**: removes the global telemetry singleton. `ApplicationContainer`
  injects telemetry into the pipeline, and `ApplicationService` opens a `ContextVar`-isolated
  collector for each generate or resume run so concurrent traces do not share span buffers.
- **P0 transcript snapshot integrity**: short-video Frontier benchmark preparation now resolves
  public captions once before any condition runs and injects that immutable snapshot into every
  single-pass and hierarchical repeat. A resolution failure therefore produces no live condition
  and no quality report.
- **Frontier evidence and partial-result validation**: a live Codex run rejected an invalid
  transcript-evidence candidate, and a controlled live Codex pipeline run confirmed that a failed
  topic produces an explicit partial result with its missing timestamp range while remaining
  chapter and compose work completes.
- **Transcript recovery scope**: rejects visible-panel browser capture and OCR as product fallback
  work. Public URL acquisition remains the normal path, while explicit VTT/SRT/TXT input remains
  the sole credential-free recovery mechanism.
- **Bounded runtime rate-limit recovery**: `ExecutionPlan` now records the normal runtime retry
  ceiling (2 attempts) and 429 policy (3 attempts, a 60-second per-job budget, and full-jitter
  waits capped at 5 seconds). Persistent rate limits now end as `failed_runtime`; topic failures
  retain partial-result behavior, while critical jobs remain terminal. An explicit `chew resume`
  starts a new in-memory rate-limit budget.
- **Strict credential-free transcript acquisition**: removed the `chew auth youtube` command, browser-profile store, `youtube_cookie_file` configuration, and yt-dlp cookie/browser options. Built-in provider construction now supports only anonymous public caption retrieval; invalid legacy configuration fails explicitly.
- **Strict Codex output composition schemas**: output outline, compose, and verification requests now declare complete object properties, allowing cached Knowledge Packs to be reassembled through Codex structured output.
- **P0 URL-path validation**: the locked five-minute fixture completed public transcript acquisition, Frontier synthesis, Knowledge Pack generation, Digest export, and cached Blog reassembly without browser credentials.
- **Short-video Frontier benchmark**:
  - Adds `chew benchmark run --short-video` to compare one-pass and hierarchical synthesis using the same transcript and configured Frontier runtime.
  - Records provider usage, latency, evidence coverage, timestamp accuracy, and unsupported claims without mixing in direct video-URL input.
- **Harness Response and Endpoint Boundaries**:
  - Rejects model responses over 1 MiB, deeper than 64 JSON levels, or containing collections over 10,000 items before schema materialization.
  - Restricts Ollama to loopback endpoints unless the caller explicitly provides an endpoint allowlist.
  - Prevents configured Ollama routes from handling summary tasks; the Policy Layer records the Frontier fallback instead.
  - Redacts values stored under sensitive keys in structured logs and SQLite job measurements.
  - Normalizes Pydantic and compose schemas for Codex strict structured output, including required properties, closed objects, and default removal.
  - Resuming a failed run now retries every downstream dependency, preventing stale chapter or compose artifacts from being reused.
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
