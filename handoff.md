# Current Execution Index

> Read this first to answer "what should we do now?" Read the linked canonical document only
> when its acceptance criteria or product decision is needed.

## Branch and State

- Branch: `feature/benchmark-quality-readiness`
- Active roadmap: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)

## Next Priorities

1. Run the final integrated Frontier benchmark against the user-reviewed references, recording GKT
   call/grounding diagnostics and raw/processed quality gates.
2. Resolve the five `수정` queue entries before adding them to the corresponding references; the
   current approved claims are already transcribed under `benchmarks/references/`.
3. Add the optional bounded LangGraph Agent Orchestration plane only behind the `agents` extra after
   the final compiler and policy benchmark gate is complete.

## Active Constraints

- `benchmarks/videos.lock.json` contains the Korean lecture fixture
  `youtube_ko_45m46s_for_benchmark`, Korean conversational fixture
  `youtube_ko_38m48s_for_benchmark`, plus English fixtures: `youtube_en_4m35s_for_benchmark`,
  `youtube_en_39m00s_for_benchmark`, `youtube_en_55m48s_for_benchmark`,
  `youtube_en_2h00m09s_for_benchmark`, and `youtube_en_2h49m45s_for_benchmark`. A locked fixture
  is a reproducibility target for maintainer benchmarks, not a user-input restriction. Its matching
  quality reference must be independently human-reviewed. Approved, source-specific references are
  stored under `benchmarks/references/`; draft Markdown remains non-executable.
- Each lock entry has a required caption `language`; both preprocessing measurement paths request
  that entry-specific language. The Korean lecture has publicly available automatic `ko` captions,
  but this does not establish an availability guarantee.
- `ExecutionPlan` records normal-runtime retry (2 attempts) and 429 policy (3 attempts, 60-second
  budget, 5-second full-jitter cap). The scheduler resets that in-memory 429 budget for an explicit
  `chew resume`. Generation subprocess timeout remains the separate `GenerationRequest` default.
- Do not run or interpret end-to-end Frontier benchmarks during incremental implementation. They are
  reserved for the final pre-deployment gate after functionality, policy boundaries, and loop
  termination work are complete.

## Current Decision

- Frontier remains the final reasoning and summary runtime.
- The approved architecture is a deterministic Grounded Knowledge Tree compiler plus an optional
  LangGraph Agent Orchestration plane. The compiler does not import LangGraph; agents consume Grounded
  Knowledge Tree artifacts through policy-scoped typed tools.
- Ollama may propose span-ID-based input-cleanup annotations in `auto/on` mode when a configured single
  model is already installed. It never summarizes or judges evidence, never downloads during analysis,
  and any invalid, timed-out, or >5% token-expanding result falls back to deterministic cleanup.
- Frontier receives one prepared transcript, not raw and prepared copies. Default output profiles must
  render from the resulting Knowledge Pack without additional outline/compose/verify model calls.
- Visible-panel browser capture and OCR are not product work: URL-based public transcript
  acquisition is the default path, and VTT/SRT/TXT remains the only explicit recovery input.
- Telemetry is injected by `ApplicationContainer` and uses `ContextVar`-isolated run collectors;
  a scoped DI library remains deferred in `PRODUCT_ROADMAP.md`.
- A general Knowledge Graph database, Notion, RSS, MCP, REST API, and automation remain deferred. Grounded
  Knowledge Tree is the compiler's versioned artifact and does not introduce a graph database.

## Verification and Working Tree

- `b1870bf` makes the application default to a GKT path: it compiles a reversible prepared
  transcript, calls Frontier once for a strict `KnowledgeTreeDraft`, grounds raw segment IDs and
  timestamps locally, projects the compatible Knowledge Pack, and renders all default outputs
  without model calls. `1b48a13` adds tree-domain grounding/projection types. Full verification:
  `301 passed, 2 skipped`; Ruff and mypy passed. No live Frontier benchmark was run.
- `10567bf` persists immutable compiler checkpoints for prepared input, Frontier draft, grounded
  tree, and compatibility pack. `1b09a58` records uncertain provider acceptance as
  `external_outcome_unknown` and does not automatically resend it. Focused database/pipeline
  tests, Ruff, and mypy passed; no live Frontier benchmark was run.
- `e04810b` routes the sole `transcript_annotate` role to an already-available single Ollama model
  only when explicitly enabled; knowledge extraction remains Frontier-only. Full verification:
  `305 passed, 2 skipped`; Ruff and mypy passed.
- `2637689` makes `resume` explicitly reopen `external_outcome_unknown` via a new retry attempt;
  ordinary failed-job resume behavior remains unchanged. Focused database/application tests, Ruff,
  and mypy passed.
- `e0608f5` adds the offline-testable `gkt-deterministic` short-video benchmark condition beside
  the legacy conditions, sharing the same transcript snapshot and runtime. Full verification:
  `307 passed, 2 skipped`; Ruff and mypy passed. No live benchmark was run.
- `3bac3cb` emits GKT stage spans aligned with durable checkpoints. Focused pipeline/telemetry
  tests, Ruff, and mypy passed.
- `7143ffc` adds GKT Frontier-call and grounding diagnostics to short-video benchmark reports.
  Full verification: `307 passed, 2 skipped`; Ruff and mypy passed. No live benchmark was run.
- User-reviewed queue decisions are committed in `cdc2f75`; the approval column is now explicitly
  labelled as a user review decision. Six structurally validated JSON references contain the 14
  approved claims; five `수정` entries remain excluded. `tests/test_benchmark.py` passed (11 tests),
  as did JSON schema validation and Ruff. No live Frontier benchmark has run yet.
- The 2026-08-25 metrics-only run covers all seven locked fixtures with the same lock and concurrency
  (`baseline-20260825T052411Z`, `current-20260825T052533Z`). All succeeded; tokenizer input fell
  from 132,312 to 118,716 (10.28%). The Korean lecture fell 22,916 -> 22,747 (0.74%) and the Korean
  conversation 18,014 -> 17,866 (0.82%). No Frontier call, quality evaluation, adoption decision,
  or report promotion occurred. These two untracked run directories require review before staging.

- `0baee5d` contains the credential-boundary, transcript pipeline, bounded-runtime-policy,
  telemetry, P0 benchmark-snapshot, and migration work. Full verification at that point was
  `282 passed, 2 skipped`; Ruff and mypy passed. `e4d11c6` removes localized Korean segmentation
  depth aliases; its focused tests, Ruff, and mypy passed.
- `3bac530` adds the Korean lecture catalog and per-video caption-language handling. Full
  verification is current: `287 passed, 2 skipped`; Ruff and mypy passed. The metadata and
  caption-track check used anonymous public yt-dlp only; no live Frontier benchmark was run.
- `06d1654` adds the Korean conversational fixture. The same anonymous public metadata and
  caption-track check confirmed `ko`/`ko-orig`; no live Frontier benchmark was run.
- `79e5e8e` adds benchmark-reference validation. Full verification at that point was
  `291 passed, 2 skipped`; Ruff and mypy passed. Invalid references now fail before a live provider
  call; this does not replace the required human content review.
- `c474f93` adds AI-assisted, non-executable reference drafts. Focused benchmark tests passed
  (`39 passed`), as did Ruff and mypy. The source captions were retrieved anonymously with public
  yt-dlp; no browser credentials, local profile, or live Frontier benchmark were used.
- The latest five-English-video metrics-only run found `origin/develop` already up to date. Baseline
  `baseline-20260824T075239Z` and current
  `current-20260824T075339Z` used the same temporary five-video lock; all videos succeeded and
  current preprocessing reduced tokenizer input from 79,788 to 78,056 (2.2%) with 0.232 seconds of
  aggregate preprocessing latency. Quality was not evaluated, so the report status is `revise` and
  no default-adoption decision follows.
- `d695ee8` defines the presentation-only benchmark-label contract; `caff0ba` implements it. The
  renderer replaces internal keys in Markdown, HTML tables, Plotly axes, and fallback HTML
  with labels such as `English · 2h 00m`; the persisted keys remain unchanged. Full verification:
  `293 passed, 2 skipped`; Ruff and mypy passed. A regenerated five-video Plotly report is under
  `/tmp/chew-benchmark-five-labels.g8XKJ2/current/report.html`.
- User-approved short-video benchmark run `benchmark-results/run-7022e011212b/` compared the
  anonymously acquired 14m34s English transcript for `aBUniZHgCnE` across three Codex repeats per
  path. Single-pass median latency/usage was `16.952s`/`29,192`; hierarchical was
  `57.744s`/`348,963`. Both had zero evidence coverage, and the paths carry different prompt
  fingerprints, so this is not a default-path decision. Keep the reference-evidence/prompt-policy
  repair as the immediate prerequisite for rerunning it.
- The previous `single_frontier_v1` 15-minute design is not implementation-ready: duration alone
  is not a valid trigger for fan-out. Gemini long-context models can accept much longer prepared
  transcripts in one request, so the policy must become runtime/model input-budget aware first.
- A result-path audit found no hard-coded summary, claim, or evidence content under `src/chew`.
  Static result strings are only renderer structure and state/provenance labels; every semantic
  result value comes from a Knowledge Pack and validated transcript evidence.
- The five-minute URL path completed under run `d2e4a1f7-9ab7-442a-9084-9a6129f7021d`; its
  `auto_subtitle` raw artifact, Knowledge Pack, Digest, and cached Blog reassembly are recorded
  in [`docs/wiki/transcript-acquisition.md`](docs/wiki/transcript-acquisition.md). The output
  schema fix has focused tests and a live reassembly result. Latest full verification: `279
  passed, 2 skipped`; Ruff and mypy passed.
- P0 transcript acquisition is complete. Short-video benchmark preparation resolves one public raw
  transcript snapshot before any Frontier condition runs and reuses it for all conditions and
  repeats; failure therefore creates no live condition or report. This was verified with focused
  tests only, not a live benchmark.
- Bounded 429 retry implementation has focused scheduler/policy coverage; full verification is the
  immediate next action before the next live Frontier validation. The required scheduler benchmark
  completed in `2m34.57s` (320,600 input / 9,647 output), above the recorded `1m50s` baseline;
  no 429 was reported and the separate dashboard process had no in-memory spans. This result is
  non-decisive and must not be repeated or interpreted until the final pre-deployment benchmark.
- Frontier validation is complete: the recorded five-minute Codex run rejected 1 of 11 proposed
  evidence candidates (10 valid), and a separate controlled Codex run with one injected topic
  failure produced `partial` status and the expected `01:00-02:00` missing range while actual
  Codex chapter and compose jobs completed. Details are in
  [`docs/wiki/transcript-acquisition.md`](docs/wiki/transcript-acquisition.md).
- Acquisition evidence and root-cause history are in
  [`docs/wiki/transcript-acquisition.md`](docs/wiki/transcript-acquisition.md).
- Untracked benchmark-report directories exist under
  `reports/performance-comparisons/transcript-preprocessing/`; inspect before staging and do not
  include them accidentally.
